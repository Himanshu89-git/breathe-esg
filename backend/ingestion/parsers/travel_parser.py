"""
Corporate Travel Parser — Concur / Navan CSV Export
Handles the standard Concur Travel transaction export format and Navan's CSV export.

Design choice: CSV export (not API) because:
- Concur's API requires OAuth + enterprise admin credentials. CSV export is available to
  any travel admin without IT involvement.
- Navan (formerly TripActions) offers a similar CSV export from their Reports section.
- Both platforms export in broadly compatible formats: one row per booking/segment.

Real-world fields: traveler name, booking date, travel date, origin, destination,
trip type (air/hotel/car/rail), amount, vendor, booking reference.

For flights: origin & destination airport codes. Distance not always given —
we calculate great-circle distance from IATA codes when not present.
Emission factors: DEFRA/ICAO values per passenger-km, with radiative forcing multiplier for air.
"""
import pandas as pd
import io
import math
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

TRAVEL_COLUMN_MAP = {
    # Concur headers
    'travel date': 'travel_date',
    'departure date': 'travel_date',
    'start date': 'travel_date',
    'transaction date': 'travel_date',
    'booking date': 'booking_date',
    'trip type': 'trip_type',
    'expense type': 'trip_type',
    'type': 'trip_type',
    'category': 'trip_type',
    'origin': 'origin',
    'from': 'origin',
    'departure': 'origin',
    'destination': 'destination',
    'to': 'destination',
    'arrival': 'destination',
    'distance (km)': 'distance_km',
    'distance': 'distance_km',
    'traveler': 'traveler',
    'employee': 'traveler',
    'employee name': 'traveler',
    'vendor': 'vendor',
    'airline': 'vendor',
    'hotel': 'vendor',
    'amount': 'amount',
    'total': 'amount',
    'cost': 'amount',
    'currency': 'currency',
    'class': 'travel_class',
    'cabin class': 'travel_class',
    'flight class': 'travel_class',
    'country': 'country',
    'nights': 'hotel_nights',
    'hotel nights': 'hotel_nights',
    # Normalised (already correct)
    'travel_date': 'travel_date',
    'trip_type': 'trip_type',
    'origin': 'origin',
    'destination': 'destination',
    'distance_km': 'distance_km',
    'traveler': 'traveler',
    'amount': 'amount',
    'currency': 'currency',
    'travel_class': 'travel_class',
    'hotel_nights': 'hotel_nights',
}

# IATA airport coordinates for distance calculation (major airports)
AIRPORT_COORDS = {
    'DEL': (28.5665, 77.1031), 'BOM': (19.0896, 72.8656), 'BLR': (13.1986, 77.7066),
    'MAA': (12.9941, 80.1709), 'CCU': (22.6520, 88.4463), 'HYD': (17.2403, 78.4294),
    'LHR': (51.4700, -0.4543), 'CDG': (49.0097, 2.5479), 'FRA': (50.0379, 8.5622),
    'AMS': (52.3086, 4.7639), 'MAD': (40.4936, -3.5668), 'FCO': (41.8003, 12.2389),
    'JFK': (40.6413, -73.7781), 'LAX': (33.9425, -118.4081), 'ORD': (41.9742, -87.9073),
    'SFO': (37.6213, -122.3790), 'MIA': (25.7959, -80.2870), 'DXB': (25.2532, 55.3657),
    'SIN': (1.3644, 103.9915), 'HKG': (22.3080, 113.9185), 'NRT': (35.7720, 140.3929),
    'SYD': (-33.9461, 151.1772), 'MEL': (-37.6690, 144.8410), 'DOH': (25.2609, 51.6138),
    'IST': (41.2753, 28.7519), 'MUC': (48.3538, 11.7861), 'ZRH': (47.4647, 8.5492),
}

# Emission factors (kg CO2e per unit)
# Source: DEFRA 2023 GHG conversion factors
TRAVEL_EMISSION_FACTORS = {
    'flight_short_haul': 0.25510,   # kg CO2e / passenger-km (< 3700 km, economy, incl. RFI 2x)
    'flight_long_haul': 0.19500,    # kg CO2e / passenger-km (>= 3700 km, economy, incl. RFI)
    'flight_business': 0.42800,     # multiplier applied separately
    'hotel': 31.2,                  # kg CO2e / room-night (global average, DEFRA)
    'car_rental': 0.19400,          # kg CO2e / km (average rental car)
    'taxi': 0.21000,                # kg CO2e / km
    'rail': 0.03700,                # kg CO2e / passenger-km (UK average; varies hugely by country)
}

CATEGORY_SCOPE = {
    'air': ('flight', '3'),
    'flight': ('flight', '3'),
    'hotel': ('hotel', '3'),
    'accommodation': ('hotel', '3'),
    'car': ('car_rental', '3'),
    'car rental': ('car_rental', '3'),
    'rail': ('rail', '3'),
    'train': ('rail', '3'),
    'taxi': ('taxi', '3'),
    'ground': ('taxi', '3'),
}

DATE_FORMATS = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%d.%m.%Y']


def _parse_date(val):
    val = str(val).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _get_distance(origin, destination, raw_distance):
    """Calculate or retrieve flight distance in km."""
    if raw_distance:
        try:
            return float(str(raw_distance).replace(',', ''))
        except (ValueError, TypeError):
            pass
    o = str(origin).upper().strip()
    d = str(destination).upper().strip()
    if o in AIRPORT_COORDS and d in AIRPORT_COORDS:
        lat1, lon1 = AIRPORT_COORDS[o]
        lat2, lon2 = AIRPORT_COORDS[d]
        return round(_haversine_km(lat1, lon1, lat2, lon2), 1)
    return None


def _compute_flight_kg_co2e(distance_km, travel_class='economy'):
    if not distance_km:
        return None
    factor_key = 'flight_long_haul' if distance_km >= 3700 else 'flight_short_haul'
    ef = TRAVEL_EMISSION_FACTORS[factor_key]
    class_lower = str(travel_class).lower()
    if 'business' in class_lower or 'club' in class_lower:
        ef *= 2.0    # Business class approx 2x economy
    elif 'first' in class_lower:
        ef *= 3.0
    return round(distance_km * ef, 4)


def parse_travel_file(file_content: bytes, filename: str) -> dict:
    errors = []
    warnings = []
    records = []

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

    df.columns = [TRAVEL_COLUMN_MAP.get(c.strip().lower(), c.strip().lower()) for c in df.columns]
    df = df.dropna(how='all')

    for idx, row in df.iterrows():
        row_num = idx + 2
        raw = row.to_dict()

        # Parse date
        travel_date = _parse_date(raw.get('travel_date', ''))
        if not travel_date:
            errors.append({'row': row_num, 'field': 'travel_date',
                           'error': f"Cannot parse date: {raw.get('travel_date')}", 'raw': raw})
            continue

        # Infer trip type / category
        trip_type_raw = str(raw.get('trip_type', '')).lower().strip()
        category, scope = None, '3'
        for key, (cat, sc) in CATEGORY_SCOPE.items():
            if key in trip_type_raw:
                category, scope = cat, sc
                break
        if not category:
            warnings.append({'row': row_num, 'warning': f"Unknown trip type '{trip_type_raw}', defaulting to 'other'"})
            category = 'other_travel'

        # Compute quantity and emissions
        quantity = None
        unit = 'passenger-km'
        kg_co2e = None

        if category == 'flight':
            distance_km = _get_distance(
                raw.get('origin', ''), raw.get('destination', ''),
                raw.get('distance_km')
            )
            if not distance_km:
                warnings.append({'row': row_num,
                                  'warning': f"Cannot compute distance for {raw.get('origin')}→{raw.get('destination')}; IATA code not in lookup table"})
            quantity = distance_km or 0
            kg_co2e = _compute_flight_kg_co2e(distance_km, raw.get('travel_class', 'economy'))

        elif category == 'hotel':
            nights_raw = raw.get('hotel_nights', '1')
            try:
                nights = float(str(nights_raw).replace(',', ''))
            except (ValueError, TypeError):
                nights = 1
                warnings.append({'row': row_num, 'warning': f"Could not parse hotel nights '{nights_raw}', defaulting to 1"})
            quantity = nights
            unit = 'room-night'
            kg_co2e = round(nights * TRAVEL_EMISSION_FACTORS['hotel'], 4)

        elif category in ('car_rental', 'taxi'):
            distance_km = None
            try:
                distance_km = float(str(raw.get('distance_km', '')).replace(',', ''))
            except (ValueError, TypeError):
                pass
            quantity = distance_km or 0
            unit = 'km'
            if distance_km:
                ef = TRAVEL_EMISSION_FACTORS.get(category, 0.21)
                kg_co2e = round(distance_km * ef, 4)
            else:
                warnings.append({'row': row_num, 'warning': 'No distance for car/taxi segment — kg CO2e will be null'})

        elif category == 'rail':
            try:
                quantity = float(str(raw.get('distance_km', '0')).replace(',', ''))
            except (ValueError, TypeError):
                quantity = 0
            unit = 'passenger-km'
            if quantity:
                kg_co2e = round(quantity * TRAVEL_EMISSION_FACTORS['rail'], 4)

        else:
            quantity = 0
            unit = 'trip'

        is_suspicious = False
        suspicion_reason = ''
        if category == 'flight' and quantity and quantity > 18000:
            is_suspicious = True
            suspicion_reason = f'Exceptionally long flight distance: {quantity} km'
        if kg_co2e and kg_co2e > 10000:
            is_suspicious = True
            suspicion_reason = f'Very high emissions for single trip: {kg_co2e} kg CO2e'

        records.append({
            'scope': scope,
            'source_type': 'travel',
            'category': category,
            'activity_date': travel_date,
            'quantity': quantity or 0,
            'unit': unit,
            'quantity_original': quantity or 0,
            'unit_original': unit,
            'facility': raw.get('traveler', ''),
            'cost_center': raw.get('cost_center', ''),
            'country': raw.get('country', ''),
            'kg_co2e': kg_co2e,
            'is_suspicious': is_suspicious,
            'suspicion_reason': suspicion_reason,
            'raw_data': raw,
        })

    return {'records': records, 'errors': errors, 'warnings': warnings}
