import os

from rest_framework.test import APITestCase
from finance.factories import (
    UserFactory, 
    PaymentSourceFactory, 
    TagFactory,
    CategoryFactory
)
from loguru import logger
from pyinstrument import Profiler

PROFILER_HTML_DIR = "profiler_html"


class BaseTestCase(APITestCase):
    """
    Base test case for all tests.
    Sets up the user and profile.
    """
    def setUp(self):
        self.profiler = Profiler()
        self.profiler.start()
        self.addCleanup(self._profiler_log)
        self.user = UserFactory()
        self.profile = self.user.appprofile
        self.client.force_authenticate(user=self.user)
        self.sources = PaymentSourceFactory.create(uid=self.profile.user_id)
        self.currency = self.profile.base_currency
        self.categories = CategoryFactory.create_batch(3, uid=self.profile.user_id)
        self.tags = TagFactory.create_batch(2, uid=self.profile.user_id)
        self.tag_list = [tag.tags for tag in self.tags]
        logger.info(f"Setup complete.  Tags: {self.tag_list}")
    
    def tearDown(self):
        super().tearDown()

    def _profiler_log(self):
        self.profiler.stop()
        os.makedirs(PROFILER_HTML_DIR, exist_ok=True)
        path = os.path.join(PROFILER_HTML_DIR, f"profiler_{self.id()}.html")
        with open(path, "w") as f:
            f.write(self.profiler.output_html())