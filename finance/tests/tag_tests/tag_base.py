from django.urls import reverse

from finance.tests.basetest import BaseTestCase


class TagBase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("tags")
