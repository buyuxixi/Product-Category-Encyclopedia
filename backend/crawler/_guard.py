"""Global kill switch for crawler scripts.

Respects CRAWLER_ENABLED (default false). Call require_crawler_enabled()
at the start of any crawler CLI entrypoint.
"""
from __future__ import annotations

import os
import sys


def is_crawler_enabled() -> bool:
    return os.getenv("CRAWLER_ENABLED", "false").lower() in {"1", "true", "yes"}


def require_crawler_enabled() -> None:
    if not is_crawler_enabled():
        print("Crawler disabled (CRAWLER_ENABLED=false). Exiting.")
        sys.exit(0)
