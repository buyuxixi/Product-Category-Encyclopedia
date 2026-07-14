from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal

from scripts.database_bundle import _decode_value, _encode_value


def test_database_values_round_trip() -> None:
    value = {
        "created": datetime(2026, 7, 13, 12, 30, tzinfo=UTC),
        "date": date(2026, 7, 13),
        "time": time(12, 30),
        "amount": Decimal("12.3400"),
        "blob": b"snapshot",
        "json": ["中文", {"enabled": True}],
    }

    assert _decode_value(_encode_value(value)) == value
