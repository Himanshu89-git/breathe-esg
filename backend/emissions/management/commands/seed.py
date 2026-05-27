"""
Management command to seed the database with:
- Emission factors (DEFRA 2023)
- A demo tenant and analyst user
- Sample emission records across all three source types
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
import random
import uuid

from accounts.models import Tenant, User
from emissions.models import EmissionFactor, IngestionBatch, EmissionRecord


EMISSION_FACTORS = [
    # Scope 1 — Fuel
    {'source_type': 'sap', 'activity': 'diesel', 'unit': 'litre', 'kg_co2e_per_unit': 2.68861, 'region': 'GLOBAL', 'source_reference': 'DEFRA 2023'},
    {'source_type': 'sap', 'activity': 'petrol', 'unit': 'litre', 'kg_co2e_per_unit': 2.31390, 'region': 'GLOBAL', 'source_reference': 'DEFRA 2023'},
    {'source_type': 'sap', 'activity': 'lpg', 'unit': 'litre', 'kg_co2e_per_unit': 1.55540, 'region': 'GLOBAL', 'source_reference': 'DEFRA 2023'},
    {'source_type': 'sap', 'activity': 'natural_gas', 'unit': 'kWh', 'kg_co2e_per_unit': 0.20274, 'region': 'GLOBAL', 'source_reference': 'DEFRA 2023'},
    {'source_type': 'sap', 'activity': 'coal', 'unit': 'kg', 'kg_co2e_per_unit': 2.42300, 'region': 'GLOBAL', 'source_reference': 'DEFRA 2023'},
    # Scope 2 — Electricity
    {'source_type': 'utility', 'activity': 'electricity', 'unit': 'kWh', 'kg_co2e_per_unit': 0.23314, 'region': 'IN', 'source_reference': 'CEA India 2023'},
    {'source_type': 'utility', 'activity': 'electricity', 'unit': 'kWh', 'kg_co2e_per_unit': 0.23314, 'region': 'GLOBAL', 'source_reference': 'DEFRA 2023'},
    {'source_type': 'utility', 'activity': 'electricity', 'unit': 'kWh', 'kg_co2e_per_unit': 0.23392, 'region': 'GB', 'source_reference': 'DEFRA 2023'},
    {'source_type': 'utility', 'activity': 'electricity', 'unit': 'kWh', 'kg_co2e_per_unit': 0.38600, 'region': 'US', 'source_reference': 'EPA eGRID 2022'},
    # Scope 3 — Travel
    {'source_type': 'travel', 'activity': 'flight', 'unit': 'passenger-km', 'kg_co2e_per_unit': 0.25510, 'region': 'GLOBAL', 'source_reference': 'DEFRA 2023 short-haul economy+RFI'},
    {'source_type': 'travel', 'activity': 'hotel', 'unit': 'room-night', 'kg_co2e_per_unit': 31.20, 'region': 'GLOBAL', 'source_reference': 'DEFRA 2023'},
    {'source_type': 'travel', 'activity': 'car_rental', 'unit': 'km', 'kg_co2e_per_unit': 0.19400, 'region': 'GLOBAL', 'source_reference': 'DEFRA 2023 average car'},
    {'source_type': 'travel', 'activity': 'taxi', 'unit': 'km', 'kg_co2e_per_unit': 0.21000, 'region': 'GLOBAL', 'source_reference': 'DEFRA 2023'},
    {'source_type': 'travel', 'activity': 'rail', 'unit': 'passenger-km', 'kg_co2e_per_unit': 0.03700, 'region': 'GLOBAL', 'source_reference': 'DEFRA 2023'},
]

SAP_RECORDS = [
    ('diesel', '1', 15000, 'litre', 'PLANT-DEL', 'CC-OPS-01', 'IN'),
    ('diesel', '1', 8200, 'litre', 'PLANT-BOM', 'CC-OPS-02', 'IN'),
    ('petrol', '1', 4500, 'litre', 'PLANT-BLR', 'CC-FLEET', 'IN'),
    ('diesel', '1', 120000, 'litre', 'PLANT-DEL', 'CC-OPS-01', 'IN'),  # suspicious
    ('natural_gas', '1', 25000, 'kWh', 'PLANT-DEL', 'CC-UTIL', 'IN'),
    ('lpg', '1', 1200, 'litre', 'PLANT-MAA', 'CC-KITCHEN', 'IN'),
    ('diesel', '1', 9800, 'litre', 'PLANT-HYD', 'CC-OPS-03', 'IN'),
    ('coal', '1', 5000, 'kg', 'PLANT-DEL', 'CC-BOILER', 'IN'),
]

UTILITY_RECORDS = [
    ('electricity', '2', 45000, 'kWh', 'HQ Tower Floor 1-5', 'ACC-001', 'IN'),
    ('electricity', '2', 38500, 'kWh', 'HQ Tower Floor 6-10', 'ACC-002', 'IN'),
    ('electricity', '2', 12000, 'kWh', 'Warehouse Mumbai', 'ACC-003', 'IN'),
    ('electricity', '2', 0, 'kWh', 'Satellite Office Pune', 'ACC-004', 'IN'),  # suspicious - zero
    ('electricity', '2', 620000, 'kWh', 'Data Centre Delhi', 'ACC-005', 'IN'),  # suspicious - very high
    ('electricity', '2', 9500, 'kWh', 'Factory Bangalore', 'ACC-006', 'IN'),
    ('electricity', '2', 14200, 'kWh', 'HQ Tower Floor 1-5', 'ACC-001', 'IN'),
]

TRAVEL_RECORDS = [
    ('flight', '3', 2200, 'passenger-km', 'Rahul Sharma', '', 'IN'),
    ('flight', '3', 6800, 'passenger-km', 'Priya Mehta', '', 'IN'),
    ('flight', '3', 18500, 'passenger-km', 'Amit Kumar', '', 'IN'),  # suspicious - very long
    ('hotel', '3', 3, 'room-night', 'Rahul Sharma', '', 'IN'),
    ('hotel', '3', 7, 'room-night', 'Priya Mehta', '', 'IN'),
    ('car_rental', '3', 450, 'km', 'Vikram Singh', '', 'IN'),
    ('taxi', '3', 85, 'km', 'Sonia Gupta', '', 'IN'),
    ('rail', '3', 1400, 'passenger-km', 'Amit Kumar', '', 'IN'),
    ('flight', '3', 1100, 'passenger-km', 'Neha Verma', '', 'IN'),
    ('hotel', '3', 2, 'room-night', 'Vikram Singh', '', 'IN'),
]


class Command(BaseCommand):
    help = 'Seed database with emission factors and demo data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding emission factors...')
        for ef_data in EMISSION_FACTORS:
            EmissionFactor.objects.get_or_create(
                source_type=ef_data['source_type'],
                activity=ef_data['activity'],
                unit=ef_data['unit'],
                region=ef_data.get('region', 'GLOBAL'),
                defaults={'kg_co2e_per_unit': ef_data['kg_co2e_per_unit'],
                          'source_reference': ef_data.get('source_reference', '')}
            )
        self.stdout.write(self.style.SUCCESS(f'  {len(EMISSION_FACTORS)} emission factors seeded'))

        # Create demo tenant
        tenant, _ = Tenant.objects.get_or_create(
            slug='acme-corp',
            defaults={'name': 'ACME Corporation'}
        )

        # Create demo users
        analyst, created = User.objects.get_or_create(
            username='analyst',
            defaults={
                'email': 'analyst@acme.com',
                'first_name': 'Ananya',
                'last_name': 'Sharma',
                'tenant': tenant,
                'role': User.ROLE_ANALYST,
            }
        )
        if created:
            analyst.set_password('analyst123')
            analyst.save()

        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@acme.com',
                'first_name': 'Arjun',
                'last_name': 'Patel',
                'tenant': tenant,
                'role': User.ROLE_ADMIN,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()

        self.stdout.write(f'  Tenant: {tenant.name}')
        self.stdout.write(f'  Users: analyst/analyst123, admin/admin123')

        # Create sample batches and records
        base_date = date.today() - timedelta(days=60)

        def make_batch(source_type, day_offset=0):
            return IngestionBatch.objects.create(
                tenant=tenant,
                uploaded_by=analyst,
                source_type=source_type,
                status=IngestionBatch.STATUS_DONE,
                file_name=f'sample_{source_type}_{base_date + timedelta(days=day_offset)}.csv',
                reporting_period_start=base_date,
                reporting_period_end=base_date + timedelta(days=30),
                processed_at=timezone.now(),
            )

        sap_batch = make_batch('sap', 0)
        util_batch = make_batch('utility', 5)
        travel_batch = make_batch('travel', 10)

        ef_cache = {}
        def get_ef(source, activity, unit):
            key = (source, activity, unit)
            if key not in ef_cache:
                ef_cache[key] = EmissionFactor.objects.filter(
                    source_type=source, activity=activity, unit=unit
                ).first()
            return ef_cache[key]

        statuses = [
            EmissionRecord.STATUS_PENDING,
            EmissionRecord.STATUS_PENDING,
            EmissionRecord.STATUS_PENDING,
            EmissionRecord.STATUS_APPROVED,
            EmissionRecord.STATUS_FLAGGED,
        ]

        def create_records(batch, records_data, source_type):
            for i, (cat, scope, qty, unit, facility, cc, country) in enumerate(records_data):
                ef = get_ef(source_type, cat, unit)
                is_suspicious = False
                suspicion_reason = ''
                if source_type == 'sap' and unit == 'litre' and qty > 100000:
                    is_suspicious = True
                    suspicion_reason = f'Unusually large fuel quantity: {qty} litres'
                if source_type == 'utility' and qty == 0:
                    is_suspicious = True
                    suspicion_reason = 'Zero kWh consumption'
                if source_type == 'utility' and qty > 500000:
                    is_suspicious = True
                    suspicion_reason = f'Very high consumption: {qty} kWh'
                if source_type == 'travel' and cat == 'flight' and qty > 18000:
                    is_suspicious = True
                    suspicion_reason = f'Exceptionally long flight: {qty} km'

                kg_co2e = None
                if ef and qty:
                    kg_co2e = round(float(qty) * float(ef.kg_co2e_per_unit), 4)

                rec_status = random.choice(statuses)
                EmissionRecord.objects.create(
                    tenant=tenant,
                    batch=batch,
                    emission_factor=ef,
                    scope=scope,
                    source_type=source_type,
                    category=cat,
                    activity_date=base_date + timedelta(days=i * 3),
                    quantity=qty,
                    unit=unit,
                    quantity_original=qty,
                    unit_original=unit,
                    facility=facility,
                    cost_center=cc,
                    country=country,
                    kg_co2e=kg_co2e,
                    is_suspicious=is_suspicious,
                    suspicion_reason=suspicion_reason,
                    status=rec_status,
                    raw_data={'seeded': True, 'category': cat},
                )

        create_records(sap_batch, SAP_RECORDS, 'sap')
        create_records(util_batch, UTILITY_RECORDS, 'utility')
        create_records(travel_batch, TRAVEL_RECORDS, 'travel')

        total = len(SAP_RECORDS) + len(UTILITY_RECORDS) + len(TRAVEL_RECORDS)
        self.stdout.write(self.style.SUCCESS(f'  {total} sample emission records created'))
        self.stdout.write(self.style.SUCCESS('✓ Seed complete!'))
