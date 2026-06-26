import os
import uuid

from django.conf import settings
from django.core import mail
from django.test import TestCase, override_settings
from loguru import logger

from finance.tasks.notify import notify_operator
from finance.utils.notify_format import build_notify_body, build_notify_subject


class NotifyFormatTestCase(TestCase):
    def test_subject_and_body_contract(self):
        subject = build_notify_subject("BUG_REPORT", "high")
        self.assertIn("[FM-NOTIFY]", subject)
        self.assertIn("BUG_REPORT", subject)
        body = build_notify_body(
            event_type="BUG_REPORT",
            severity="high",
            user_ref="00000000-0000-0000-0000-000000000001",
            file_paths=["logs/diagnostic/00000000-0000-0000-0000-000000000001.log"],
            notes="Test",
        )
        self.assertIn("User-Ref: 00000000-0000-0000-0000-000000000001", body)
        self.assertIn("No PII", body)


class NotifyOperatorTaskTestCase(TestCase):
    def test_notify_operator_sends_mail(self):
        mail.outbox.clear()
        with override_settings(OPERATOR_NOTIFY_EMAIL="operator@financemanager.local"):
            result = notify_operator.run(
                event_type="BUG_REPORT",
                severity="high",
                user_ref=str(uuid.uuid4()),
                file_paths=["logs/diagnostic/example.log"],
                notes="Smoke test",
            )
        self.assertEqual(result, "sent:BUG_REPORT")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("[FM-NOTIFY]", mail.outbox[0].subject)
