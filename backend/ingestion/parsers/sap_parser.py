"""
SAP Flat File Parser
Handles SAP FI/MM exports as tab-delimited or semicolon-delimited flat files.
Real SAP exports often come as IDoc flat files or custom ABAP report outputs.
We handle the most common: semicolon-delimited with German/English mixed headers.
"""
import pandas as pd
import io
import logging
from datetime import date
from decimal import Decimal

logger = logging.getLogger(__name__)

# Map SAP column names (German and English variants) to our normalised names
SAP_COLUMN_MAP = {
    # German → normalised
    'WERKS': 'plant_code',
    'KOSTL': 'cost_center',
    'MENGE': 'quantity',
    'MEINS': 'unit',
    'BUDAT': 'posting_date',
    'MATNR': 'material_number',
    'MAKTX': 'material_description',
    'BWART': 'movement_type',
    'LIFNR': 'vendor_number',
    'LAND1': 'country',
    # English variants
    'PLANT': 'plant_code',
    'COST_CENTER': 'cost_center',
    'QUANTITY': 'quantity',
    'UOM': 'unit',
    'POSTING_DATE': 'posting_date',
    'MATERIAL': 'material_number',
    'DESCRIPTION': 'material_description',
    'MOVEMENT_TYPE': 'movement_type',
    'VENDOR': 'vendor_number',
    'COUNTRY': 'country',
    # Breathe normalised (already correct)
    'plant_code': 'plant_code',
    'cost_center': 'cost_center',
    'quantity': 'quantity',
    'unit': 'unit',
    'posting_date': 'posting_date',
    'material_number': 'material_number',
    'material_description': 'material_description',
    'movement_type': 'movement_type',
    'vendor_number': 'vendor_number',
    'country': 'country',
}

# SAP unit codes → normalised unit + conversion factor to normalised
UNIT_NORMALISATION = {
    'L': ('litre', 1.0),
    'LT': ('litre', 1.0),
    'GAL': ('litre', 3.78541),
    'M3': ('litre', 1000.0),
    'KG': ('kg', 1.0),
    'G': ('kg', 0.001),
    'T': ('kg', 1000.0),
    'TO': ('kg', 1000.0),       # SAP metric ton code
    'LB': ('kg', 0.453592),
    'KWH': ('kWh', 1.0),
    'MWH': ('kWh', 1000.0),
    'GJ': ('kWh', 277.778),
    'MMBTU': ('kWh', 293.071),
}

# Material-number patterns → fuel category + scope
MATERIAL_CATEGORY_MAP = [
    ({'DIESEL', 'HSD', 'GAS OIL', 'GASOIL'}, 'diesel', '1'),
    ({'PETROL', 'GASOLINE', 'BENZIN'}, 'petrol', '1'),
    ({'LPG', 'PROPAN', 'BUTAN'}, 'lpg', '1'),
    ({'CNG', 'ERDGAS', 'NATURAL GAS'}, 'natural_gas', '1'),
    ({'COAL', 'KOHLE'}, 'coal', '1'),
    ({'ELECTRICITY', 'STROM', 'POWER'}, 'electricity', '2'),
    ({'STEAM', 'DAMPF', 'HEAT'}, 'steam', '2'),
]

DATE_FORMATS = ['%d.%m.%Y', '%Y%m%d', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']


def _parse_date(val):
    val = str(val).strip()
    for fmt in DATE_FORMATS:
        try:
            from datetime import datetime
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


def _infer_category(material_number: str, description: str):
    combined = f"{material_number} {description}".upper()
    for keywords, category, scope in MATERIAL_CATEGORY_MAP:
        if any(k in combined for k in keywords):
            return category, scope
    return 'other_procurement', '3'


def _normalise_unit(sap_unit: str, quantity: float):
    sap_unit = str(sap_unit).upper().strip()
    if sap_unit in UNIT_NORMALISATION:
        norm_unit, factor = UNIT_NORMALISATION[sap_unit]
        return norm_unit, round(quantity * factor, 6)
    return sap_unit.lower(), quantity


def parse_sap_file(file_content: bytes, filename: str) -> dict:
    """
    Parse SAP flat file export. Returns dict with:
      - records: list of normalised dicts ready for EmissionRecord creation
      - errors: list of row-level error dicts
      - warnings: list of warning dicts
    """
    errors = []
    warnings = []
    records = []

    # Detect delimiter
    sample = file_content[:2000].decode('utf-8', errors='replace')
    delimiter = ';' if sample.count(';') > sample.count('\t') else '\t'

    try:
        df = pd.read_csv(
            io.BytesIO(file_content),
            sep=delimiter,
            encoding='utf-8-sig',   # handles BOM from SAP exports
            dtype=str,
            skipinitialspace=True,
        )
    except Exception as e:
        try:
            df = pd.read_csv(
                io.BytesIO(file_content),
                sep=delimiter,
                encoding='latin-1',
                dtype=str,
                skipinitialspace=True,
            )
        except Exception as e2:
            return {'records': [], 'errors': [{'row': 0, 'error': str(e2)}], 'warnings': []}

    # Normalise column names
    df.columns = [SAP_COLUMN_MAP.get(c.strip().upper(), c.strip().lower()) for c in df.columns]
    df = df.dropna(how='all')

    required = {'quantity', 'posting_date'}
    missing = required - set(df.columns)
    if missing:
        return {
            'records': [],
            'errors': [{'row': 0, 'error': f"Missing required columns: {missing}"}],
            'warnings': []
        }

    for idx, row in df.iterrows():
        row_num = idx + 2  # 1-based, skip header
        raw = row.to_dict()

        # Parse date
        posting_date = _parse_date(raw.get('posting_date', ''))
        if not posting_date:
            errors.append({'row': row_num, 'field': 'posting_date',
                           'error': f"Cannot parse date: {raw.get('posting_date')}", 'raw': raw})
            continue

        # Parse quantity
        qty_raw = str(raw.get('quantity', '')).replace(',', '.').replace(' ', '')
        try:
            quantity = float(qty_raw)
        except ValueError:
            errors.append({'row': row_num, 'field': 'quantity',
                           'error': f"Cannot parse quantity: {qty_raw}", 'raw': raw})
            continue

        if quantity <= 0:
            warnings.append({'row': row_num, 'warning': f"Zero or negative quantity: {quantity}", 'raw': raw})
            continue

        # Unit normalisation
        sap_unit = raw.get('unit', 'L')
        norm_unit, norm_qty = _normalise_unit(sap_unit, quantity)
        if sap_unit.upper() not in UNIT_NORMALISATION:
            warnings.append({'row': row_num, 'warning': f"Unknown SAP unit '{sap_unit}', keeping as-is"})

        # Category inference
        mat_num = raw.get('material_number', '')
        mat_desc = raw.get('material_description', '')
        category, scope = _infer_category(mat_num, mat_desc)

        # Suspicion: very large quantities
        is_suspicious = False
        suspicion_reason = ''
        if norm_unit == 'litre' and norm_qty > 100_000:
            is_suspicious = True
            suspicion_reason = f"Unusually large fuel quantity: {norm_qty} litres"
        elif norm_unit == 'kg' and norm_qty > 500_000:
            is_suspicious = True
            suspicion_reason = f"Unusually large mass: {norm_qty} kg"

        records.append({
            'scope': scope,
            'source_type': 'sap',
            'category': category,
            'activity_date': posting_date,
            'quantity': norm_qty,
            'unit': norm_unit,
            'quantity_original': quantity,
            'unit_original': sap_unit,
            'facility': raw.get('plant_code', ''),
            'cost_center': raw.get('cost_center', ''),
            'country': raw.get('country', ''),
            'is_suspicious': is_suspicious,
            'suspicion_reason': suspicion_reason,
            'raw_data': raw,
        })

    return {'records': records, 'errors': errors, 'warnings': warnings}
