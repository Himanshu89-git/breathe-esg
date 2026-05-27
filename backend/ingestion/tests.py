import io
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import Tenant, User
from emissions.models import IngestionBatch, EmissionRecord, EmissionFactor
from ingestion.parsers.sap_parser import parse_sap_file
from ingestion.parsers.utility_parser import parse_utility_file
from ingestion.parsers.travel_parser import parse_travel_file, _haversine_km, _get_distance


# ── SAP Parser Tests ──────────────────────────────────────────────────────────

SAP_VALID_CSV = b"""WERKS;KOSTL;MATNR;MAKTX;MENGE;MEINS;BUDAT;BWART;LAND1
PLANT-DEL;CC-OPS;MAT-001;Diesel HSD Grade A;15000.000;L;01.01.2024;261;IN
PLANT-BOM;CC-OPS;MAT-002;Petrol 91 Octane;4500.000;L;05.01.2024;261;IN
PLANT-DEL;CC-UTIL;MAT-003;CNG Natural Gas;90.000;M3;10.01.2024;261;IN
"""

SAP_BAD_DATE_CSV = b"""WERKS;KOSTL;MATNR;MAKTX;MENGE;MEINS;BUDAT;BWART;LAND1
PLANT-DEL;CC-OPS;MAT-001;Diesel HSD Grade A;15000.000;L;INVALID-DATE;261;IN
"""

SAP_BAD_QTY_CSV = b"""WERKS;KOSTL;MATNR;MAKTX;MENGE;MEINS;BUDAT;BWART;LAND1
PLANT-DEL;CC-OPS;MAT-001;Diesel HSD Grade A;NOT_A_NUMBER;L;01.01.2024;261;IN
"""

SAP_SUSPICIOUS_CSV = b"""WERKS;KOSTL;MATNR;MAKTX;MENGE;MEINS;BUDAT;BWART;LAND1
PLANT-DEL;CC-OPS;MAT-001;Diesel HSD Grade A;150000.000;L;01.01.2024;261;IN
"""

SAP_ENGLISH_HEADERS = b"""PLANT,COST_CENTER,MATERIAL,DESCRIPTION,QUANTITY,UOM,POSTING_DATE,MOVEMENT_TYPE,COUNTRY
PLANT-DEL,CC-OPS,MAT-001,Diesel HSD Grade A,5000.000,L,2024-01-01,261,IN
"""


class SAPParserTests(TestCase):
    def test_valid_csv_parses_correctly(self):
        result = parse_sap_file(SAP_VALID_CSV, 'test.csv')
        self.assertEqual(len(result['records']), 3)
        self.assertEqual(len(result['errors']), 0)

    def test_diesel_classified_scope1(self):
        result = parse_sap_file(SAP_VALID_CSV, 'test.csv')
        diesel = [r for r in result['records'] if r['category'] == 'diesel'][0]
        self.assertEqual(diesel['scope'], '1')
        self.assertEqual(diesel['source_type'], 'sap')

    def test_unit_conversion_litres(self):
        result = parse_sap_file(SAP_VALID_CSV, 'test.csv')
        diesel = [r for r in result['records'] if r['category'] == 'diesel'][0]
        self.assertEqual(diesel['unit'], 'litre')
        self.assertEqual(float(diesel['quantity']), 15000.0)

    def test_m3_converted_to_litres(self):
        result = parse_sap_file(SAP_VALID_CSV, 'test.csv')
        gas = [r for r in result['records'] if r['category'] == 'natural_gas'][0]
        self.assertEqual(gas['unit'], 'litre')
        self.assertAlmostEqual(float(gas['quantity']), 90000.0)  # 90 M3 × 1000

    def test_bad_date_produces_error(self):
        result = parse_sap_file(SAP_BAD_DATE_CSV, 'test.csv')
        self.assertEqual(len(result['records']), 0)
        self.assertEqual(len(result['errors']), 1)
        self.assertIn('posting_date', result['errors'][0]['field'])

    def test_bad_quantity_produces_error(self):
        result = parse_sap_file(SAP_BAD_QTY_CSV, 'test.csv')
        self.assertEqual(len(result['records']), 0)
        self.assertEqual(len(result['errors']), 1)

    def test_suspicious_large_quantity_flagged(self):
        result = parse_sap_file(SAP_SUSPICIOUS_CSV, 'test.csv')
        self.assertEqual(len(result['records']), 1)
        self.assertTrue(result['records'][0]['is_suspicious'])
        self.assertIn('150000', result['records'][0]['suspicion_reason'])

    def test_english_headers_accepted(self):
        result = parse_sap_file(SAP_ENGLISH_HEADERS, 'test.csv')
        self.assertEqual(len(result['records']), 1)
        self.assertEqual(len(result['errors']), 0)

    def test_raw_data_preserved(self):
        result = parse_sap_file(SAP_VALID_CSV, 'test.csv')
        rec = result['records'][0]
        self.assertIn('raw_data', rec)
        self.assertIsInstance(rec['raw_data'], dict)


# ── Utility Parser Tests ──────────────────────────────────────────────────────

UTILITY_VALID_CSV = b"""Account Number,Meter ID,Service Address,Billing Period Start,Billing Period End,kWh,Demand (kW),Tariff,Supplier,Country,Currency,Amount
ACC-001,MTR-001,HQ Floor 1-5,2024-01-01,2024-01-31,45000,120.5,LT-Commercial,TATA Power,IN,INR,225000
ACC-002,MTR-002,Warehouse Mumbai,2024-01-01,2024-01-31,12000,35.0,HT-Industrial,MSEDCL,IN,INR,72000
"""

UTILITY_ZERO_KWH = b"""Account Number,Meter ID,Service Address,Billing Period Start,Billing Period End,kWh,Country
ACC-003,MTR-003,Empty Office,2024-01-01,2024-01-31,0,IN
"""

UTILITY_LONG_PERIOD = b"""Account Number,Meter ID,Service Address,Billing Period Start,Billing Period End,kWh,Country
ACC-004,MTR-004,Regional Office,2024-01-01,2024-02-28,28000,IN
"""

UTILITY_NO_KWH_COL = b"""Account Number,Meter ID,Billing Period Start,Billing Period End
ACC-001,MTR-001,2024-01-01,2024-01-31
"""


class UtilityParserTests(TestCase):
    def test_valid_csv_parses(self):
        result = parse_utility_file(UTILITY_VALID_CSV, 'utility.csv')
        self.assertEqual(len(result['records']), 2)
        self.assertEqual(len(result['errors']), 0)

    def test_scope_is_2(self):
        result = parse_utility_file(UTILITY_VALID_CSV, 'utility.csv')
        for rec in result['records']:
            self.assertEqual(rec['scope'], '2')
            self.assertEqual(rec['category'], 'electricity')
            self.assertEqual(rec['unit'], 'kWh')

    def test_zero_kwh_flagged_suspicious(self):
        result = parse_utility_file(UTILITY_ZERO_KWH, 'utility.csv')
        self.assertEqual(len(result['records']), 1)
        self.assertTrue(result['records'][0]['is_suspicious'])

    def test_long_billing_period_warns(self):
        result = parse_utility_file(UTILITY_LONG_PERIOD, 'utility.csv')
        self.assertGreater(len(result['warnings']), 0)
        self.assertTrue(any('days' in w['warning'] for w in result['warnings']))

    def test_missing_kwh_column_returns_error(self):
        result = parse_utility_file(UTILITY_NO_KWH_COL, 'utility.csv')
        self.assertEqual(len(result['records']), 0)
        self.assertGreater(len(result['errors']), 0)

    def test_period_end_used_as_activity_date(self):
        result = parse_utility_file(UTILITY_VALID_CSV, 'utility.csv')
        from datetime import date
        self.assertEqual(result['records'][0]['activity_date'], date(2024, 1, 31))


# ── Travel Parser Tests ───────────────────────────────────────────────────────

TRAVEL_VALID_CSV = b"""Employee Name,Travel Date,Trip Type,Origin,Destination,Distance (km),Cabin Class,Vendor,Nights,Currency,Amount,Country
Rahul Sharma,2024-01-08,Air,DEL,BOM,,Economy,IndiGo,,INR,6500,IN
Priya Mehta,2024-01-10,Air,BOM,LHR,,Economy,Air India,,INR,45000,IN
Amit Kumar,2024-01-12,Hotel,,,,,,3,INR,9000,IN
Vikram Singh,2024-01-15,Car Rental,DEL,,,450,,,INR,8000,IN
Neha Verma,2024-01-20,Rail,DEL,BOM,1400,,,,,INR,2000,IN
"""

TRAVEL_BUSINESS_CLASS = b"""Employee Name,Travel Date,Trip Type,Origin,Destination,Distance (km),Cabin Class,Vendor,Nights,Currency,Amount,Country
Exec User,2024-01-10,Air,DEL,JFK,,Business,Air India,,INR,180000,IN
"""


class TravelParserTests(TestCase):
    def test_valid_csv_parses(self):
        result = parse_travel_file(TRAVEL_VALID_CSV, 'travel.csv')
        self.assertGreater(len(result['records']), 0)

    def test_all_scope_3(self):
        result = parse_travel_file(TRAVEL_VALID_CSV, 'travel.csv')
        for rec in result['records']:
            self.assertEqual(rec['scope'], '3')

    def test_flight_distance_computed_from_iata(self):
        result = parse_travel_file(TRAVEL_VALID_CSV, 'travel.csv')
        del_bom = [r for r in result['records'] if r['category'] == 'flight'][0]
        # DEL→BOM great-circle is ~1140 km
        self.assertGreater(float(del_bom['quantity']), 1000)
        self.assertLess(float(del_bom['quantity']), 1500)

    def test_hotel_uses_nights_as_quantity(self):
        result = parse_travel_file(TRAVEL_VALID_CSV, 'travel.csv')
        hotel = [r for r in result['records'] if r['category'] == 'hotel'][0]
        self.assertEqual(float(hotel['quantity']), 3.0)
        self.assertEqual(hotel['unit'], 'room-night')

    def test_hotel_kg_co2e_computed(self):
        result = parse_travel_file(TRAVEL_VALID_CSV, 'travel.csv')
        hotel = [r for r in result['records'] if r['category'] == 'hotel'][0]
        # 3 nights × 31.2 = 93.6
        self.assertAlmostEqual(float(hotel['kg_co2e']), 93.6, places=1)

    def test_business_class_higher_emissions(self):
        economy_result = parse_travel_file(TRAVEL_VALID_CSV, 'travel.csv')
        business_result = parse_travel_file(TRAVEL_BUSINESS_CLASS, 'travel.csv')
        biz = business_result['records'][0]
        # Business class should have non-null and high kg_co2e
        self.assertIsNotNone(biz['kg_co2e'])
        self.assertGreater(float(biz['kg_co2e']), 1000)

    def test_haversine_del_bom(self):
        """DEL (28.57, 77.10) → BOM (19.09, 72.87) ≈ 1140 km"""
        dist = _haversine_km(28.5665, 77.1031, 19.0896, 72.8656)
        self.assertGreater(dist, 1100)
        self.assertLess(dist, 1200)

    def test_get_distance_from_iata(self):
        dist = _get_distance('DEL', 'BOM', None)
        self.assertIsNotNone(dist)
        self.assertGreater(dist, 1000)

    def test_get_distance_from_explicit_value(self):
        dist = _get_distance('DEL', 'BOM', '1400')
        self.assertEqual(dist, 1400.0)

    def test_unknown_iata_returns_none(self):
        dist = _get_distance('ZZZ', 'YYY', None)
        self.assertIsNone(dist)


# ── Upload Endpoint Integration Tests ─────────────────────────────────────────

class UploadEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tenant = Tenant.objects.create(name='Test Corp', slug='test-corp')
        self.user = User.objects.create_user(
            username='analyst', password='pass',
            tenant=self.tenant, role=User.ROLE_ANALYST,
        )
        self.client.force_authenticate(user=self.user)
        EmissionFactor.objects.create(
            source_type='sap', activity='diesel', unit='litre',
            kg_co2e_per_unit=2.68861, region='GLOBAL',
        )

    def test_upload_sap_csv(self):
        file = io.BytesIO(SAP_VALID_CSV)
        file.name = 'test_sap.csv'
        res = self.client.post('/api/ingestion/upload/', {
            'file': file,
            'source_type': 'sap',
        }, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['created'], 3)
        self.assertEqual(res.data['errors'], 0)
        # Check records are in DB
        self.assertEqual(EmissionRecord.objects.filter(tenant=self.tenant).count(), 3)

    def test_upload_utility_csv(self):
        file = io.BytesIO(UTILITY_VALID_CSV)
        file.name = 'test_utility.csv'
        res = self.client.post('/api/ingestion/upload/', {
            'file': file,
            'source_type': 'utility',
        }, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['created'], 2)

    def test_upload_travel_csv(self):
        file = io.BytesIO(TRAVEL_VALID_CSV)
        file.name = 'test_travel.csv'
        res = self.client.post('/api/ingestion/upload/', {
            'file': file,
            'source_type': 'travel',
        }, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertGreater(res.data['created'], 0)

    def test_upload_invalid_source_type(self):
        file = io.BytesIO(b'col1,col2\nval1,val2')
        file.name = 'test.csv'
        res = self.client.post('/api/ingestion/upload/', {
            'file': file,
            'source_type': 'invalid_source',
        }, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_no_file(self):
        res = self.client.post('/api/ingestion/upload/', {
            'source_type': 'sap',
        }, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_unauthenticated(self):
        self.client.logout()
        file = io.BytesIO(SAP_VALID_CSV)
        file.name = 'test.csv'
        res = self.client.post('/api/ingestion/upload/', {
            'file': file, 'source_type': 'sap',
        }, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_batch_created_on_upload(self):
        file = io.BytesIO(SAP_VALID_CSV)
        file.name = 'batch_test.csv'
        self.client.post('/api/ingestion/upload/', {
            'file': file, 'source_type': 'sap',
        }, format='multipart')
        self.assertEqual(IngestionBatch.objects.filter(tenant=self.tenant).count(), 1)
        batch = IngestionBatch.objects.get(tenant=self.tenant)
        self.assertEqual(batch.status, 'done')
        self.assertEqual(batch.row_count, 3)

    def test_co2e_computed_when_emission_factor_exists(self):
        file = io.BytesIO(SAP_VALID_CSV)
        file.name = 'test.csv'
        self.client.post('/api/ingestion/upload/', {
            'file': file, 'source_type': 'sap',
        }, format='multipart')
        diesel_records = EmissionRecord.objects.filter(tenant=self.tenant, category='diesel')
        self.assertTrue(diesel_records.exists())
        for rec in diesel_records:
            self.assertIsNotNone(rec.kg_co2e)
            self.assertGreater(float(rec.kg_co2e), 0)
