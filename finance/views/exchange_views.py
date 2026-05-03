"""Authenticated read-only exchange rate matrix for offline PWA clients."""

from __future__ import annotations

import time
from decimal import Decimal

from drf_spectacular.utils import OpenApiParameter, extend_schema
from finance.logic.convert_currency import convert_currency
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class ExchangeRatesMatrixView(APIView):
    """
    Return pairwise conversion factors among a caller-supplied currency set.

    Each rate is ``convert_currency(Decimal("1"), from_ccy, to_ccy)`` using the
    same ECB-backed converter as transaction math. Clients should request only
    currencies they need (e.g. profile base + source + recent tx currencies).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="finance_exchange_rates_matrix",
        summary="Pairwise exchange rates for a currency subset",
        parameters=[
            OpenApiParameter(
                name="currencies",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Comma-separated ISO 4217 codes (e.g. USD,PHP,EUR). Max 24.",
                required=True,
            ),
        ],
        tags=["Finance"],
    )
    def get(self, request):
        raw = (request.query_params.get("currencies") or "").strip()
        if not raw:
            return Response(
                {"rates": {}, "fetched_at_ms": int(time.time() * 1000), "currencies": []},
                status=200,
            )
        parts = [p.strip().upper()[:3] for p in raw.split(",") if p.strip()]
        codes = sorted(set(parts))
        if len(codes) > 24:
            return Response({"detail": "Too many currencies (max 24)."}, status=400)

        rates: dict[str, float] = {}
        for a in codes:
            for b in codes:
                if a == b:
                    continue
                key = f"{a}:{b}"
                try:
                    r = convert_currency(Decimal("1"), a, b)
                    rates[key] = float(r)
                except (FileNotFoundError, ValueError, TypeError, KeyError):
                    continue

        return Response(
            {
                "rates": rates,
                "fetched_at_ms": int(time.time() * 1000),
                "currencies": codes,
            },
            status=200,
        )
