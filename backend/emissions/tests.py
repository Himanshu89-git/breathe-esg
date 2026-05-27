from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date
from accounts.models import Tenant, User
from emissions.models import EmissionFactor, IngestionBatch, EmissionRecord


def make_tenant_and_user():
    tenant = Tenant.objects.create(name='Acme', slug='acme')
    user = User.objects.create_user(
        username='analyst', password='pass', tenant=tenant, role=User.ROLE_ANALYST
    )
    return tenant, user


def make_batch(tenant, user, source='sap'):
    return IngestionBatch.objects.create(
        tenant=tenant, uploaded_by=user, source_type=source,
        status=IngestionBatch.STATUS_DONE, file_name='test.csv',
        row_count=1,
    )


def make_record(tenant, batch, **kwargs):
    defaults = dict(
        scope='1', source_type='sap', category='diesel',
        activity_date=date(2024, 1, 15),
        quantity=1000, unit='litre',
        status=EmissionRecord.STATUS_PENDING,
        raw_data={},
    )
    defaults.update(kwargs)
    return EmissionRecord.objects.create(tenant=tenant, batch=batch, **defaults)


class EmissionRecordTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tenant, self.user = make_tenant_and_user()
        self.client.force_authenticate(user=self.user)
        self.batch = make_batch(self.tenant, self.user)

    def test_list_records(self):
        make_record(self.tenant, self.batch)
        make_record(self.tenant, self.batch, scope='2', source_type='utility', category='electricity', unit='kWh')
        res = self.client.get(reverse('records-list'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 2)

    def test_tenant_isolation(self):
        """Records from another tenant must not appear."""
        other_tenant = Tenant.objects.create(name='Other', slug='other')
        other_user = User.objects.create_user(username='other', password='pass', tenant=other_tenant)
        other_batch = make_batch(other_tenant, other_user)
        make_record(other_tenant, other_batch)

        make_record(self.tenant, self.batch)
        res = self.client.get(reverse('records-list'))
        self.assertEqual(res.data['count'], 1)

    def test_filter_by_scope(self):
        make_record(self.tenant, self.batch, scope='1')
        make_record(self.tenant, self.batch, scope='2', source_type='utility', category='electricity', unit='kWh')
        make_record(self.tenant, self.batch, scope='3', source_type='travel', category='flight', unit='passenger-km')

        res = self.client.get(reverse('records-list'), {'scope': '1'})
        self.assertEqual(res.data['count'], 1)

    def test_filter_by_status(self):
        make_record(self.tenant, self.batch, status='pending')
        make_record(self.tenant, self.batch, status='approved')
        res = self.client.get(reverse('records-list'), {'status': 'pending'})
        self.assertEqual(res.data['count'], 1)

    def test_filter_suspicious(self):
        make_record(self.tenant, self.batch, is_suspicious=False)
        make_record(self.tenant, self.batch, is_suspicious=True, suspicion_reason='Very large quantity')
        res = self.client.get(reverse('records-list'), {'is_suspicious': 'true'})
        self.assertEqual(res.data['count'], 1)

    def test_review_approve(self):
        rec = make_record(self.tenant, self.batch)
        res = self.client.post(
            reverse('records-review', kwargs={'pk': rec.id}),
            {'action': 'approve', 'notes': 'Looks correct'},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'approved')
        self.assertEqual(res.data['review_notes'], 'Looks correct')

    def test_review_flag(self):
        rec = make_record(self.tenant, self.batch)
        res = self.client.post(
            reverse('records-review', kwargs={'pk': rec.id}),
            {'action': 'flag', 'notes': 'Needs verification'},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'flagged')

    def test_review_reject(self):
        rec = make_record(self.tenant, self.batch)
        res = self.client.post(
            reverse('records-review', kwargs={'pk': rec.id}),
            {'action': 'reject', 'notes': 'Duplicate row'},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'rejected')

    def test_bulk_approve(self):
        r1 = make_record(self.tenant, self.batch)
        r2 = make_record(self.tenant, self.batch)
        make_record(self.tenant, self.batch, status='approved')  # already approved
        res = self.client.post(
            reverse('records-bulk-approve'),
            {'ids': [str(r1.id), str(r2.id)]},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['approved'], 2)

    def test_stats_endpoint(self):
        make_record(self.tenant, self.batch, kg_co2e=500, scope='1')
        make_record(self.tenant, self.batch, kg_co2e=300, scope='2',
                    source_type='utility', category='electricity', unit='kWh')
        res = self.client.get(reverse('records-stats'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['total_records'], 2)
        self.assertAlmostEqual(res.data['total_kg_co2e'], 800.0)
        self.assertIn('by_scope', res.data)
        self.assertIn('by_source', res.data)


class EmissionFactorTests(TestCase):
    def test_emission_factor_creation(self):
        ef = EmissionFactor.objects.create(
            source_type='sap', activity='diesel', unit='litre',
            kg_co2e_per_unit=2.68861, region='GLOBAL',
        )
        self.assertEqual(str(ef), 'diesel (litre) = 2.688610 kgCO2e')

    def test_unique_together(self):
        EmissionFactor.objects.create(
            source_type='sap', activity='diesel', unit='litre',
            kg_co2e_per_unit=2.68861, region='GLOBAL',
        )
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            EmissionFactor.objects.create(
                source_type='sap', activity='diesel', unit='litre',
                kg_co2e_per_unit=2.68861, region='GLOBAL',
            )
