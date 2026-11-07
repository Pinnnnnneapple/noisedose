"""End-to-end commands and report contracts, including untrusted text."""
import json
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

from noisedose.cli import _parser, main
from noisedose.io import load_tasks
from noisedose.models import Segment
from noisedose.report import build_report, console_table, to_html, to_json, to_markdown

ROOT = Path(__file__).resolve().parents[1]


def test_parser_help_formats_all_commands():
    parser = _parser()
    rendered = [parser.format_help()]
    subparsers = parser._subparsers._group_actions[0].choices
    rendered.extend(subparser.format_help() for subparser in subparsers.values())
    assert "100%" in rendered[0]
    assert "50%" in rendered[list(subparsers).index("protect") + 1]


@pytest.mark.parametrize("command,file,expected", [
    ("log", "sawmill_dosimeter.csv", 2),
    ("tasks", "workshop_tasks.csv", 2), ("log", "office_quiet.csv", 0),
])
def test_examples_and_outputs(command, file, expected, tmp_path, capsys):
    args = [command, str(ROOT / "examples" / file), "--worker", "Op\u00e9rateur \u6e2c\u5b9a"]
    for fmt in ("html", "json", "md"):
        args.extend(["--" + fmt, str(tmp_path / ("report." + fmt))])
    assert main(args) == expected
    output = capsys.readouterr().out
    assert all(s in output for s in ["osha-pel", "osha-hc", "niosh-rel", "eu"])
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["exit_code"] == expected
    assert report["worker"] == "Op\u00e9rateur \u6e2c\u5b9a"
    assert "<!doctype html>" in (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "# Noise exposure assessment" in (tmp_path / "report.md").read_text(encoding="utf-8")
    for fmt, render in [("json", to_json), ("html", to_html), ("md", to_markdown)]:
        assert (tmp_path / ("report." + fmt)).read_bytes() == render(report).encode("utf-8")


@pytest.mark.parametrize("args,expected,text", [
    (["calc", "--level", "90", "--hours", "8"], 1, "100.0"),
    (["calc", "--level", "95", "--hours", "4"], 1, "90.0"),
    (["calc", "--level", "85", "--hours", "8", "--standard", "osha-hc"], 1, "50.0"),
    (["calc", "--level", "100", "--hours", "4"], 2, "OVER LIMIT"),
    (["calc", "--level", "50", "--hours", "8"], 0, "n/a"),
    (["allowed", "--level", "100", "--standard", "niosh-rel"], 0, "15.00 min"),
    (["allowed", "--level", "100", "--standard", "niosh-rel", "--current-dose", "50"], 0, "7.50 min"),
    (["allowed", "--level", "70"], 0, "no counted dose"),
    (["protect", "--twa", "100", "--nrr", "29"], 0, "78.0 dBA"),
    (["protect", "--twa", "100", "--nrr", "29", "--safety-factor"], 0, "89.0 dBA"),
    (["protect", "--twa", "100", "--nrr", "29", "--method", "niosh"], 0, "92.5 dBA"),
    (["protect", "--twa", "100", "--nrr", "29", "--nrr2", "25"], 0, "73.0 dBA"),
    (["protect", "--twa", "100", "--method", "snr", "--lc", "102", "--snr", "30"], 0, "72.0 dBA"),
    (["protect", "--twa", "98", "--method", "hml", "--lc", "100", "--h", "30", "--m", "25", "--l", "20"], 0, "73.0 dBA"),
    (["standards"], 0, "Threshold"),
])
def test_commands(args, expected, text, capsys):
    assert main(args) == expected
    assert text in capsys.readouterr().out


@pytest.mark.parametrize("args", [
    [], ["unknown"], ["calc"], ["calc", "--level", "nan", "--hours", "8"],
    ["calc", "--level", "80", "--hours", "-1"],
    ["allowed", "--level", "100", "--standard", "bogus"],
    ["protect", "--twa", "98"], ["protect", "--twa", "98", "--method", "snr"],
    ["protect", "--twa", "98", "--method", "hml", "--lc", "100"],
    ["protect", "--twa", "nan", "--method", "snr", "--lc", "100", "--snr", "30"],
    ["log", "missing.csv"], ["tasks", "missing.json"],
    ["log", "examples/office_quiet.csv", "--standards", "eu,eu"],
    ["log", "examples/office_quiet.csv", "--standards", ""],
    ["tasks", "examples/workshop_tasks.csv", "--shift-hours", "0"],
    ["tasks", "examples/workshop_tasks.csv", "--protector", "foam:snr=34,method=snr"],
])
def test_input_error_code(args, capsys):
    assert main(args) == 3
    assert "noisedose: error:" in capsys.readouterr().err


def test_no_input_overwrite(tmp_path, capsys):
    path = tmp_path / "plan.csv"
    original = "task,hours,LAeq\na,8,85\n"
    path.write_text(original, encoding="utf-8", newline="")
    assert main(["tasks", str(path), "--json", str(path)]) == 3
    assert path.read_text(encoding="utf-8") == original


def test_distinct_output_paths(tmp_path):
    path = tmp_path / "report.txt"
    assert main(["tasks", "examples/workshop_tasks.csv", "--json", str(path), "--md", str(path)]) == 3
    assert not path.exists()


def test_module_entrypoint():
    result = subprocess.run([sys.executable, "-m", "noisedose", "allowed", "--level", "100", "--standard", "niosh-rel"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "15.00 min" in result.stdout


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.attributes = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attributes.extend(attrs)


def test_html_self_contained_and_escaping():
    evil = '<script>alert("bad")</script>&"'
    report = build_report([Segment(evil, 8, 90, 130)], worker=evil, area=evil, source=evil,
                          protectors=['<img src=x onerror=alert(1)>:nrr=29'])
    rendered = to_html(report)
    parser = Tags()
    parser.feed(rendered)
    assert "script" not in parser.tags
    assert "img" not in parser.tags
    assert "link" not in parser.tags
    assert not any(key in {"src", "href", "onerror"} for key, _ in parser.attributes)
    assert "&lt;script&gt;" in rendered
    assert "&lt;img" in rendered
    assert "prefers-color-scheme:dark" in rendered
    assert parser.tags.count("svg") == 2
    assert "50%" in rendered and "100%" in rendered
    assert "criterion" in rendered and "threshold" in rendered


def test_json_contract_and_zero_dose_null():
    report = build_report([Segment("Quiet", 8, 50)])
    result = json.loads(to_json(report))
    assert result["schema_version"] == "1.0"
    assert set(result) == {"schema_version", "generator", "worker", "area", "source",
                           "measurement_hours", "projection_shift_hours", "laeq_db", "lex8_db",
                           "metrics", "exit_code", "segments", "contributions", "protectors",
                           "uncertainty", "warnings", "recommendations", "methodology", "disclaimer"}
    assert result["metrics"][0]["twa_db"] is None
    assert "Infinity" not in to_json(report)
    assert "NaN" not in to_json(report)


def test_energy_and_dose_contributions_are_distinct():
    report = build_report(load_tasks("examples/workshop_tasks.csv"), task_based=True)
    assert sum(x["energy_percent"] for x in report["contributions"]) == pytest.approx(100)
    assert max(report["contributions"], key=lambda x: x["energy_percent"])["task"] == "Grinding"
    assert report["contributions"][0]["energy_percent"] == pytest.approx(78.06, abs=.1)
    for row in report["metrics"]:
        assert sum(x["dose_percent_by_standard"][row["standard"]] for x in report["contributions"]) == pytest.approx(row["dose_percent"])


def test_protection_does_not_remove_action_obligations():
    report = build_report([Segment("Loud", 8, 95, 141)], protectors=["foam:nrr=29"])
    assert report["exit_code"] == 2
    protector = report["protectors"][0]
    assert protector["protected_level_db"] == 84
    assert protector["eu_daily_limit_estimate"]["estimated_below_daily_limit"]
    assert not protector["eu_daily_limit_estimate"]["peak_limit_assessed"]


def test_reports_show_partial_uncertainty_and_missing_peaks():
    report = build_report([Segment("Task", 4, 90)], task_based=True)
    for output in (to_html(report), to_markdown(report)):
        assert "partial" in output
        assert "LCpeak" in output
        assert "one-sided" in output
    assert any("unmeasured" in warning for warning in report["warnings"])


def test_markdown_escaping():
    output = to_markdown(build_report([Segment("a|b\n<script>", 8, 80)], worker="<img>"))
    assert "<script>" not in output and "<img>" not in output
    assert "a&#124;b &lt;script&gt;" in output


def test_shift_projection_visible_in_console_and_markdown():
    report = build_report([Segment("Work", 2, 90, 120)], ["osha-pel"], shift_hours=12)
    output = console_table(report)
    assert "Projection shift: 12.00 h" in output
    assert "150.0" in output
    assert "Projected shift TWA" in output
    assert "Projection shift: 12.00 h" in to_markdown(report)


def test_calc_warns_about_partial_shift_and_missing_peaks(capsys):
    assert main(["calc", "--level", "70", "--hours", "1", "--standard", "eu"]) == 0
    output = capsys.readouterr().out
    assert "unmeasured periods" in output
    assert "LCpeak is missing" in output


def test_snr_cli_and_report_use_same_conservative_estimate(capsys):
    assert main(["protect", "--twa", "90", "--method", "snr", "--lc", "100", "--snr", "5"]) == 0
    assert "95.0 dBA" in capsys.readouterr().out
    report = build_report([Segment("work", 8, 90, 120)], ["eu"], lc=100,
                          protectors=["custom:snr=5,method=snr"])
    assert report["protectors"][0]["protected_level_db"] == 95


def test_hml_cli_labels_la_assumption(capsys):
    main(["protect", "--twa", "98", "--method", "hml", "--lc", "100", "--h", "30", "--m", "25", "--l", "20"])
    assert "TWA as an estimate of LA" in capsys.readouterr().out


def test_committed_reports_match_current_renderer():
    for stem in ["sawmill_dosimeter", "workshop_tasks", "office_quiet"]:
        report = json.loads((ROOT / "examples/output" / (stem + ".json")).read_text(encoding="utf-8"))
        assert to_json(report) == (ROOT / "examples/output" / (stem + ".json")).read_text(encoding="utf-8")
        assert to_html(report) == (ROOT / "examples/output" / (stem + ".html")).read_text(encoding="utf-8")
        assert to_markdown(report) == (ROOT / "examples/output" / (stem + ".md")).read_text(encoding="utf-8")
