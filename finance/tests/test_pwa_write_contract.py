"""D2 PWA write contract: idempotency, allowlist, client build 409, health payload."""

import json
import uuid

from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from rest_framework_simplejwt.tokens import RefreshToken

from finance.models import Transaction
from finance.tests.transaction_tests.transaction_base import TransactionBase


def _resp_payload(response):
    if hasattr(response, "data"):
        return response.data
    return json.loads(response.content.decode("utf-8"))


class JwtAuthTransactionBase(TransactionBase):
    """JWT in Authorization so PwaWriteContractMiddleware can resolve the user."""

    def setUp(self):
        super().setUp()
        token = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")


class PwaIdempotencyTransactionTests(JwtAuthTransactionBase):
    def test_post_transaction_idempotent_replay_same_body(self):
        key = str(uuid.uuid4())
        r1 = self.client.post(
            self.url,
            self.expense_data,
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
            HTTP_X_CLIENT_BUILD="9.9.9",
        )
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED, msg=_resp_payload(r1))
        before = Transaction.objects.filter(uid=str(self.profile.user_id)).count()
        r2 = self.client.post(
            self.url,
            self.expense_data,
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
            HTTP_X_CLIENT_BUILD="9.9.9",
        )
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED, msg=_resp_payload(r2))
        after = Transaction.objects.filter(uid=str(self.profile.user_id)).count()
        self.assertEqual(before, after)
        self.assertEqual(r1.content, r2.content)

    def test_idempotency_key_on_non_allowlisted_path_returns_400(self):
        key = str(uuid.uuid4())
        url = reverse("categories")
        r = self.client.post(
            url,
            {"name": "cat-from-pwa-test", "amount": "1.00"},
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
            HTTP_X_CLIENT_BUILD="9.9.9",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not supported", str(_resp_payload(r)).lower())


@override_settings(CLIENT_BUILD_MIN_WRITE="5.0.0")
class PwaClientBuildEnforcementTests(JwtAuthTransactionBase):
    def test_missing_client_build_returns_409_when_min_configured(self):
        r = self.client.post(self.url, self.expense_data, format="json")
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(_resp_payload(r).get("code"), "CLIENT_BUILD_UNSUPPORTED")

    def test_low_client_build_returns_409(self):
        r = self.client.post(
            self.url,
            self.expense_data,
            format="json",
            HTTP_X_CLIENT_BUILD="1.0.0",
        )
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(_resp_payload(r).get("code"), "CLIENT_BUILD_UNSUPPORTED")
        self.assertEqual(_resp_payload(r).get("min_supported_build"), "5.0.0")

    def test_acceptable_client_build_passes(self):
        r = self.client.post(
            self.url,
            self.expense_data,
            format="json",
            HTTP_X_CLIENT_BUILD="5.0.0",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, msg=_resp_payload(r))


class PwaDeleteIdempotentTests(JwtAuthTransactionBase):
    def test_delete_missing_transaction_with_idempotency_key_returns_idempotent_shape(self):
        key = str(uuid.uuid4())
        url = reverse("transaction_detail", kwargs={"tx_id": "2099-01-01-notreal"})
        r = self.client.delete(url, HTTP_IDEMPOTENCY_KEY=key)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        body = _resp_payload(r)
        self.assertTrue(body.get("idempotent"))
        self.assertEqual(body.get("tx_id"), "2099-01-01-notreal")


class ApiHealthPayloadTests(JwtAuthTransactionBase):
    @override_settings(CLIENT_BUILD_MIN_WRITE="3.1.0", API_SERVER_BUILD="ci-123")
    def test_health_includes_build_fields(self):
        r = self.client.get(reverse("health"))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.json().get("status"), "ok")
        self.assertEqual(r.json().get("api_server_build"), "ci-123")
        self.assertEqual(r.json().get("min_client_build_write"), "3.1.0")
