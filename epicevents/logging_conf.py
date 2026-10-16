"""Sentry initialisation: unexpected errors are reported."""

import os
import sentry_sdk
from dotenv import load_dotenv


def init_sentry() -> None:
    """Load .env and start Sentry. No-op without a DSN (tests, dev)."""
    load_dotenv()
    dsn = os.getenv("SENTRY_DSN")
    if dsn:
        sentry_sdk.init(dsn=dsn)
