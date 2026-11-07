"""Deterministic, portable JSON, Markdown and self-contained HTML reports."""
from __future__ import annotations

import html
import json
import math
from dataclasses import asdict
from typing import Optional, Sequence

from .metrics import DEFAULT_STANDARDS, assess, dose, leq, lex8, task_uncertainty
from .models import Segment
from .protectors import analyze_protector

DISCLAIMER = ("Not a substitute for a competent person's assessment with calibrated class 1/2 "
              "instruments. Estimates depend on representative measurements and correct protector fit. "
              "NIOSH/ACGIH are guidance criteria, not OSHA permissible limits.")
METHODOLOGY = ("Actual dose uses recorded durations and each preset's threshold and exchange rate. "
               "TWA and LEX,8h are normalized to 8 hours. Projections repeat the measured exposure mix; "
               "they are estimates, not additional observations. EU action levels use unprotected exposure; "
               "87 dBA / 140 dBC limit screening receives no estimated protector credit. "
               "Exposure-limit equality is ACTION LEVEL; OVER LIMIT denotes strictly above the limit. "
               "See docs/methodology.md for formulas and references.")

_STYLE = """
:root { color-scheme:light dark; --bg:#f4f7fb; --fg:#182332;
        --card:#fff; --line:#d7e0eb; --muted:#43546b; }
* { box-sizing:border-box; }
body { background:var(--bg); color:var(--fg); margin:0;
       font:16px/1.6 system-ui,sans-serif; }
main { max-width:1100px; margin:auto; padding:36px 24px; }
h1 { font-size:2.4rem; letter-spacing:-.04em; margin-bottom:8px; }
h2 { font-size:1.2rem; }
section { background:var(--card); border:1px solid var(--line);
          border-radius:12px; padding:24px; margin:20px 0; }
table { border-collapse:collapse; width:100%; font-size:.9rem; }
td, th { text-align:right; padding:10px; border-bottom:1px solid var(--line); }
th:first-child { text-align:left; }
svg { width:100%; height:auto; font-size:11px; fill:currentColor; }
.scroll { overflow-x:auto; }
.bar { background:#2563eb; height:12px; border-radius:4px; margin-bottom:10px; }
.bar-label { display:flex; justify-content:space-between; font-size:.85rem; }
footer, .muted { color:var(--muted); font-size:.9rem; }
.badge { display:inline-block; padding:6px 14px; background:#173964;
         color:#fff; border-radius:20px; }
@media(prefers-color-scheme:dark) {
    :root { --bg:#101723; --fg:#e1eaf7; --card:#182332;
            --line:#34465f; --muted:#bbc9dd; }
}
@media print { section { break-inside:avoid; } body { font-size:11px; } }
"""


def build_report(segments: Sequence[Segment], standards: Sequence[str] = DEFAULT_STANDARDS,
                 shift_hours: Optional[float] = None, worker: str = "Not specified",
                 area: str = "Not specified", source: str = "", task_based: bool = False,
                 instrument_class: int = 2, protectors: Sequence[str] = (),
                 lc: Optional[float] = None) -> dict:
    """Build versioned report data; non-applicable numeric values are JSON null.

    Protector estimates apply to the unthresholded daily LEX,8h, allowing a common
    baseline without conflating OSHA and energy averages. LC must likewise be a
    representative C-weighted daily exposure, never LCpeak.
    """
    rows = assess(segments, standards, shift_hours)
    duration = math.fsum(x.duration_hours for x in segments)
    daily = lex8(segments)
    energies = [x.duration_hours * 10 ** ((x.level_db - daily) / 10) for x in segments]
    total = math.fsum(energies)
    contributions = [{"task": x.name, "hours": x.duration_hours, "level_db": x.level_db,
                      "energy_percent": 100 * energy / total,
                      "dose_percent_by_standard": {s: dose([x], s) for s in standards}}
                     for x, energy in zip(segments, energies)]
    code = max(row["exit_code"] for row in rows)
    recommendations = []
    if any(row.get("osha_hc_dose_percent") is not None and row["osha_hc_dose_percent"] >= 50 - 1e-9 for row in rows):
        recommendations.append("Enrol exposed workers in a hearing conservation programme; arrange audiometry, training and monitoring as applicable.")
    if code:
        recommendations.append("Engineering controls first: follow the hierarchy of controls, reduce noise at source, isolate equipment and then review exposure time.")
        recommendations.append("Select and individually fit-test hearing protection; verify continuous correct use and repeat the assessment after controls.")
    else:
        recommendations.append("Maintain controls and repeat monitoring when tasks, equipment or exposure patterns change.")
    warnings = []
    if any(x.peak_db is None for x in segments):
        warnings.append("LCpeak is missing for some or all intervals; peak screening is incomplete. Missing peaks never imply zero peak exposure.")
    uncertainty = task_uncertainty(segments, instrument_class) if task_based else None
    if uncertainty and not uncertainty["complete_sampling"]:
        warnings.append("Sampling uncertainty is unknown for tasks with fewer than two samples. The reported uncertainty is a partial budget.")
    if duration < 8:
        warnings.append("This record covers less than 8 hours. Actual exposure excludes unmeasured periods; assess them before judging the full shift.")
    if any(row["upper_action_reached"] for row in rows):
        recommendations.append("EU upper action level reached: implement a technical/organisational noise reduction programme and enforce protector use as applicable.")
    protector_results = [dict(analyze_protector(daily, p, lc=lc),
                              baseline="unthresholded daily LEX,8h") for p in protectors]
    for result in protector_results:
        result["eu_daily_limit_estimate"] = {
            "limit_db_a": 87.0,
            "estimated_below_daily_limit": result["protected_level_db"] <= 87,
            "peak_limit_assessed": False,
            "note": "Screening only; unprotected action obligations remain and peak protection requires separate evidence.",
        }
    return {"schema_version": "1.0", "generator": "noisedose 0.1.0",
            "worker": worker, "area": area, "source": source,
            "measurement_hours": duration, "projection_shift_hours": shift_hours if shift_hours is not None else duration,
            "laeq_db": leq([x.level_db for x in segments], [x.duration_hours for x in segments]),
            "lex8_db": daily, "metrics": rows, "exit_code": code,
            "segments": [asdict(x) for x in segments], "contributions": contributions,
            "protectors": protector_results,
            "uncertainty": uncertainty, "warnings": warnings,
            "recommendations": recommendations, "methodology": METHODOLOGY, "disclaimer": DISCLAIMER}


def to_json(report: dict) -> str:
    """Serialize schema 1.0 using strict JSON (no NaN or Infinity)."""
    return json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def _number(value: Optional[float], digits: int = 1) -> str:
    return "n/a" if value is None else format(value, "." + str(digits) + "f")


def console_table(report: dict) -> str:
    """Return a side-by-side standards comparison for a terminal."""
    rows = report["metrics"]
    width = 20
    def line(label: str, values: Sequence[str]) -> str:
        return label.ljust(22) + " | ".join(v.rjust(width) for v in values)
    return "\n".join([
        "Exposure: %.2f h | LAeq %.1f dBA | LEX,8h %.1f dBA" % (report["measurement_hours"], report["laeq_db"], report["lex8_db"]),
        line("Standard", [r["standard"] for r in rows]),
        line("Actual dose (%)", [_number(r["dose_percent"]) for r in rows]),
        line("8h TWA (dBA)", [_number(r["twa_db"]) for r in rows]),
        line("Projected 8h dose (%)", [_number(r["projected_8h_dose_percent"]) for r in rows]),
        line("Projected 8h TWA", [_number(r["projected_8h_twa_db"]) for r in rows]),
        line("Projected shift dose", [_number(r["projected_shift_dose_percent"]) for r in rows]),
        line("Projected shift TWA", [_number(r["projected_shift_twa_db"]) for r in rows]),
        line("Status", [r["status"] for r in rows]),
        "Projection shift: %.2f h (dose in %%; TWA in dBA)." % report["projection_shift_hours"],
        "EU dose is an energy index relative to 85 dBA, not a legal dose limit.",
        "Status uses actual exposure; projections assume the same exposure mix.",
    ])


def _md(value: object) -> str:
    return html.escape(str(value), quote=True).replace("|", "&#124;").replace("\n", " ").replace("\r", " ")


def to_markdown(report: dict) -> str:
    """Render a readable Markdown report, escaping raw HTML and table delimiters."""
    text = ["# Noise exposure assessment", "", "Worker: " + _md(report["worker"]),
            "", "Area: " + _md(report["area"]), "", "Source: " + _md(report["source"]), "",
            "Measured: %.2f h; LAeq: %.1f dBA; LEX,8h: %.1f dBA." % (report["measurement_hours"], report["laeq_db"], report["lex8_db"]), "",
            "Projection shift: %.2f h (representative-pattern estimate)." % report["projection_shift_hours"], "",
            "| Metric | " + " | ".join(_md(r["standard"]) for r in report["metrics"]) + " |",
            "|---|" + "---|" * len(report["metrics"])]
    for label, key in [("Actual dose (%)", "dose_percent"), ("8h TWA (dBA)", "twa_db"),
                       ("Projected 8h dose (%)", "projected_8h_dose_percent"),
                       ("Projected 8h TWA (dBA)", "projected_8h_twa_db"),
                       ("Projected shift dose (%)", "projected_shift_dose_percent"),
                       ("Projected shift TWA (dBA)", "projected_shift_twa_db"), ("Status", "status")]:
        text.append("| " + label + " | " + " | ".join(_md(r[key]) if key == "status" else _number(r[key]) for r in report["metrics"]) + " |")
    text += ["", "## Task energy contribution", "", "Percent of unthresholded acoustic energy; differs from OSHA dose share.", "",
             "| Task | Hours | LAeq dBA | Energy % |", "|---|---:|---:|---:|"]
    text += ["| %s | %.3f | %.1f | %.1f |" % (_md(x["task"]), x["hours"], x["level_db"], x["energy_percent"]) for x in report["contributions"]]
    for row in report["metrics"]:
        if row["peak"]:
            peak = row["peak"]
            text += ["", "EU LCpeak: %s dBC; %s. Peak protection is not inferred from NRR/SNR/HML." % (_number(peak["level_db_c"]), peak["status"])]
    for x in report["protectors"]:
        text += ["", "Protector: " + _md(x.get("name", "")) + " (" + _md(x["method"]) + "), estimated %.1f dBA: %s." % (x["protected_level_db"], _md(x["rating"]))]
        text += ["", "Estimated daily EU limit screen: " + ("at/below 87 dBA" if x["eu_daily_limit_estimate"]["estimated_below_daily_limit"] else "above 87 dBA") + ". Unprotected action obligations remain; peak protection is not assessed."]
        text += ["- " + _md(note) for note in x["assumptions"]]
    if report["uncertainty"]:
        u = report["uncertainty"]
        text += ["", "Simplified uncertainty: u = %.2f dB; U = %.2f dB (k = 1.65, one-sided ~95%%). Upper estimate %.2f dBA. Sampling budget %s." % (u["combined_standard_db"], u["expanded_db"], u["upper_95_db"], "complete" if u["complete_sampling"] else "partial")]
    text += ["", "## Recommendations", ""] + ["- " + _md(x) for x in report["recommendations"]]
    text += ["", "## Notes", ""] + ["- " + _md(x) for x in report["warnings"]]
    text += ["", report["methodology"], "", report["disclaimer"], ""]
    return "\n".join(text)


def _svg_chart(series: Sequence[tuple], ylabel: str, guides: Sequence[tuple] = (),
               zero_based: bool = True) -> str:
    """Render numerical step-series data as an accessible inline SVG."""
    xs = [point[0] for _, points in series for point in points]
    ys = [point[1] for _, points in series for point in points] + [value for _, value in guides]
    xmax = max(xs) if xs else 1
    low, high = min(ys, default=0), max(ys, default=100)
    ymin = min(0, low) if zero_based else low - 8
    ymax = high + max(2, (high - ymin) * 0.08)
    if ymax <= ymin:
        ymax = ymin + 1
    def xy(x: float, y: float) -> str:
        return "%.2f,%.2f" % (65 + x / (xmax or 1) * 700, 235 - (y - ymin) / (ymax - ymin) * 200)
    colors = ["#2563eb", "#db2777", "#059669", "#d97706", "#7c3aed"]
    out = ['<svg viewBox="0 0 820 290" role="img" aria-label="' + html.escape(ylabel, quote=True) + '">',
           '<text x="10" y="18">' + html.escape(ylabel) + '</text>',
           '<path d="M65 35 V235 H765" fill="none" stroke="currentColor"/>',
           '<text x="65" y="255">0 h</text><text x="700" y="255">%.2f h</text>' % xmax]
    for label, value in guides:
        y = xy(0, value).split(",")[1]
        out.append('<line x1="65" x2="765" y1="%s" y2="%s" stroke="currentColor" stroke-dasharray="4 4"/><text x="68" y="%s">%s</text>' % (y, y, y, html.escape(label)))
    for i in range(5):
        value = ymin + (ymax - ymin) * i / 4
        y = xy(0, value).split(",")[1]
        out.append('<text x="2" y="%s">%.0f</text>' % (y, value))
    for i, (name, points) in enumerate(series):
        color = colors[i % len(colors)]
        out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2"/>' % (" ".join(xy(x, y) for x, y in points), color))
        out.append('<text x="%d" y="280" fill="%s">%s</text>' % (65 + i * 145, color, html.escape(name)))
    return "".join(out) + "</svg>"


def to_html(report: dict) -> str:
    """Render one offline HTML file with escaped text and SVG charts, without JS."""
    escape = html.escape
    rows = report["metrics"]
    header = "<tr><th>Metric</th>" + "".join("<th>" + escape(x["standard"]) + "</th>" for x in rows) + "</tr>"
    body = []
    for label, key in [("Actual dose (%)", "dose_percent"), ("8h TWA (dBA)", "twa_db"),
                       ("Projected 8h dose (%)", "projected_8h_dose_percent"),
                       ("Projected 8h TWA (dBA)", "projected_8h_twa_db"),
                       ("Projected shift dose (%)", "projected_shift_dose_percent"),
                       ("Projected shift TWA (dBA)", "projected_shift_twa_db"), ("Status", "status")]:
        body.append("<tr><th>" + label + "</th>" + "".join("<td>" + (escape(x[key]) if key == "status" else _number(x[key])) + "</td>" for x in rows) + "</tr>")
    segments = [Segment(**{**x, "samples": tuple(x["samples"])}) for x in report["segments"]]
    series = []
    for row in rows:
        elapsed, cumulative = 0.0, 0.0
        points = [(0, 0)]
        for x in segments:
            elapsed += x.duration_hours
            cumulative += dose([x], row["standard"])
            points.append((elapsed, cumulative))
        series.append((row["standard"], points))
    history, elapsed = [], 0.0
    for x in segments:
        history.extend([(elapsed, x.level_db), (elapsed + x.duration_hours, x.level_db)])
        elapsed += x.duration_hours
    guide_labels = {}
    for row in rows:
        for label, key in [("criterion", "criterion_db"), ("threshold", "threshold_db")]:
            if row[key] is not None:
                labels = guide_labels.setdefault(row[key], [])
                if label not in labels:
                    labels.append(label)
    guides = [(" / ".join(labels) + " " + str(value) + " dBA", value)
              for value, labels in guide_labels.items()]
    bars = []
    for item in sorted(report["contributions"], key=lambda x: -x["energy_percent"]):
        bars.append('<div class="bar-label">%s <span>%.1f%%</span></div><div class="bar" style="width:%.4f%%"></div>' % (escape(item["task"]), item["energy_percent"], item["energy_percent"]))
    # Bound the visible log contribution list, retaining all intervals in JSON.
    if len(bars) > 30:
        bars = bars[:30] + ["<p>Largest 30 intervals shown; full contributions are in JSON.</p>"]
    protectors = "<p>No protector estimate requested.</p>"
    if report["protectors"]:
        protector_rows = []
        for item in report["protectors"]:
            below = item["eu_daily_limit_estimate"]["estimated_below_daily_limit"]
            protector_rows.append(
                "<tr><td>%s</td><td>%s</td><td>%.1f</td><td>%s</td><td>%s</td></tr>"
                % (escape(item["name"]), escape(item["method"]),
                   item["protected_level_db"], escape(item["rating"]),
                   "at/below 87 dBA" if below else "above 87 dBA")
            )
        protectors = (
            '<div class="scroll"><table><tr><th>Protector</th><th>Method</th>'
            "<th>Estimated dBA</th><th>Rating</th><th>EU daily limit estimate</th></tr>"
            + "".join(protector_rows)
            + "</table></div><p>Baseline: unthresholded daily LEX,8h. "
            "Unprotected action obligations remain. Peak protection is not assessed.</p>"
            + "".join("<p>" + escape(note) + "</p>"
                      for item in report["protectors"] for note in item["assumptions"])
        )
    uncertainty = ""
    if report["uncertainty"]:
        u = report["uncertainty"]
        uncertainty = (
            "<h2>Task uncertainty (simplified)</h2><p>u = %.2f dB; U = %.2f dB; "
            "k = 1.65 (one-sided approximately 95%%). Upper estimate %.2f dBA. "
            "Sampling budget: %s.</p>"
            % (u["combined_standard_db"], u["expanded_db"], u["upper_95_db"],
               "complete" if u["complete_sampling"] else "partial")
        )
    peaks = "".join(
        "<p>EU LCpeak: %s dBC; %s. Upper action: %s. "
        "Missing peaks mean incomplete assessment.</p>"
        % (_number(row["peak"]["level_db_c"]), escape(row["peak"]["status"]),
           "reached" if row["peak"].get("upper_action_reached") else "not reached / unknown")
        for row in rows if row["peak"]
    )
    # Escape metadata at the point of insertion; assembled sections contain only
    # fixed markup, escaped text and validated numerical values.
    title = "Noise exposure assessment"
    status = ("BELOW ACTION", "ACTION LEVEL", "OVER LIMIT")[report["exit_code"]]
    summary = (
        "Measured %.2f h · LAeq %.1f dBA · LEX,8h %.1f dBA · Projection shift %.2f h"
        % (report["measurement_hours"], report["laeq_db"], report["lex8_db"],
           report["projection_shift_hours"])
    )
    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        "<title>" + title + "</title><style>" + _STYLE + "</style></head><body><main>",
        '<p class="muted">NOISEDOSE / OCCUPATIONAL EXPOSURE</p><h1>' + title + "</h1>",
        '<span class="badge">' + status + "</span>",
        "<p>Worker: " + escape(report["worker"]) + " · Area: " + escape(report["area"]) + "</p>",
        '<p class="muted">Source: ' + escape(report["source"]) + "</p>",
        "<section><p>" + summary + '</p><div class="scroll"><table>' + header,
        "".join(body) + "</table></div>" + peaks + "</section>",
        "<section><h2>Cumulative dose over time</h2>",
        _svg_chart(series, "Dose / EU energy index (%)", [("50%", 50), ("100%", 100)]),
        "<p>EU curve is an energy index relative to 85 dBA; action levels and limits "
        "use LEX,8h and LCpeak.</p></section>",
        "<section><h2>Level time history</h2>",
        _svg_chart([("LAeq", history)], "Level (dBA)", guides, zero_based=False) + "</section>",
        "<section><h2>Task energy contribution</h2>",
        "<p>Share of unthresholded acoustic energy; OSHA dose shares can differ.</p>",
        "".join(bars) + "</section>",
        "<section><h2>Hearing protection</h2>" + protectors + uncertainty + "</section>",
        "<section><h2>Recommendations</h2><ul>",
        "".join("<li>" + escape(x) + "</li>" for x in report["recommendations"]),
        "</ul><h2>Assessment notes</h2><ul>",
        "".join("<li>" + escape(x) + "</li>" for x in report["warnings"]),
        "</ul></section><footer><p>" + escape(report["methodology"]),
        "</p><p>" + escape(report["disclaimer"]) + "</p></footer></main></body></html>",
    ]
    return "".join(parts)
