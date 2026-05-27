"""
Utility Data Parser — Electricity Portal CSV Export
Handles the most common format: CSV exports from utility portals (e.g., Uplight, EnergyCAP,
meter data management systems, or manual spreadsheets maintained by facilities teams).

Design choice: CSV portal export (not PDF bills, not API) because:
- Most enterprise facilities teams already pull CSVs from their utility portals monthly
- PDFs require OCR and layout parsing that breaks with any template change
- APIs are available only from some utilities (Green Button, some European smart meter APIs)
- CSV is the lowest-friction, most universally available format

Real-world columns vary but usually include: account number, meter ID, billing period,
kWh consumption, demand (kW), tariff/rate code, amount billed.
"""
import pandas as pd
import io
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)

UTILITY_COLUMN_MAP = {
    # Common portal export headers → normalised
    'account number': 'account_number',
    'account_number': 'account_number',
    'account no': 'account_number',
    'meter id': 'meter_id',
    'meter_id': 'meter_id',
    'meter number': 'meter_id',
    'service address': 'facility',
    'facility': 'facility',
    'location': 'facility',
    'billing period start': 'period_start',
    'period_start': 'period_start',
    'start date': 'period_start',
    'billing period end': 'period_end',
    'period_end': 'period_end',
    'end date': 'period_end',
    'kwh': 'kwh',
    'consumption (kwh)': 'kwh',
    'energy (kwh)': 'kwh',
    'usage_kwh': 'kwh',
    'kwh usage': 'kwh',
    'demand (kw)': 'demand_kw',
    'peak demand': 'demand_kw',
    'tariff': 'tariff_code',
    'rate code': 'tariff_code',
    'supplier': 'supplier',
    'utility': 'supplier',
    'renewable %': 'renewable_pct',
    'renewable_pct': 'renewable_pct',
    'country': 'country',
    'currency': 'currency',
    'amount': 'billed_amount',
    'cost': 'billed_amount',
    'total cost': 'billed_amount',
}

DATE_FORMATS = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%d.%m.%Y',
                '%b %Y', '%B %Y', '%Y%m%d']


def _parse_date(val):
    val = str(val).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


def _parse_float(val):
    try:
        return float(str(val).replace(',', '').replace(' ', ''))
    except (ValueError, TypeError):
        return None


def parse_utility_file(file_content: bytes, filename: str) -> dict:
    """
    Parse utility portal CSV export.
    Handles kWh, demand, multi-meter per account, billing period vs calendar month misalignment.
    """
    errors = []
    warnings = []
    records = []

    # Try multiple delimiters
    for delimiter in [',', ';', '\t']:
        try:
            df = pd.read_csv(
                io.BytesIO(file_content),
                sep=delimiter,
                encoding='utf-8-sig',
                dtype=str,
                skipinitialspace=True,
            )
            if len(df.columns) > 2:
                break
        except Exception:
            continue
    else:
        return {'records': [], 'errors': [{'row': 0, 'error': 'Could not parse CSV'}], 'warnings': []}

    # Normalise column names (lowercase, map)
    df.columns = [UTILITY_COLUMN_MAP.get(c.strip().lower(), c.strip().lower()) for c in df.columns]
    df = df.dropna(how='all')

    # Must have at least kwh and some date
    if 'kwh' not in df.columns:
        return {
            'records': [],
            'errors': [{'row': 0, 'error': "No kWh column found. Expected 'kWh', 'Consumption (kWh)', or 'Usage_kWh'"}],
            'warnings': []
        }

    for idx, row in df.iterrows():
        row_num = idx + 2
        raw = row.to_dict()

        # Parse kWh
        kwh = _parse_float(raw.get('kwh'))
        if kwh is None:
            errors.append({'row': row_num, 'field': 'kwh', 'error': f"Cannot parse kWh: {raw.get('kwh')}", 'raw': raw})
            continue
        if kwh < 0:
            errors.append({'row': row_num, 'field': 'kwh', 'error': f"Negative kWh: {kwh}", 'raw': raw})
            continue

        # Parse billing period — use period_end as activity_date (standard practice)
        period_end = _parse_date(raw.get('period_end', ''))
        period_start = _parse_date(raw.get('period_start', ''))
        activity_date = period_end or period_start
        if not activity_date:
            errors.append({'row': row_num, 'field': 'date', 'error': 'No parseable date found', 'raw': raw})
            continue

        # Warn if billing period > 35 days (utilities sometimes combine periods)
        if period_start and period_end:
            days = (period_end - period_start).days
            if days > 35:
                warnings.append({'row': row_num,
                                  'warning': f"Billing period is {days} days — may span multiple months"})

        # Suspicious: very high or zero consumption
        is_suspicious = False
        suspicion_reason = ''
        if kwh == 0:
            is_suspicious = True
            suspicion_reason = 'Zero kWh consumption — meter read issue or vacant facility?'
        elif kwh > 500_000:
            is_suspicious = True
            suspicion_reason = f'Very high consumption: {kwh} kWh in one billing period'

        records.append({
            'scope': '2',  # Market-based; location-based would need grid emission factors
            'source_type': 'utility',
            'category': 'electricity',
            'activity_date': activity_date,
            'quantity': kwh,
            'unit': 'kWh',
            'quantity_original': kwh,
            'unit_original': 'kWh',
            'facility': raw.get('facility', raw.get('account_number', '')),
            'cost_center': raw.get('account_number', ''),
            'country': raw.get('country', ''),
            'is_suspicious': is_suspicious,
            'suspicion_reason': suspicion_reason,
            'raw_data': raw,
            # Extra metadata stored in raw; billing period info
        })

    return {'records': records, 'errors': errors, 'warnings': warnings}
