import hashlib
from datetime import UTC, datetime
from unittest.mock import patch

from alphatrion.utils.time import humanize_time, now_2_hash


def test_now_2_hash():
    fixed_timestamp = 1700000000
    fixed_datetime = datetime.fromtimestamp(fixed_timestamp, tz=UTC)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_datetime

    with patch("alphatrion.utils.time.datetime", FixedDateTime):
        expected_hash = hashlib.sha1(str(fixed_timestamp).encode()).hexdigest()[:7]
        assert now_2_hash() == expected_hash


def test_humanize_time():
    fixed_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    with patch("alphatrion.utils.time.datetime", FixedDateTime):
        assert humanize_time("2024-01-01T11:59:30Z") == "30s"
        assert humanize_time("2024-01-01T11:50:00Z") == "10m"
        assert humanize_time("2024-01-01T10:00:00Z") == "2h"
        assert humanize_time("2023-12-31T12:00:00Z") == "1d"
