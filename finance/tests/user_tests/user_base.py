from decimal import Decimal
from datetime import date

from django.urls import reverse

from finance.factories import PaymentSourceFactory, TransactionFactory, UserFactory
from finance.models import Category, PaymentSource, Tag, UpcomingExpense
from finance.tests.basetest import BaseTestCase


class UserBase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.user_url = reverse("user")
        self.tx_detail_url_name = "transaction_detail_update_delete"

        # PaymentSource.source is globally unique in this schema; free reserved defaults
        # so a second user can be created for ownership-boundary tests.
        PaymentSource.objects.filter(uid=str(self.profile.user_id), source="cash").update(source=f"cash-{self.profile.user_id}")
        PaymentSource.objects.filter(uid=str(self.profile.user_id), source="unknown").update(source=f"unknown-{self.profile.user_id}")

        self.other_user = UserFactory()
        self.other_profile = self.other_user.appprofile
        self.other_uid = str(self.other_profile.user_id)

        PaymentSourceFactory.create(
            uid=self.other_uid, source="other-wallet", acc_type="CASH", amount=Decimal("100.00"), currency="USD"
        )
        TransactionFactory.create(
            uid=self.other_uid,
            date=date(2025, 1, 1),
            created_on=date(2025, 1, 1),
            tx_id="2025-01-01-OTHERTX1",
            source="other-wallet",
            currency="USD",
            tx_type="INCOME",
            amount=Decimal("10.00"),
            tags=[],
        )
        Category.objects.create(uid=self.other_uid, name="other-cat")
        Tag.objects.create(uid=self.other_uid, tags=["other-tag"])
        UpcomingExpense.objects.create(
            uid=self.other_uid,
            name="other-bill",
            amount=Decimal("3.00"),
            currency="USD",
            due_date="2025-01-01",
            start_date="2025-01-01",
        )
