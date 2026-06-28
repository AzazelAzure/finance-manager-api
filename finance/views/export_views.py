import csv
import io
import json
from datetime import datetime

from django.http import HttpResponse, StreamingHttpResponse
from django.utils import timezone
from loguru import logger
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from finance.models import Category, PaymentSource, Tag, Transaction, UpcomingExpense

CSV_HEADERS = [
    "Date",
    "Amount",
    "Currency",
    "Source",
    "Category",
    "Tags",
    "Notes",
    "Linked Bill",
]


def _parse_optional_date(raw: str | None, param_name: str) -> tuple[datetime.date | None, Response | None]:
    if not raw:
        return None, None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date(), None
    except ValueError:
        return None, Response(
            {param_name: "Invalid date format. Use YYYY-MM-DD."},
            status=status.HTTP_400_BAD_REQUEST,
        )


def _format_tags(tags) -> str:
    if not tags:
        return ""
    if isinstance(tags, list):
        return "|".join(str(t) for t in tags)
    return str(tags)


def _transaction_csv_row(tx: Transaction) -> list:
    return [
        tx.date.isoformat(),
        str(tx.amount),
        tx.currency or "",
        tx.source or "",
        tx.category or "",
        _format_tags(tx.tags),
        tx.description or "",
        tx.bill or "",
    ]


class TransactionCsvExportView(APIView):
    """Export the authenticated user's transactions as CSV (F-010 T01)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.appprofile
        uid = str(profile.user_id)

        date_from_raw = request.query_params.get("date_from")
        date_to_raw = request.query_params.get("date_to")

        date_from, err = _parse_optional_date(date_from_raw, "date_from")
        if err:
            return err
        date_to, err = _parse_optional_date(date_to_raw, "date_to")
        if err:
            return err

        queryset = Transaction.objects.for_user(uid).order_by("date", "tx_id")
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        row_count = queryset.count()

        def csv_rows():
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(CSV_HEADERS)
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

            for tx in queryset.iterator():
                writer.writerow(_transaction_csv_row(tx))
                yield buffer.getvalue()
                buffer.seek(0)
                buffer.truncate(0)

        today = datetime.now().strftime("%Y%m%d")
        filename = f"hfm_transactions_{today}.csv"
        response = StreamingHttpResponse(csv_rows(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        logger.info(
            "export_csv user={} rows={} date_from={} date_to={}",
            uid,
            row_count,
            date_from_raw or "",
            date_to_raw or "",
        )
        return response


def _profile_backup_dict(profile) -> dict:
    return {
        "user_id": str(profile.user_id),
        "base_currency": profile.base_currency,
        "timezone": profile.timezone,
        "start_of_week": profile.start_of_week,
        "sts_window_mode": profile.sts_window_mode,
        "pay_cycle_frequency": profile.pay_cycle_frequency,
        "pay_cycle_anchor_date": profile.pay_cycle_anchor_date,
        "spend_accounts": profile.spend_accounts,
    }


class FullBackupExportView(APIView):
    """Export the authenticated user's full finance dataset as JSON (F-010 T02)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.appprofile
        uid = str(profile.user_id)

        transactions = list(Transaction.objects.for_user(uid).order_by("date", "tx_id").values())
        sources = list(PaymentSource.objects.filter(uid=uid).values())
        categories = list(Category.objects.filter(uid=uid).values())
        tags = list(Tag.objects.filter(uid=uid).values())
        upcoming_expenses = list(UpcomingExpense.objects.filter(uid=uid).order_by("due_date").values())

        payload = {
            "export_version": "1",
            "exported_at": timezone.now().isoformat(),
            "profile": _profile_backup_dict(profile),
            "sources": sources,
            "categories": categories,
            "tags": tags,
            "transactions": transactions,
            "upcoming_expenses": upcoming_expenses,
        }

        today = datetime.now().strftime("%Y%m%d")
        filename = f"hfm_backup_{today}.json"
        body = json.dumps(payload, default=str)
        response = HttpResponse(body, content_type="application/json")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        logger.info(
            "export_full_backup user={} tx_count={} src_count={} ue_count={}",
            uid,
            len(transactions),
            len(sources),
            len(upcoming_expenses),
        )
        return response
