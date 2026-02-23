from rest_framework.test import APITestCase
from finance.factories import (
    UserFactory, 
    PaymentSourceFactory, 
    TagFactory
)
from finance.models import CurrentAsset
from loguru import logger

class BaseTestCase(APITestCase):
    """
    Base test case for all tests.
    Sets up the user and profile.
    """
    def setUp(self):
        self.user = UserFactory()
        self.profile = self.user.appprofile
        self.client.force_authenticate(user=self.user)
        self.source = PaymentSourceFactory.create(uid=self.profile)
        self.currency = self.profile.base_currency
        self.asset = CurrentAsset.objects.for_user(self.profile).get_asset(source=self.source).get()
        self.asset.amount = 100
        self.asset.currency = self.currency
        self.asset.save()
        self.tags = TagFactory.create_batch(2, uid=self.profile)
        self.tag_list = [tag.name for tag in self.tags]
        logger.info(f"Setup complete.  Tags: {self.tag_list}")