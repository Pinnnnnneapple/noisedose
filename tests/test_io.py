"""Behavioral contracts for exposure log and task importers."""
import csv
import io
import json
import math
import re

import pytest

from noisedose.io import load_log, load_tasks
from noisedose.models import Segment


def write_text(tmp_path, text, filename="input.csv"):
    path = tmp_path / filename
    path.write_text(text, encoding="utf-8")
    return path


def write_csv(tmp_path, rows, delimiter=",", bom=False):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=delimiter)
    writer.writerows(rows)
    return write_text(tmp_path, ("\ufeff" if bom else "") + stream.getvalue())


def csv_error(loader, path, line, **kwargs):
    with pytest.raises(ValueError) as caught:
        loader(path, **kwargs)
    message = str(caught.value)
    assert str(path) in message
    # Permit either "line 3" or conventional path:3 diagnostics.
    context = message.replace(str(path), "")
    assert re.search(rf"(?<!\d){line}(?!\d)", context), message


def write_tasks(tmp_path, tasks, wrapped=False):
    return write_text(tmp_path, json.dumps({"tasks": tasks} if wrapped else tasks), "tasks.json")


def json_error(path):
    with pytest.raises(ValueError) as caught:
        load_tasks(path)
    message = str(caught.value)
    assert str(path) in message
    assert re.search(r"item|task|index|\[\d+\]", message, re.I), message


@pytest.mark.parametrize("delimiter", [",", ";", "\t"])
@pytest.mark.parametrize("bom", [False, True])
def test_log_delimiters_and_bom(tmp_path, delimiter, bom):
    path = write_csv(tmp_path, [["timestamp", "LAeq", "LCpeak"],
                               ["0", "80.5", "103"], ["2", "82", "105"]], delimiter, bom)
    result = load_log(path)
    assert isinstance(result, list)
    assert all(isinstance(segment, Segment) for segment in result)
    assert [s.level_db for s in result] == [80.5, 82]
    assert [s.peak_db for s in result] == [103, 105]
    assert [s.duration_hours for s in result] == pytest.approx([2 / 3600] * 2)


@pytest.mark.parametrize("header", ["LAeq", "LAeq,T", "LAS", "LAF", "Lavg", "dBA",
                                    "LAeq (dB)", "LAeq [dB(A)]", "LAS (dBA)", "LAF [dB]",
                                    "Lavg (dB(A))", "dBA (dB)"])
def test_log_detects_a_weighted_headers_with_units(tmp_path, header):
    path = write_csv(tmp_path, [["time", header], ["0", "80"], ["1", "81"]])
    assert [s.level_db for s in load_log(path)] == [80, 81]


@pytest.mark.parametrize("header", ["LCpeak", "Peak", "LCpeak (dB)", "Peak [dB]"])
def test_log_detects_peak_headers(tmp_path, header):
    path = write_csv(tmp_path, [["time", "LAeq", header], ["0", "80", "120"]])
    assert load_log(path, interval_seconds=1)[0].peak_db == 120


def test_log_peak_is_optional(tmp_path):
    path = write_csv(tmp_path, [["time", "LAeq"], ["0", "80"], ["1", "81"]])
    assert all(s.peak_db is None for s in load_log(path))


@pytest.mark.parametrize("delimiter", [";", "\t"])
def test_log_decimal_commas(tmp_path, delimiter):
    path = write_csv(tmp_path, [["time", "LAeq", "Peak"],
                               ["0,0", "80,5", "100,25"], ["1,5", "81,5", "101,25"]], delimiter)
    segments = load_log(path)
    assert [s.level_db for s in segments] == [80.5, 81.5]
    assert segments[0].peak_db == 100.25
    assert [s.duration_hours for s in segments] == pytest.approx([1.5 / 3600] * 2)


def test_log_comma_delimiter_rejects_quoted_decimal_comma(tmp_path):
    path = write_csv(tmp_path, [["time", "LAeq"], ["0", "80,5"]])
    csv_error(load_log, path, 2, interval_seconds=1)


def test_log_skips_arbitrary_preamble_before_header(tmp_path):
    path = write_text(tmp_path, "\ufeffInstrument report\nsite;warehouse\n\nTime,LAeq\n0,80\n2,81\n")
    segments = load_log(path)
    assert [s.level_db for s in segments] == [80, 81]
    assert [s.duration_hours for s in segments] == pytest.approx([2 / 3600] * 2)


@pytest.mark.parametrize("row", ["not a data row", "Time,LAeq", "garbage,garbage", "", ",", "1", "1,81,99"])
def test_log_never_skips_malformed_rows_after_header(tmp_path, row):
    path = write_text(tmp_path, f"report\nTime,LAeq\n0,80\n{row}\n2,82\n")
    csv_error(load_log, path, 4)


@pytest.mark.parametrize("columns", [["LAeq", "LAS"], ["LAS", "LAF"], ["LAeq", "dBA"]])
def test_log_ambiguous_automatic_level_rejected(tmp_path, columns):
    path = write_csv(tmp_path, [["time", *columns], ["0", "80", "90"]])
    csv_error(load_log, path, 1, interval_seconds=1)


def test_log_exact_override_resolves_ambiguity(tmp_path):
    path = write_csv(tmp_path, [["time", "LAeq", "LAS"], ["0", "80", "90"]])
    assert load_log(path, interval_seconds=1, level_column="LAS")[0].level_db == 90


def test_log_unknown_level_requires_explicit_override(tmp_path):
    path = write_csv(tmp_path, [["time", "Custom reading"], ["0", "88"]])
    with pytest.raises(ValueError):
        load_log(path, interval_seconds=1)
    assert load_log(path, interval_seconds=1, level_column="Custom reading")[0].level_db == 88


def test_log_explicit_peak_override(tmp_path):
    path = write_csv(tmp_path, [["time", "LAeq", "Custom maximum"], ["0", "88", "122"]])
    assert load_log(path, interval_seconds=1, peak_column="Custom maximum")[0].peak_db == 122


@pytest.mark.parametrize("option", ["level_column", "peak_column"])
def test_log_override_must_match_exact_header(tmp_path, option):
    path = write_csv(tmp_path, [["time", "LAeq", "Peak"], ["0", "80", "100"]])
    with pytest.raises(ValueError):
        load_log(path, interval_seconds=1, **{option: "laeq" if option == "level_column" else "peak"})


@pytest.mark.parametrize("headers", [["time", "LAeq", "LAeq"], ["time", "LAeq", "Peak", "Peak"],
                                     ["time", "time", "LAeq"]])
def test_log_duplicate_headers_rejected(tmp_path, headers):
    path = write_csv(tmp_path, [headers, ["0"] * len(headers)])
    csv_error(load_log, path, 1, interval_seconds=1)


@pytest.mark.parametrize("time_header", ["timestamp", "date time", "time"])
@pytest.mark.parametrize("times", [["2026-01-01T00:00:00", "2026-01-01T00:00:02", "2026-01-01T00:00:08"],
                                  ["2026-01-01T00:00:00Z", "2026-01-01T00:00:02Z", "2026-01-01T00:00:08Z"],
                                  ["12:00:00", "12:00:02", "12:00:08"], ["0", "2", "8"]])
def test_log_timestamp_types_forward_intervals_and_final_median(tmp_path, time_header, times):
    path = write_csv(tmp_path, [[time_header, "LAeq"], *[[t, "80"] for t in times]])
    result = load_log(path)
    assert [s.duration_hours for s in result] == pytest.approx([2 / 3600, 6 / 3600, 4 / 3600])
    assert [s.timestamp for s in result] == times


def test_log_final_interval_uses_median_not_mean(tmp_path):
    path = write_csv(tmp_path, [["time", "LAeq"], ["0", "80"], ["1", "81"], ["4", "82"], ["104", "83"]])
    assert [s.duration_hours for s in load_log(path)] == pytest.approx([1 / 3600, 3 / 3600, 100 / 3600, 3 / 3600])


def test_log_preserves_stripped_timestamp_text(tmp_path):
    path = write_csv(tmp_path, [["timestamp", "LAeq"], ["  000.00  ", "80"], ["  002.50 ", "81"]])
    assert [s.timestamp for s in load_log(path)] == ["000.00", "002.50"]


def test_log_explicit_interval_fixes_every_duration(tmp_path):
    path = write_csv(tmp_path, [["time", "LAeq"], ["0", "80"], ["2", "81"], ["19", "82"]])
    assert [s.duration_hours for s in load_log(path, interval_seconds=5)] == pytest.approx([5 / 3600] * 3)


def test_log_no_timestamps_requires_explicit_interval(tmp_path):
    path = write_csv(tmp_path, [["LAeq"], ["80"], ["81"]])
    with pytest.raises(ValueError):
        load_log(path)
    segments = load_log(path, interval_seconds=2)
    assert [s.duration_hours for s in segments] == pytest.approx([2 / 3600] * 2)
    assert [s.timestamp for s in segments] == [None, None]


def test_log_single_row_requires_explicit_interval(tmp_path):
    path = write_csv(tmp_path, [["time", "LAeq"], ["0", "80"]])
    with pytest.raises(ValueError):
        load_log(path)
    assert load_log(path, interval_seconds=0.5)[0].duration_hours == pytest.approx(0.5 / 3600)


@pytest.mark.parametrize("interval", [0, -1, math.nan, math.inf, -math.inf])
def test_log_invalid_explicit_interval(tmp_path, interval):
    path = write_csv(tmp_path, [["time", "LAeq"], ["0", "80"], ["1", "81"]])
    with pytest.raises(ValueError):
        load_log(path, interval_seconds=interval)


@pytest.mark.parametrize("times", [["1", "1"], ["2", "1"], ["23:59:59", "00:00:01"],
                                  ["0", "12:00:00"], ["12:00:00", "2026-01-01T12:00:01"],
                                  ["0", "nan"], ["0", "inf"], ["0", "nonsense"], ["0", ""]])
@pytest.mark.parametrize("interval", [None, 3])
def test_log_invalid_timestamps_even_with_fixed_interval(tmp_path, times, interval):
    path = write_csv(tmp_path, [["time", "LAeq"], [times[0], "80"], [times[1], "81"]])
    csv_error(load_log, path, 3, interval_seconds=interval)


@pytest.mark.parametrize("column", ["LAeq", "Peak"])
@pytest.mark.parametrize("value", ["nan", "NaN", "inf", "-inf", "251", "-100.01", "bad"])
def test_log_invalid_levels_report_physical_line(tmp_path, column, value):
    row = ["1", "81", "110"]
    row[1 if column == "LAeq" else 2] = value
    path = write_text(tmp_path, "Instrument report\n\nTime,LAeq,Peak\n0,80,100\n" + ",".join(row) + "\n")
    csv_error(load_log, path, 5)


@pytest.mark.parametrize("value", ["", "   "])
def test_log_blank_level_rejected(tmp_path, value):
    path = write_csv(tmp_path, [["time", "LAeq"], ["0", value]])
    csv_error(load_log, path, 2, interval_seconds=1)


@pytest.mark.parametrize("value", [-100, 250])
def test_log_level_and_peak_range_boundaries(tmp_path, value):
    path = write_csv(tmp_path, [["time", "LAeq", "Peak"], ["0", value, value]])
    segment = load_log(path, interval_seconds=1)[0]
    assert segment.level_db == segment.peak_db == value


@pytest.mark.parametrize("wrapped", [False, True])
def test_tasks_json_top_level_shapes(tmp_path, wrapped):
    path = write_tasks(tmp_path, [{"task": "Drilling", "duration_hours": 2, "LAeq": 85, "LCpeak": 120}], wrapped)
    result = load_tasks(path)
    assert isinstance(result, list)
    assert isinstance(result[0], Segment)
    assert result[0].name == "Drilling"
    assert result[0].duration_hours == 2
    assert result[0].level_db == 85
    assert result[0].peak_db == 120
    assert result[0].samples == ()
    assert result[0].duration_uncertainty_hours == 0


@pytest.mark.parametrize("name_key", ["task", "name"])
@pytest.mark.parametrize("duration_key", ["duration_hours", "hours", "duration"])
@pytest.mark.parametrize("level_key,peak_key", [("LAeq", "LCpeak"), ("level_db", "peak_db")])
@pytest.mark.parametrize("fmt", ["csv", "json"])
def test_tasks_aliases(tmp_path, name_key, duration_key, level_key, peak_key, fmt):
    task = {name_key: "Assembly", duration_key: 1.25, level_key: 82, peak_key: 115}
    path = write_tasks(tmp_path, [task]) if fmt == "json" else write_csv(tmp_path, [list(task), list(task.values())])
    segment = load_tasks(path)[0]
    assert (segment.name, segment.duration_hours, segment.level_db, segment.peak_db) == ("Assembly", 1.25, 82, 115)


@pytest.mark.parametrize("delimiter", [",", ";", "\t"])
@pytest.mark.parametrize("bom", [False, True])
def test_tasks_csv_dialects(tmp_path, delimiter, bom):
    path = write_csv(tmp_path, [["name", "hours", "level_db"], ["Work", "2", "85"]], delimiter, bom)
    assert load_tasks(path)[0].level_db == 85


@pytest.mark.parametrize("sample_key", ["samples", "measurements"])
@pytest.mark.parametrize("samples", [[80, 90], "[80, 90]", "80;90", "80|90"])
def test_tasks_json_sample_encodings_and_energy_mean(tmp_path, sample_key, samples):
    path = write_tasks(tmp_path, [{"name": "Work", "hours": 1, sample_key: samples, "n_measurements": 2}])
    segment = load_tasks(path)[0]
    assert segment.samples == (80, 90)
    assert segment.level_db == pytest.approx(10 * math.log10((10**8 + 10**9) / 2))


@pytest.mark.parametrize("sample_key", ["samples", "measurements"])
@pytest.mark.parametrize("samples", ["[80, 90]", "80;90", "80|90"])
def test_tasks_csv_sample_encodings(tmp_path, sample_key, samples):
    path = write_csv(tmp_path, [["name", "hours", sample_key, "n_measurements"], ["Work", "1", samples, "2"]])
    segment = load_tasks(path)[0]
    assert segment.samples == (80, 90)
    assert segment.level_db == pytest.approx(87.4036268949)


@pytest.mark.parametrize("fmt", ["csv", "json"])
def test_tasks_summary_level_with_count_does_not_synthesize_samples(tmp_path, fmt):
    task = {"name": "Work", "hours": 1, "level_db": 85, "n_measurements": 7}
    path = write_tasks(tmp_path, [task]) if fmt == "json" else write_csv(tmp_path, [list(task), list(task.values())])
    segment = load_tasks(path)[0]
    assert segment.level_db == 85
    assert segment.samples == ()


@pytest.mark.parametrize("fmt", ["csv", "json"])
def test_tasks_preserves_supplied_summary_level_and_samples(tmp_path, fmt):
    task = {"name": "Work", "hours": 1, "level_db": 83, "samples": "80|90", "n_measurements": 2}
    path = write_tasks(tmp_path, [task]) if fmt == "json" else write_csv(tmp_path, [list(task), list(task.values())])
    segment = load_tasks(path)[0]
    assert segment.level_db == 83
    assert segment.samples == (80, 90)


@pytest.mark.parametrize("fmt", ["csv", "json"])
def test_tasks_blank_optional_fields(tmp_path, fmt):
    task = {"name": "Work", "hours": 1, "level_db": 85, "peak_db": "", "samples": "",
            "n_measurements": "", "duration_uncertainty_hours": ""}
    path = write_tasks(tmp_path, [task]) if fmt == "json" else write_csv(tmp_path, [list(task), list(task.values())])
    segment = load_tasks(path)[0]
    assert segment.peak_db is None
    assert segment.samples == ()
    assert segment.duration_uncertainty_hours == 0


@pytest.mark.parametrize("fmt", ["csv", "json"])
def test_tasks_positive_duration_uncertainty(tmp_path, fmt):
    task = {"name": "Work", "hours": 2, "level_db": 85, "duration_uncertainty_hours": 0.125}
    path = write_tasks(tmp_path, [task]) if fmt == "json" else write_csv(tmp_path, [list(task), list(task.values())])
    assert load_tasks(path)[0].duration_uncertainty_hours == 0.125


INVALID_TASK_UPDATES = [
    {"name": ""}, {"name": "   "}, {"hours": ""}, {"hours": 0}, {"hours": -1},
    {"hours": "nan"}, {"hours": "inf"}, {"hours": "bad"},
    {"level_db": "nan"}, {"level_db": "inf"}, {"level_db": "-inf"},
    {"level_db": 251}, {"level_db": -101}, {"level_db": "bad"},
    {"peak_db": "nan"}, {"peak_db": "inf"}, {"peak_db": 251}, {"peak_db": -101},
    {"duration_uncertainty_hours": -0.01}, {"duration_uncertainty_hours": "nan"},
    {"duration_uncertainty_hours": "inf"}, {"duration_uncertainty_hours": "bad"},
    {"n_measurements": 0}, {"n_measurements": -1}, {"n_measurements": 1.5},
    {"n_measurements": "nan"}, {"n_measurements": "inf"}, {"n_measurements": "bad"},
    {"samples": "80|90", "n_measurements": 3},
    {"samples": "80|nan"}, {"samples": "80|inf"}, {"samples": "80|-101"},
    {"samples": "80|251"}, {"samples": "80|bad"}, {"samples": "[80, invalid]"},
    {"level_db": "", "samples": ""},
]


@pytest.mark.parametrize("updates", INVALID_TASK_UPDATES)
@pytest.mark.parametrize("fmt", ["csv", "json"])
def test_tasks_invalid_values_have_source_context(tmp_path, updates, fmt):
    valid = {"name": "Good", "hours": 1, "level_db": 80}
    invalid = {**valid, **updates}
    if fmt == "json":
        path = write_tasks(tmp_path, [valid, invalid])
        json_error(path)
    else:
        headers = list(invalid)
        path = write_csv(tmp_path, [headers, [valid.get(k, "") for k in headers], list(invalid.values())])
        csv_error(load_tasks, path, 3)


@pytest.mark.parametrize("task", [{"name": "Work", "level_db": 80},
                                  {"name": "Work", "hours": 1},
                                  {"name": "Work", "hours": 1, "n_measurements": 2}])
def test_tasks_missing_required_information_json(tmp_path, task):
    json_error(write_tasks(tmp_path, [task]))


@pytest.mark.parametrize("row", ["", "Work,1", "Work,1,80,90", "Work,,80", "Work,1,", ",1,80"])
def test_tasks_csv_bad_rows_have_physical_context(tmp_path, row):
    path = write_text(tmp_path, f"name,hours,level_db\nGood,1,80\n{row}\nNext,1,85\n")
    csv_error(load_tasks, path, 3)


def test_tasks_duplicate_csv_headers(tmp_path):
    path = write_text(tmp_path, "name,hours,level_db,level_db\nWork,1,80,90\n")
    csv_error(load_tasks, path, 1)


@pytest.mark.parametrize("payload", [{}, {"tasks": {}}, {"tasks": "bad"}, "bad", 7, None])
def test_tasks_invalid_json_top_level(tmp_path, payload):
    path = write_text(tmp_path, json.dumps(payload), "tasks.json")
    with pytest.raises(ValueError) as caught:
        load_tasks(path)
    assert str(path) in str(caught.value)


@pytest.mark.parametrize("item", [None, 1, "bad", []])
def test_tasks_json_nonobject_item_has_context(tmp_path, item):
    json_error(write_tasks(tmp_path, [{"name": "Good", "hours": 1, "level_db": 80}, item]))


@pytest.mark.parametrize("samples", [[80, math.nan], [80, math.inf], [80, 251], [80, -101], [80, "bad"]])
def test_tasks_json_invalid_raw_numeric_list(tmp_path, samples):
    json_error(write_tasks(tmp_path, [{"name": "Work", "hours": 1, "samples": samples}]))


@pytest.mark.parametrize("value", [-100, 250])
def test_tasks_inclusive_level_peak_sample_bounds(tmp_path, value):
    path = write_tasks(tmp_path, [{"name": "Work", "hours": 1, "level_db": value,
                                  "peak_db": value, "samples": [value], "n_measurements": 1}])
    segment = load_tasks(path)[0]
    assert segment.level_db == segment.peak_db == value
    assert segment.samples == (value,)


def test_log_timezone_offsets_use_elapsed_time(tmp_path):
    path = write_csv(tmp_path, [["timestamp", "LAeq"],
                               ["2026-01-01T12:00:00+02:00", 80],
                               ["2026-01-01T10:00:03+00:00", 81]])
    assert [s.duration_hours for s in load_log(path)] == pytest.approx([3 / 3600] * 2)


@pytest.mark.parametrize("times", [
    ["2026-01-01T00:00:00Z", "2026-01-01T00:00:01"],
    ["2026-01-01T00:00:00Z", "2026-01-01T01:00:00+01:00"],
    ["12:00:00", "24:00:00"], ["12:00:00", "12:60:00"],
    ["12:00:00", "12:00:60"], ["12:00:00", "2026-02-30T00:00:00"],
])
def test_log_invalid_datetime_and_clock_values_have_context(tmp_path, times):
    path = write_csv(tmp_path, [["timestamp", "LAeq"], [times[0], 80], [times[1], 81]])
    csv_error(load_log, path, 3)


def test_log_fractional_clock_intervals(tmp_path):
    path = write_csv(tmp_path, [["time", "LAeq"], ["12:00:00.125", 80], ["12:00:00.625", 81]])
    assert [s.duration_hours for s in load_log(path)] == pytest.approx([0.5 / 3600] * 2)


def test_log_parenthesized_a_weighting_header(tmp_path):
    path = write_csv(tmp_path, [["dB(A)"], [80]])
    assert load_log(path, interval_seconds=1)[0].level_db == 80


def test_log_ambiguous_peaks_require_override(tmp_path):
    path = write_csv(tmp_path, [["LAeq", "LCpeak", "Peak"], [80, 110, 120]])
    csv_error(load_log, path, 1, interval_seconds=1)
    assert load_log(path, interval_seconds=1, peak_column="Peak")[0].peak_db == 120


def test_log_lcpeak_weighting_units(tmp_path):
    path = write_csv(tmp_path, [["LAeq [dB(A)]", "LCpeak [dB(C)]"], [80, 120]])
    assert load_log(path, interval_seconds=1)[0].peak_db == 120


@pytest.mark.parametrize("loader,header", [(load_log, "time,LAeq"), (load_tasks, "name,hours,LAeq")])
def test_unclosed_csv_quote_is_not_skipped(tmp_path, loader, header):
    path = write_text(tmp_path, header + '\n"unfinished\n')
    csv_error(loader, path, 2, **({"interval_seconds": 1} if loader is load_log else {}))


@pytest.mark.parametrize("loader,header", [(load_log, "time,LAeq"), (load_tasks, "name,hours,LAeq")])
def test_multiline_csv_record_errors_point_to_start(tmp_path, loader, header):
    row = '0,"bad\nlevel"' if loader is load_log else '"Work\nstation",bad,80'
    path = write_text(tmp_path, "report\n" + header + "\n" + row + "\n")
    csv_error(loader, path, 3, **({"interval_seconds": 1} if loader is load_log else {}))


@pytest.mark.parametrize("delimiter", [";", "\t"])
def test_tasks_csv_preamble_and_decimal_comma_samples(tmp_path, delimiter):
    rows = [["task", "duration", "measurements", "n_measurements", "duration_uncertainty_hours"],
            ["Work", "1,5", "80,5|90,5", "2", "0,25"]]
    path = write_csv(tmp_path, rows, delimiter, bom=True)
    path.write_text("\ufeffInstrument report\nlocation: factory\n" + path.read_text(encoding="utf-8-sig"),
                    encoding="utf-8")
    segment = load_tasks(path)[0]
    assert segment.duration_hours == 1.5
    assert segment.duration_uncertainty_hours == 0.25
    assert segment.samples == (80.5, 90.5)
    assert segment.level_db == pytest.approx(87.9036268949)


@pytest.mark.parametrize("body", ["[]", '{"tasks": []}', '{"tasks": [', 'not json'])
def test_tasks_empty_and_malformed_json_rejected(tmp_path, body):
    path = write_text(tmp_path, body, "tasks.json")
    with pytest.raises(ValueError, match=re.escape(str(path))):
        load_tasks(path)


def test_tasks_json_content_detection_without_json_suffix(tmp_path):
    path = write_text(tmp_path, '\ufeff  [{"task":"Work","hours":1,"LAeq":85}]', "tasks.data")
    assert load_tasks(str(path))[0].level_db == 85


@pytest.mark.parametrize("updates", [
    {"name": 7}, {"hours": True}, {"level_db": False},
    {"samples": [True]}, {"samples": 80}, {"samples": {"level": 80}},
    {"samples": "80||90"}, {"samples": "80;"},
    {"samples": [250, -100], "n_measurements": True},
    {"samples": [251, 80]}, {"samples": [-101, 80]},
    {"duration_hours": 1}, {"LAeq": 80}, {"task": "Duplicate"},
])
def test_tasks_invalid_types_and_duplicate_aliases(tmp_path, updates):
    task = {"name": "Work", "hours": 1, "level_db": 80, **updates}
    json_error(write_tasks(tmp_path, [task]))


def test_tasks_energy_mean_is_stable_at_model_range_limits(tmp_path):
    path = write_tasks(tmp_path, [{"name": "Work", "hours": 1, "samples": [-100, 250]}])
    segment = load_tasks(path)[0]
    assert segment.level_db == pytest.approx(250 - 10 * math.log10(2))
    assert segment.samples == (-100, 250)


@pytest.mark.parametrize("loader,body", [(load_log, ""), (load_log, "time,LAeq\n"),
                                       (load_tasks, ""), (load_tasks, "name,hours,LAeq\n")])
def test_empty_csv_and_headers_without_records_rejected(tmp_path, loader, body):
    path = write_text(tmp_path, body)
    with pytest.raises(ValueError, match=re.escape(str(path))):
        loader(path)
