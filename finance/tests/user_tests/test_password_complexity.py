from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from finance.validators.password_complexity import ComplexPasswordValidator


class ComplexPasswordValidatorTests(TestCase):
    def setUp(self):
        self.validator = ComplexPasswordValidator()
        self.user = User(username="complexity-user", email="complexity@example.com")

    def test_accepts_strong_password(self):
        self.validator.validate("StrongPass1!", self.user)

    def test_rejects_missing_uppercase(self):
        with self.assertRaises(ValidationError):
            self.validator.validate("weakpass1!", self.user)

    def test_rejects_missing_special(self):
        with self.assertRaises(ValidationError):
            self.validator.validate("WeakPass1234", self.user)
