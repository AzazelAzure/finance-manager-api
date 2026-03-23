from __future__ import annotations

import os
import re
from typing import Callable

from django.conf import settings
from django.db import connection
from loguru import logger


class DBHitCounterMiddleware:
    """
    Logs total SQL execute calls executed during a single API request.

    Notes:
    - This counts database "hits" as the number of SQL execution wrapper invocations
      (i.e., execute/ executemany) handled by Django's database backend.
    - Output is a single Loguru INFO line per request.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, "DB_HIT_LOGGING_ENABLED", False):
            return self.get_response(request)

        db_hits = 0
        keyword_counts = {}
        table_counts = {}

        def execute_wrapper(execute, sql, params, many, context):
            nonlocal db_hits
            db_hits += 1
            try:
                keyword = (sql or "").strip().split(None, 1)[0].upper()
            except Exception:
                keyword = "UNKNOWN"
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

            # Best-effort table name extraction (enough to identify hot models).
            # This is intentionally lightweight and may not be perfect for all SQL.
            tbl = None
            if sql:
                s = sql.strip()
                m = None
                if keyword == "SELECT":
                    m = re.search(r'\bFROM\s+["`]?([A-Za-z0-9_]+)["`]?', s, flags=re.I)
                    if not m:
                        m = re.search(r'\bJOIN\s+["`]?([A-Za-z0-9_]+)["`]?', s, flags=re.I)
                elif keyword == "UPDATE":
                    m = re.search(r'\bUPDATE\s+["`]?([A-Za-z0-9_]+)["`]?', s, flags=re.I)
                elif keyword == "DELETE":
                    m = re.search(r'\bFROM\s+["`]?([A-Za-z0-9_]+)["`]?', s, flags=re.I)
                elif keyword == "INSERT":
                    m = re.search(r'\bINTO\s+["`]?([A-Za-z0-9_]+)["`]?', s, flags=re.I)
                if m:
                    # Patterns above capture table name as the first (and only) group.
                    tbl = m.group(1)

            if tbl:
                table_counts[tbl] = table_counts.get(tbl, 0) + 1
            return execute(sql, params, many, context)

        with connection.execute_wrapper(execute_wrapper):
            response = self.get_response(request)

        status_code = getattr(response, "status_code", None)
        current_test = os.getenv("PYTEST_CURRENT_TEST", "").split(" (call)")[0]
        keyword_summary = "|".join(
            f"{k}:{keyword_counts[k]}" for k in sorted(keyword_counts.keys())
        )
        table_summary = "|".join(
            f"{t}:{table_counts[t]}" for t in sorted(table_counts.keys())[:10]
        )
        logger.info(
            "db_hits path={} method={} status_code={} db_hits={} keyword_counts={} table_counts={} test={}",
            request.path,
            request.method,
            status_code,
            db_hits,
            keyword_summary,
            table_summary,
            current_test or "n/a",
        )
        return response

