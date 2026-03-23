from django.urls import reverse

from finance.tests.basetest import BaseTestCase


class ProfileBase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.profile_url = reverse("appprofile")
        self.snapshot_url = reverse("appprofile_snapshot")
