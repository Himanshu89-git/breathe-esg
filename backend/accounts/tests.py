from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import Tenant, User


class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tenant = Tenant.objects.create(name='Test Corp', slug='test-corp')
        self.user = User.objects.create_user(
            username='testanalyst',
            password='testpass123',
            tenant=self.tenant,
            role=User.ROLE_ANALYST,
        )

    def test_obtain_token(self):
        res = self.client.post(reverse('token_obtain_pair'), {
            'username': 'testanalyst',
            'password': 'testpass123',
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access', res.data)
        self.assertIn('refresh', res.data)

    def test_me_endpoint_authenticated(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.get(reverse('me'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['username'], 'testanalyst')
        self.assertEqual(res.data['role'], 'analyst')
        self.assertEqual(res.data['tenant']['slug'], 'test-corp')

    def test_me_endpoint_unauthenticated(self):
        res = self.client.get(reverse('me'))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh(self):
        res = self.client.post(reverse('token_obtain_pair'), {
            'username': 'testanalyst', 'password': 'testpass123',
        })
        refresh = res.data['refresh']
        res2 = self.client.post(reverse('token_refresh'), {'refresh': refresh})
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertIn('access', res2.data)
