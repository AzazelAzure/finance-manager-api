from __future__ import annotations

import csv
import io
from datetime import datetime

from django.http import StreamingHttpResponse
from loguru import logger
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from finance.models import Transaction

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
