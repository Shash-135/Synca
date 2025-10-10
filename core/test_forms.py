from django.test import TestCase
from .forms import RegisterForm

class RegisterFormTest(TestCase):
    def test_password_mismatch(self):
        form = RegisterForm(data={
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'abc123',
            'password2': 'xyz789',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)
