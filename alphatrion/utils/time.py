import hashlib
from datetime import UTC, datetime


# ruff: noqa: PLR2004
def humanize_time(timestamp: str) -> str:
    creation_time = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=UTC
    )
    t = datetime.now(UTC) - creation_time

    if t.days > 0:
        age = f"{t.days}d"
    elif t.seconds >= 3600:
        age = f"{t.seconds // 3600}h"
    elif t.seconds >= 60:
        age = f"{t.seconds // 60}m"
    else:
        age = f"{t.seconds}s"

    return age


def now_2_hash() -> str:
    timestamp = str(int(datetime.now(UTC).timestamp()))
    unique_hash = hashlib.sha1(timestamp.encode()).hexdigest()[:7]

    print("Generated hash from timestamp:", timestamp, "->", unique_hash)
    return unique_hash
