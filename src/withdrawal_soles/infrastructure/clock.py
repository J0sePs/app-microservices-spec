"""System clock and identifier generation."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo


class SystemClock:
    """Production clock with the bank's business time zone."""

    def __init__(self, timezone_name: str = "America/Lima") -> None:
        self._timezone = ZoneInfo(timezone_name)

    def now(self) -> datetime:
        return datetime.now(UTC)

    def day_bounds(self) -> tuple[datetime, datetime]:
        local_now = datetime.now(self._timezone)
        local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        local_end = local_start + timedelta(days=1)
        return local_start.astimezone(UTC), local_end.astimezone(UTC)


class Uuid4Generator:
    """Production identifier source."""

    def new_id(self) -> UUID:
        return uuid4()
