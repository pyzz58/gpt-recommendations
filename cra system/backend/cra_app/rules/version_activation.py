"""Manual activation intervals with inclusive starts and exclusive ends."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ActivationInterval:
    starts_on: date
    ends_before: date | None

    def contains(self, event_date: date) -> bool:
        return self.starts_on <= event_date and (
            self.ends_before is None or event_date < self.ends_before
        )

    def overlaps(self, other: "ActivationInterval") -> bool:
        self_end = self.ends_before
        other_end = other.ends_before
        return (self_end is None or other.starts_on < self_end) and (
            other_end is None or self.starts_on < other_end
        )


def boundary_expectations(
    interval: ActivationInterval,
) -> dict[str, bool]:
    points = {
        "before_start": date.fromordinal(interval.starts_on.toordinal() - 1),
        "on_start": interval.starts_on,
    }
    if interval.ends_before is not None:
        points["before_end"] = date.fromordinal(
            interval.ends_before.toordinal() - 1
        )
        points["on_end"] = interval.ends_before
    return {key: interval.contains(value) for key, value in points.items()}
