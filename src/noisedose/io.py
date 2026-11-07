"""Read exposure logs and task tables with only the Python standard library.

Import assumptions are documented on the loaders; no warnings are emitted and
malformed data is never silently skipped after the CSV header.
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
from datetime import datetime
from statistics import median
from typing import Any, Dict, List, Optional, Tuple, Union

from .models import Segment

__all__ = ["load_log", "load_tasks"]

_Path = Union[str, os.PathLike[str]]
_ALIASES = {
    "task": "name", "name": "name",
    "durationhours": "duration_hours", "hours": "duration_hours",
    "duration": "duration_hours", "leveldb": "level_db", "laeq": "level_db",
    "peakdb": "peak_db", "lcpeak": "peak_db", "peak": "peak_db",
    "samples": "samples", "measurements": "samples",
    "nmeasurements": "n_measurements",
    "durationuncertaintyhours": "duration_uncertainty_hours",
}


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _level_header(value: str) -> bool:
    if _key(value) == "dba":
        return True
    compact = re.sub(r"\s+", "", value.casefold())
    match = re.fullmatch(r"(laeq(?:,?t)?|las|laf|lavg|dba)(.*)", compact)
    return bool(match and _key(match.group(2)) in {"", "db", "dba"})


def _peak_header(value: str) -> bool:
    match = re.fullmatch(r"(lcpeak|peak)(.*)", re.sub(r"\s+", "", value.casefold()))
    return bool(match and _key(match.group(2)) in {"", "db", "dbc"})


def _time_header(value: str) -> bool:
    return _key(value) in {"timestamp", "datetime", "time", "times", "timeseconds"}


def _task_field(value: str) -> Optional[str]:
    field = _ALIASES.get(_key(value))
    if field is None and _level_header(value):
        field = "level_db"
    if field is None and _peak_header(value):
        field = "peak_db"
    return field


def _context(path: _Path, location: str, error: Any) -> ValueError:
    return ValueError("{}: {}: {}".format(os.fspath(path), location, error))


def _text(path: _Path) -> str:
    with open(path, "r", encoding="utf-8-sig", newline="") as stream:
        return stream.read()


def _csv_table(
    path: _Path, content: str, tasks: bool = False,
    level_column: Optional[str] = None,
) -> Tuple[List[str], List[Tuple[int, List[str]]], str, int]:
    lines = content.splitlines(keepends=True)
    selected = None
    for index, line in enumerate(lines):
        candidates = []
        for delimiter in (",", ";", "\t"):
            try:
                header = [cell.strip() for cell in next(csv.reader([line], delimiter=delimiter, strict=True))]
            except (csv.Error, StopIteration):
                continue
            if tasks:
                fields = {_task_field(cell) for cell in header}
                recognized = "duration_hours" in fields or (
                    "name" in fields and bool(fields & {"level_db", "samples"})
                )
            else:
                recognized = any(_level_header(cell) or _time_header(cell) for cell in header)
                recognized = recognized or (level_column is not None and level_column in header)
            if recognized:
                candidates.append((len(header), delimiter, header))
        if candidates:
            _, delimiter, header = max(candidates, key=lambda candidate: candidate[0])
            selected = (index, delimiter, header)
            break
    if selected is None:
        raise _context(path, "line 1", "no recognizable CSV header (an A-weighted level is required for logs)")
    index, delimiter, header = selected
    header_line = index + 1
    normalized = [_key(cell) for cell in header]
    if any(not cell for cell in normalized) or len(set(normalized)) != len(normalized):
        raise _context(path, "line {}".format(header_line), "empty or duplicate CSV column names")
    reader = csv.reader(lines[index + 1:], delimiter=delimiter, strict=True)
    rows = []
    while True:
        start = header_line + reader.line_num + 1
        try:
            row = next(reader)
        except StopIteration:
            break
        except csv.Error as exc:
            raise _context(path, "line {}".format(start), "malformed CSV: {}".format(exc)) from exc
        if not row or len(row) != len(header):
            raise _context(path, "line {}".format(start), "missing row or wrong number of CSV fields")
        rows.append((start, [cell.strip() for cell in row]))
    if not rows:
        raise _context(path, "line {}".format(header_line), "CSV header has no data rows")
    return header, rows, delimiter, header_line


def _number(value: Any, label: str, decimal_comma: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError("{} must be a finite number".format(label))
    if isinstance(value, str):
        value = value.strip()
        if decimal_comma:
            value = value.replace(",", ".")
    try:
        result = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError("{} must be a finite number".format(label)) from exc
    if not math.isfinite(result):
        raise ValueError("{} must be a finite number".format(label))
    return result


def _column(
    header: List[str], matches: List[int], label: str,
    explicit: Optional[str] = None, required: bool = False,
) -> Optional[int]:
    if explicit is not None:
        if explicit not in header:
            raise ValueError("{} column {!r} was not found".format(label, explicit))
        return header.index(explicit)
    if len(matches) > 1:
        raise ValueError("ambiguous {} columns; select an explicit column".format(label))
    if not matches:
        if required:
            raise ValueError("no A-weighted level column was found")
        return None
    return matches[0]


def _timestamp(value: str, decimal_comma: bool) -> Tuple[str, Any]:
    if not value:
        raise ValueError("missing timestamp")
    if re.match(r"^\d{4}-\d{2}-\d{2}[Tt ]", value):
        try:
            return "datetime", datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("invalid ISO datetime timestamp {!r}".format(value)) from exc
    match = re.fullmatch(r"(\d{2}):(\d{2}):(\d{2}(?:[.,]\d+)?)", value)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        second = float(match.group(3).replace(",", "."))
        if hour >= 24 or minute >= 60 or second >= 60:
            raise ValueError("invalid HH:MM:SS timestamp {!r}".format(value))
        return "clock", hour * 3600 + minute * 60 + second
    return "elapsed", _number(value, "timestamp", decimal_comma)


def load_log(
    path: _Path, interval_seconds: Optional[float] = None,
    level_column: Optional[str] = None, peak_column: Optional[str] = None,
) -> List[Segment]:
    """Load a CSV sound-level log into one Segment per data row.

    Detect comma, semicolon or tab delimiters, UTF-8 BOMs, and leading preamble.
    Semicolon/tab tables may use decimal commas. Recognized A-weighted headers
    are LAeq, LAeq,T, LAS, LAF, Lavg and dBA, optionally with dB/dB(A) units;
    LCpeak and Peak are optional. Multiple matching columns require an exact
    header-name override. An explicit level_column asserts the user's chosen
    column is suitable; units/weighting are not converted.

    Timestamp/date time/time accepts ISO datetimes, HH:MM:SS, or numeric elapsed
    seconds. Durations use forward differences; the last uses the median of all
    preceding intervals. A single row or a log without timestamps requires a
    positive interval_seconds, which, when supplied, sets *every* duration.
    Timestamps must still increase strictly, use one representation and have
    compatible timezone awareness; clock-only midnight rollover is rejected.
    Original timestamp text is retained; row names are 'Reading 1', etc.

    LAS/LAF/Lavg values are imported as supplied, without assuming instrument
    averaging settings. These assumptions emit no warnings. Invalid/empty rows,
    missing levels and nonfinite numbers raise ValueError with path and physical
    CSV line context. Only lines before the header may be skipped.
    """
    fixed = None
    if interval_seconds is not None:
        try:
            fixed = _number(interval_seconds, "interval_seconds")
            if fixed <= 0:
                raise ValueError("interval_seconds must be positive")
        except ValueError as exc:
            raise _context(path, "interval_seconds", exc) from exc
    header, rows, delimiter, header_line = _csv_table(path, _text(path), level_column=level_column)
    try:
        level = _column(header, [i for i, cell in enumerate(header) if _level_header(cell)],
                        "A-weighted level", level_column, required=True)
        peak = _column(header, [i for i, cell in enumerate(header) if _peak_header(cell)],
                       "peak", peak_column)
        time = _column(header, [i for i, cell in enumerate(header) if _time_header(cell)], "timestamp")
        if fixed is None and (time is None or len(rows) == 1):
            raise ValueError("interval_seconds is required for a single row or a log without timestamps")
    except ValueError as exc:
        raise _context(path, "line {}".format(header_line), exc) from exc
    records = []
    intervals = []
    previous = None
    decimal_comma = delimiter != ","
    for line, row in rows:
        try:
            level_db = _number(row[level], "A-weighted level", decimal_comma)
            peak_db = None if peak is None or not row[peak] else _number(row[peak], "peak", decimal_comma)
            stamp = None if time is None else row[time]
            if stamp is not None:
                current = _timestamp(stamp, decimal_comma)
                if previous is not None:
                    if current[0] != previous[0]:
                        raise ValueError("timestamp representations must not be mixed")
                    try:
                        delta = current[1] - previous[1]
                    except TypeError as exc:
                        raise ValueError("timestamps have incompatible timezone awareness") from exc
                    seconds = delta.total_seconds() if current[0] == "datetime" else delta
                    if not math.isfinite(seconds) or seconds <= 0:
                        raise ValueError("timestamps must be strictly increasing")
                    intervals.append(seconds)
                previous = current
            # Validate each physical row now; durations are assigned below.
            records.append(Segment("Reading {}".format(len(records) + 1), 1.0,
                                   level_db, peak_db, timestamp=stamp))
        except ValueError as exc:
            raise _context(path, "line {}".format(line), exc) from exc
    durations = [fixed] * len(records) if fixed is not None else intervals + [median(intervals)]
    result = []
    for record, duration, (line, _) in zip(records, durations, rows):
        try:
            result.append(Segment(record.name, duration / 3600.0, record.level_db,
                                  record.peak_db, timestamp=record.timestamp))
        except ValueError as exc:
            raise _context(path, "line {}".format(line), exc) from exc
    return result


def _samples(value: Any, decimal_comma: bool) -> Tuple[float, ...]:
    if value is None or (isinstance(value, str) and not value.strip()):
        return ()
    if isinstance(value, str):
        if value.lstrip().startswith("["):
            try:
                value = json.loads(value)
            except ValueError as exc:
                raise ValueError("samples must be a JSON array or semicolon/pipe list") from exc
        else:
            value = re.split(r"[;|]", value)
    if not isinstance(value, (list, tuple)):
        raise ValueError("samples must be a numeric array or semicolon/pipe list")
    return tuple(_number(sample, "sample", decimal_comma) for sample in value)


def _missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _task(record: Dict[str, Any], decimal_comma: bool) -> Segment:
    fields = {}
    for key, value in record.items():
        canonical = _task_field(key)
        if canonical is not None:
            if canonical in fields:
                raise ValueError("ambiguous task aliases for {}".format(canonical))
            fields[canonical] = value
    name = fields.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("task/name is required and must be nonempty text")
    duration = _number(fields.get("duration_hours"), "duration_hours", decimal_comma)
    samples = _samples(fields.get("samples"), decimal_comma)
    count = fields.get("n_measurements")
    if not _missing(count):
        number = _number(count, "n_measurements", decimal_comma)
        if number <= 0 or not number.is_integer():
            raise ValueError("n_measurements must be a positive integer")
        if samples and number != len(samples):
            raise ValueError("n_measurements does not match the sample count")
    value = fields.get("level_db")
    if _missing(value):
        if not samples:
            raise ValueError("an A-weighted level or measurement samples are required")
        maximum = max(samples)
        level = maximum + 10 * math.log10(sum(10 ** ((x - maximum) / 10) for x in samples) / len(samples))
    else:
        level = _number(value, "level_db", decimal_comma)
    peak = fields.get("peak_db")
    peak = None if _missing(peak) else _number(peak, "peak_db", decimal_comma)
    uncertainty = fields.get("duration_uncertainty_hours")
    uncertainty = 0.0 if _missing(uncertainty) else _number(uncertainty, "duration_uncertainty_hours", decimal_comma)
    return Segment(name.strip(), duration, level, peak, samples, uncertainty)


def load_tasks(path: _Path) -> List[Segment]:
    """Load task CSV or JSON (a list, or an object containing a 'tasks' list).

    Required name aliases: task/name. Duration aliases: duration_hours/hours/
    duration, always interpreted as hours. LAeq/level_db and LCpeak/peak_db are
    level and optional peak aliases. samples/measurements accepts numeric arrays,
    JSON-array strings, or semicolon/pipe-separated strings. Missing levels are
    derived by an energy mean of samples; supplied summaries are retained.

    Optional n_measurements must be a positive integer, matching the raw sample
    count when samples exist. A summary plus count alone retains empty samples;
    it never synthesizes repeated measurements or estimates sampling uncertainty.
    duration_uncertainty_hours defaults to zero and must be nonnegative.
    Empty optional cells are treated as absent. Duplicate aliases are errors.

    CSV supports the same delimiters, decimal commas, BOM and preamble handling
    as load_log. JSON is selected by .json suffix or leading '['/'{'. Empty task
    lists, malformed records, missing required fields and nonfinite values raise
    ValueError with path and CSV line or JSON task-item context. No warnings are
    emitted, and no rows after a CSV header are skipped.
    """
    content = _text(path)
    is_json = os.fspath(path).lower().endswith(".json") or content.lstrip().startswith(("[", "{"))
    if is_json:
        try:
            data = json.loads(content)
        except ValueError as exc:
            raise _context(path, "JSON", exc) from exc
        if isinstance(data, dict):
            data = data.get("tasks")
        if not isinstance(data, list) or not data:
            raise _context(path, "JSON", "expected a nonempty tasks list")
        result = []
        for index, record in enumerate(data, 1):
            try:
                if not isinstance(record, dict):
                    raise ValueError("task must be an object")
                result.append(_task(record, False))
            except ValueError as exc:
                raise _context(path, "task item {}".format(index), exc) from exc
        return result
    header, rows, delimiter, header_line = _csv_table(path, content, tasks=True)
    fields = [_task_field(cell) for cell in header]
    known = [field for field in fields if field is not None]
    if len(known) != len(set(known)):
        raise _context(path, "line {}".format(header_line), "ambiguous task column aliases")
    result = []
    for line, row in rows:
        try:
            result.append(_task(dict(zip(header, row)), delimiter != ","))
        except ValueError as exc:
            raise _context(path, "line {}".format(line), exc) from exc
    return result
