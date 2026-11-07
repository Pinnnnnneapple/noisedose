"""Noise exposure arithmetic. Durations are hours; levels are dB(A) unless stated.

These calculations do not validate the representativeness or calibration of input.
See docs/methodology.md for threshold, projection and uncertainty assumptions.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Union

from .models import Segment


@dataclass(frozen=True)
class Standard:
    """Dosimeter settings; EU uses a separate, unthresholded energy assessment."""

    key: str
    criterion_level: float
    exchange_rate: float
    threshold: Optional[float]
    criterion_hours: float = 8.0
    energy_twa: bool = False

    def __post_init__(self) -> None:
        values = (self.criterion_level, self.exchange_rate, self.criterion_hours)
        if not all(math.isfinite(x) for x in values):
            raise ValueError("standard settings must be finite")
        if self.exchange_rate <= 0 or self.criterion_hours <= 0:
            raise ValueError("exchange rate and criterion duration must be positive")
        if self.threshold is not None and not math.isfinite(self.threshold):
            raise ValueError("threshold must be finite or None")


STANDARDS: Dict[str, Standard] = {
    "osha-pel": Standard("osha-pel", 90, 5, 90),
    "osha-hc": Standard("osha-hc", 90, 5, 80),
    "niosh-rel": Standard("niosh-rel", 85, 3, 80, energy_twa=True),
    "acgih-tlv": Standard("acgih-tlv", 85, 3, 80, energy_twa=True),
    "eu": Standard("eu", 85, 10 * math.log10(2), None, energy_twa=True),
}
DEFAULT_STANDARDS = ("osha-pel", "osha-hc", "niosh-rel", "eu")


def get_standard(standard: Union[str, Standard]) -> Standard:
    """Resolve a preset name or return a custom standard."""
    if isinstance(standard, Standard):
        return standard
    try:
        return STANDARDS[standard]
    except KeyError:
        raise ValueError("unknown standard: " + str(standard)) from None


def _finite(value: float, name: str) -> None:
    if not math.isfinite(value):
        raise ValueError(name + " must be finite")


def leq(levels: Sequence[float], hours: Sequence[float]) -> float:
    """Return the energy average of equal-length level and duration sequences."""
    if not levels or len(levels) != len(hours):
        raise ValueError("levels and hours must be nonempty and have equal lengths")
    for level, duration in zip(levels, hours):
        _finite(level, "level")
        _finite(duration, "duration")
        if duration <= 0:
            raise ValueError("durations must be positive")
    reference = max(levels)
    return reference + 10 * math.log10(
        math.fsum(t * 10 ** ((l - reference) / 10) for l, t in zip(levels, hours))
        / math.fsum(hours)
    )


def allowed_time(level: float, standard: Union[str, Standard] = "osha-pel") -> float:
    """Return hours to 100% dose; infinity below the integration threshold.

    Infinity means no accumulated dose under these settings, not safe indefinitely.
    EU uses an energy-equivalent reference of 85 dB(A), not a legal dose limit.
    """
    _finite(level, "level")
    s = get_standard(standard)
    if s.threshold is not None and level < s.threshold:
        return math.inf
    if s.key == "eu":
        return s.criterion_hours * 10 ** ((s.criterion_level - level) / 10)
    return s.criterion_hours * 2 ** ((s.criterion_level - level) / s.exchange_rate)


def dose(segments: Iterable[Segment], standard: Union[str, Standard] = "osha-pel") -> float:
    """Return accumulated dose percent using actual exposure durations."""
    s = get_standard(standard)
    return 100 * math.fsum(x.duration_hours / allowed_time(x.level_db, s) for x in segments)


def twa_from_dose(percent: float, standard: Union[str, Standard] = "osha-pel") -> float:
    """Return eight-hour normalized TWA; zero dose has TWA negative infinity.

    NIOSH/ACGIH use 10 log10 convention; exact Q=3 dose doubling differs slightly
    from exact energy doubling. Custom standards use Q/log10(2).
    """
    _finite(percent, "dose")
    if percent < 0:
        raise ValueError("dose must be nonnegative")
    if percent == 0:
        return -math.inf
    s = get_standard(standard)
    coefficient = 10 if s.energy_twa else s.exchange_rate / math.log10(2)
    return s.criterion_level + coefficient * (math.log10(percent) - 2)


def dose_from_twa(twa: float, standard: Union[str, Standard] = "osha-pel") -> float:
    """Invert twa_from_dose, including the zero-dose negative-infinity value."""
    if twa == -math.inf:
        return 0.0
    _finite(twa, "TWA")
    s = get_standard(standard)
    coefficient = 10 if s.energy_twa else s.exchange_rate / math.log10(2)
    return 10 ** (2 + (twa - s.criterion_level) / coefficient)


def time_until_100(level: float, current_dose: float = 0,
                   standard: Union[str, Standard] = "osha-pel") -> float:
    """Return additional hours until 100%, zero if already reached."""
    _finite(current_dose, "current dose")
    if current_dose < 0:
        raise ValueError("current dose must be nonnegative")
    if current_dose >= 100:
        return 0.0
    return allowed_time(level, standard) * (1 - current_dose / 100)


def lex8(segments: Iterable[Segment]) -> float:
    """Return ISO-style daily energy exposure LEX,8h, without a threshold."""
    items = list(segments)
    return leq([x.level_db for x in items], [x.duration_hours for x in items]) + 10 * math.log10(
        math.fsum(x.duration_hours for x in items) / 8
    )


def weekly_lex(daily_lex: Sequence[Optional[float]]) -> float:
    """Normalize daily LEX values to five days; None denotes a zero-energy day.

    Up to seven exposed days may contribute. Five is always the denominator.
    """
    if not daily_lex or len(daily_lex) > 7:
        raise ValueError("provide one to seven daily levels (None for unexposed days)")
    values = [x for x in daily_lex if x is not None and x != -math.inf]
    for value in values:
        _finite(value, "daily LEX")
    if not values:
        return -math.inf
    ref = max(values)
    return ref + 10 * math.log10(math.fsum(10 ** ((x - ref) / 10) for x in values) / 5)


def task_uncertainty(segments: Sequence[Segment], instrument_class: int = 2) -> dict:
    """Return a simplified first-order task-based standard/expanded uncertainty.

    Sampling and duration errors are independent across tasks. Instrument and
    position errors are shared, fully correlated offsets, so do not average down.
    Fewer than two samples leaves the sampling component unknown, not zero.
    """
    if not segments or instrument_class not in (1, 2):
        raise ValueError("tasks required and instrument class must be 1 or 2")
    ref = max(x.level_db for x in segments)
    energies = [x.duration_hours * 10 ** ((x.level_db - ref) / 10) for x in segments]
    total = math.fsum(energies)
    variance = 0.0
    complete = True
    details = []
    for task, energy in zip(segments, energies):
        weight = energy / total
        sampling = statistics.stdev(task.samples) / math.sqrt(len(task.samples)) if len(task.samples) >= 2 else None
        if sampling is None:
            complete = False
        duration = (10 / math.log(10)) * task.duration_uncertainty_hours / task.duration_hours
        variance += weight ** 2 * ((sampling or 0) ** 2 + duration ** 2)
        details.append({"task": task.name, "energy_weight": weight,
                        "sampling_standard_db": sampling, "duration_standard_db": duration})
    instrument = 0.7 if instrument_class == 1 else 1.5
    combined = math.sqrt(variance + instrument ** 2 + 1.0 ** 2)
    return {"method": "simplified first-order task model; not full ISO 9612 conformity",
            "complete_sampling": complete, "combined_standard_db": combined,
            "expanded_db": 1.65 * combined, "coverage_factor": 1.65,
            "coverage": "one-sided approximately 95%, normal approximation",
            "upper_95_db": lex8(segments) + 1.65 * combined,
            "instrument_class": instrument_class, "instrument_standard_db": instrument,
            "position_standard_db": 1.0, "duration_assumption": "exact unless supplied",
            "tasks": details}


def peak_evaluation(peak: Optional[float]) -> dict:
    """Evaluate an unprotected LCpeak against EU 135/137/140 dB(C) levels."""
    if peak is None:
        return {"level_db_c": None, "status": "NOT ASSESSED", "exit_code": 0}
    _finite(peak, "LCpeak")
    status, code = "BELOW ACTION", 0
    if peak > 140:
        status, code = "OVER LIMIT", 2
    elif peak >= 135:
        status, code = "ACTION LEVEL", 1
    return {"level_db_c": peak, "status": status, "exit_code": code,
            "upper_action_reached": peak >= 137, "limit_reached": peak >= 140,
            "basis": "unprotected C-weighted peak; no scalar protector credit"}


def assess(segments: Sequence[Segment], standards: Sequence[str] = DEFAULT_STANDARDS,
           shift_hours: Optional[float] = None) -> List[dict]:
    """Assess actual exposure and separately project a representative pattern.

    Status follows actual duration, never an assumed projection. For OSHA the
    hearing-conservation action test uses the separate 80 dBA threshold dose.
    """
    if not segments or not standards:
        raise ValueError("exposure records and at least one standard are required")
    measured = math.fsum(x.duration_hours for x in segments)
    if shift_hours is None:
        shift_hours = measured
    _finite(shift_hours, "shift hours")
    if shift_hours <= 0:
        raise ValueError("shift hours must be positive")
    hc = dose(segments, "osha-hc")
    pel = dose(segments, "osha-pel")
    daily = lex8(segments)
    peaks = [x.peak_db for x in segments if x.peak_db is not None]
    peak = peak_evaluation(max(peaks) if peaks else None)
    rows = []
    for name in standards:
        s = get_standard(name)
        percent = dose(segments, s)
        twa = twa_from_dose(percent, s)
        code = 0
        if name.startswith("osha"):
            code = 2 if pel > 100 + 1e-9 else (1 if hc >= 50 - 1e-9 else 0)
        elif name == "eu":
            code = max(2 if daily > 87 + 1e-9 else (1 if daily >= 80 - 1e-9 else 0), peak["exit_code"])
        else:
            code = 2 if percent > 100 + 1e-9 else (1 if percent >= 100 - 1e-9 else 0)
        rows.append({"standard": name, "dose_percent": percent,
                     "dose_basis": "energy index relative to 85 dBA; not an EU legal dose" if name == "eu" else "thresholded dosimeter dose",
                     "twa_db": None if twa == -math.inf else twa,
                     "lex8_db": daily, "projected_8h_dose_percent": percent * 8 / measured,
                     "projected_8h_twa_db": None if percent == 0 else twa_from_dose(percent * 8 / measured, s),
                     "projected_shift_dose_percent": percent * shift_hours / measured,
                     "projected_shift_twa_db": None if percent == 0 else twa_from_dose(percent * shift_hours / measured, s),
                     "criterion_db": s.criterion_level, "threshold_db": s.threshold,
                     "exchange_db": s.exchange_rate, "exit_code": code,
                     "status": ("BELOW ACTION", "ACTION LEVEL", "OVER LIMIT")[code],
                     "upper_action_reached": name == "eu" and (daily >= 85 or peak.get("upper_action_reached", False)),
                     "peak": peak if name == "eu" else None,
                     "limit_basis": "unprotected screen; attenuation estimates do not establish EU limit compliance" if name == "eu" else "unprotected",
                     "osha_hc_dose_percent": hc if name.startswith("osha") else None})
    return rows
