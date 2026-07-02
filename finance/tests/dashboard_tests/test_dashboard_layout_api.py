from django.urls import reverse
from rest_framework import status

from finance.logic.dashboard_layout import (
    DESKTOP_DEFAULT_LAYOUT,
    MOBILE_DEFAULT_LAYOUT,
    WIDGET_CATALOG_IDS,
)
from finance.models import DashboardLayout
from finance.tests.user_tests.user_base import UserBase


class DashboardLayoutApiTests(UserBase):
    def setUp(self):
        super().setUp()
        self.layout_url = reverse("dashboard_layout")
        self.reset_url = reverse("dashboard_layout_reset")
        self.custom_layout = [
            {"widget_id": "KPIRow", "size": "full", "visible": True},
            {"widget_id": "QuickActions", "size": "half", "visible": False},
        ]

    def test_get_desktop_default_when_unsaved(self):
        resp = self.client.get(self.layout_url, {"device_class": "desktop"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["is_default"])
        self.assertEqual(resp.data["device_class"], "desktop")
        self.assertEqual(len(resp.data["layout"]), len(DESKTOP_DEFAULT_LAYOUT))
        self.assertEqual(resp.data["layout"][0]["widget_id"], "QuickActions")

    def test_get_mobile_default_is_sts_first(self):
        resp = self.client.get(self.layout_url, {"device_class": "mobile"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["is_default"])
        self.assertEqual(resp.data["layout"][0]["widget_id"], "KPIRow")
        self.assertEqual(resp.data["layout"][1]["widget_id"], "UpcomingBillsWidget")
        self.assertEqual(len(resp.data["layout"]), len(MOBILE_DEFAULT_LAYOUT))

    def test_put_upserts_layout(self):
        resp = self.client.put(
            self.layout_url,
            {"device_class": "desktop", "layout": self.custom_layout},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["is_default"])
        self.assertEqual(resp.data["layout"], self.custom_layout)
        self.assertIn("updated_at", resp.data)

        get_resp = self.client.get(self.layout_url, {"device_class": "desktop"})
        self.assertFalse(get_resp.data["is_default"])
        self.assertEqual(get_resp.data["layout"], self.custom_layout)

    def test_patch_upserts_layout(self):
        resp = self.client.patch(
            self.layout_url,
            {"device_class": "mobile", "layout": self.custom_layout},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["is_default"])
        self.assertEqual(resp.data["device_class"], "mobile")

    def test_reset_scoped_to_one_variant(self):
        self.client.put(
            self.layout_url,
            {"device_class": "desktop", "layout": self.custom_layout},
            format="json",
        )
        self.client.put(
            self.layout_url,
            {"device_class": "mobile", "layout": self.custom_layout},
            format="json",
        )

        reset_resp = self.client.post(
            self.reset_url,
            {"device_class": "mobile"},
            format="json",
        )
        self.assertEqual(reset_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(reset_resp.data["is_default"])
        self.assertEqual(reset_resp.data["layout"][0]["widget_id"], "KPIRow")

        desktop_resp = self.client.get(self.layout_url, {"device_class": "desktop"})
        self.assertFalse(desktop_resp.data["is_default"])
        self.assertEqual(desktop_resp.data["layout"], self.custom_layout)

    def test_rejects_unknown_widget_id(self):
        resp = self.client.put(
            self.layout_url,
            {
                "device_class": "desktop",
                "layout": [{"widget_id": "NotAWidget", "size": "full", "visible": True}],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_invalid_size(self):
        resp = self.client.put(
            self.layout_url,
            {
                "device_class": "desktop",
                "layout": [{"widget_id": "KPIRow", "size": "quarter", "visible": True}],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_read_filters_unknown_widget_ids_gracefully(self):
        uid = str(self.profile.user_id)
        stale_layout = [
            {"widget_id": "KPIRow", "size": "full", "visible": True},
            {"widget_id": "RetiredWidget", "size": "full", "visible": True},
        ]
        DashboardLayout.objects.create(
            uid=uid,
            device_class="desktop",
            layout=stale_layout,
        )
        resp = self.client.get(self.layout_url, {"device_class": "desktop"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["layout"]), 1)
        self.assertEqual(resp.data["layout"][0]["widget_id"], "KPIRow")

    def test_cross_user_isolation(self):
        other_client = self.client_class()
        other_client.force_authenticate(user=self.other_user)

        self.client.put(
            self.layout_url,
            {"device_class": "desktop", "layout": self.custom_layout},
            format="json",
        )
        other_layout = [{"widget_id": "GoalsWidget", "size": "half", "visible": True}]
        other_client.put(
            self.layout_url,
            {"device_class": "desktop", "layout": other_layout},
            format="json",
        )

        own_resp = self.client.get(self.layout_url, {"device_class": "desktop"})
        other_resp = other_client.get(self.layout_url, {"device_class": "desktop"})

        self.assertEqual(own_resp.data["layout"], self.custom_layout)
        self.assertEqual(other_resp.data["layout"], other_layout)
        self.assertEqual(
            DashboardLayout.objects.filter(uid=str(self.profile.user_id)).count(),
            1,
        )
        self.assertEqual(
            DashboardLayout.objects.filter(uid=self.other_uid).count(),
            1,
        )

    def test_mobile_and_desktop_variants_isolated(self):
        desktop_only = [{"widget_id": "FlowChart", "size": "full", "visible": True}]
        mobile_only = [{"widget_id": "UpcomingBillsWidget", "size": "full", "visible": True}]

        self.client.put(
            self.layout_url,
            {"device_class": "desktop", "layout": desktop_only},
            format="json",
        )
        self.client.put(
            self.layout_url,
            {"device_class": "mobile", "layout": mobile_only},
            format="json",
        )

        desktop_resp = self.client.get(self.layout_url, {"device_class": "desktop"})
        mobile_resp = self.client.get(self.layout_url, {"device_class": "mobile"})

        self.assertEqual(desktop_resp.data["layout"], desktop_only)
        self.assertEqual(mobile_resp.data["layout"], mobile_only)

    def test_requires_device_class_on_get(self):
        resp = self.client.get(self.layout_url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_catalog_covers_all_widget_ids(self):
        self.assertEqual(len(WIDGET_CATALOG_IDS), 12)
