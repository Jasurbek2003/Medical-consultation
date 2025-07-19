from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


class AuthenticationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_user_registration(self):
        """Test user registration"""
        data = {
            'phone': '+998901234567',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
            'user_type': 'patient'
        }
        response = self.client.post('/api/v1/users/api/users/register/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_doctor_registration(self):
        """Test doctor registration"""
        data = {
            'phone': '+998901234568',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'first_name': 'Test',
            'last_name': 'Doctor',
            'specialty': 'terapevt',
            'license_number': 'DOC123456',
            'experience': 5,
            'education': 'Tashkent Medical Academy',
            'workplace': 'City Hospital',
            'consultation_price': 50000
        }
        response = self.client.post('/api/v1/users/api/users/register_doctor/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_doctor_approval(self):
        """Test admin approving doctor"""
        # Create admin user
        admin = User.objects.create_user(
            phone='+998901234569',
            password='admin123',
            user_type='admin',
            first_name='Admin',
            last_name='User'
        )

        # Create doctor user
        doctor_user = User.objects.create_user(
            phone='+998901234570',
            password='doctor123',
            user_type='doctor',
            first_name='Doctor',
            last_name='User'
        )

        # Login as admin
        self.client.force_authenticate(user=admin)

        # Approve doctor
        response = self.client.post(f'/api/v1/users/api/users/{doctor_user.id}/approve_doctor/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify doctor is approved
        doctor_user.refresh_from_db()
        self.assertTrue(doctor_user.is_approved_by_admin)