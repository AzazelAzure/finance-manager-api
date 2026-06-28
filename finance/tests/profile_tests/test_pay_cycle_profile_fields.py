from datetime import date

from django.test import TestCase

from finance.factories import UserFactory
from finance.models import AppProfile


class AppProfilePayCycleFieldTests(TestCase):
    def test_new_profile_defaults_to_calendar_month(self):
        user = UserFactory()
        profile = user.appprofile
        profile.refresh_from_db()
        self.assertEqual(profile.sts_window_mode, AppProfile.StsWindowMode.CALENDAR_MONTH)
        self.assertIsNone(profile.pay_cycle_frequency)
        self.assertIsNone(profile.pay_cycle_anchor_date)

    def test_pay_cycle_fields_persist(self):
        user = UserFactory()
        profile = user.appprofile
        profile.sts_window_mode = AppProfile.StsWindowMode.PAY_CYCLE
        profile.pay_cycle_frequency = AppProfile.PayCycleFrequency.BIWEEKLY
        profile.pay_cycle_anchor_date = date(2026, 7, 15)
        profile.save(
            update_fields=[
                "sts_window_mode",
                "pay_cycle_frequency",
                "pay_cycle_anchor_date",
            ]
        )
        profile.refresh_from_db()
        self.assertEqual(profile.sts_window_mode, AppProfile.StsWindowMode.PAY_CYCLE)
        self.assertEqual(profile.pay_cycle_frequency, AppProfile.PayCycleFrequency.BIWEEKLY)
        self.assertEqual(profile.pay_cycle_anchor_date, date(2026, 7, 15))
