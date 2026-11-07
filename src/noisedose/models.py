"""Validated exposure records. All durations are hours and levels are decibels."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class Segment:
    """One task or logging interval; uncertainty is a standard uncertainty in hours."""

    name: str
    duration_hours: float
    level_db: float
    peak_db: Optional[float] = None
    samples: Tuple[float, ...] = ()
    duration_uncertainty_hours: float = 0.0
    timestamp: Optional[str] = None

    def __post_init__(self) -> None:
        if not math.isfinite(self.duration_hours) or self.duration_hours <= 0:
            raise ValueError("duration_hours must be finite and positive")
        if not math.isfinite(self.level_db) or not -100 <= self.level_db <= 250:
            raise ValueError("level_db must be finite and between -100 and 250 dB")
        if self.peak_db is not None and (not math.isfinite(self.peak_db) or not -100 <= self.peak_db <= 250):
            raise ValueError("peak_db must be finite and between -100 and 250 dB")
        if not math.isfinite(self.duration_uncertainty_hours) or self.duration_uncertainty_hours < 0:
            raise ValueError("duration uncertainty must be finite and nonnegative")
        if any(not math.isfinite(x) or not -100 <= x <= 250 for x in self.samples):
            raise ValueError("measurement samples must be finite levels between -100 and 250 dB")
