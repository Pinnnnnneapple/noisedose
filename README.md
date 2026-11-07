# noisedose

Occupational noise dose, exposure and hearing-protector estimates from ordinary CSV and JSON files.

[![CI](https://github.com/Pinnnnnneapple/noisedose/actions/workflows/ci.yml/badge.svg)](https://github.com/Pinnnnnneapple/noisedose/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python 3.9–3.13](https://img.shields.io/badge/python-3.9%E2%80%933.13-blue.svg)

## Why

Safety officers, industrial hygienists and small workshops often receive noise logs tied to a particular dosimeter brand, or maintain exposure calculations in spreadsheets that are difficult to review. noisedose provides a readable, reproducible calculation from exported data, with the settings and assumptions visible in every assessment.

Use it to compare exposure criteria, identify the tasks contributing most acoustic energy, explore controls, and share a report that opens offline. A report supports a competent person's assessment; it does not certify workplace compliance.

## Features

- OSHA PEL and hearing conservation, NIOSH REL, ACGIH TLV screening, and EU daily/peak comparisons.
- Energy LAeq, daily LEX,8h, weekly LEX, configurable 3/4/5 dB exchange rates, thresholded dose, and dose/TWA conversion.
- Actual exposure, projected 8-hour exposure and projected extended-shift exposure kept separate.
- Timestamped CSV logs with preambles, common column names, decimal commas and configurable intervals; task CSV or JSON with repeated measurements.
- Simplified task uncertainty with separate sampling, duration, instrument and microphone-position components.
- OSHA base and 50% estimates, historical NIOSH type derating, dual protection, SNR, HML and over-protection guidance.
- Self-contained HTML with SVG charts, light/dark appearance and escaped user text; Markdown and strict, versioned JSON.
- Python standard library at runtime. No account, vendor SDK or network needed.

## Install

Python 3.9 or later is required.

```sh
pip install git+https://github.com/Pinnnnnneapple/noisedose
```

From a checkout:

```sh
python3 -m pip install -e .
noisedose standards
```

For development, install `.[dev]` to include pytest. To run directly without installing:

```sh
PYTHONPATH=src python3 -m noisedose standards
PYTHONPATH=src python3 -m pytest -q
```

PowerShell users can set `$env:PYTHONPATH = "src"` and use `python` in place of `python3`.

## Quickstart

All example inputs are **synthetic** and reproducible. The following output is captured from the CLI.

```sh
noisedose log examples/sawmill_dosimeter.csv --html /tmp/nd.html
```

```text
Exposure: 8.00 h | LAeq 92.1 dBA | LEX,8h 92.1 dBA
Standard                          osha-pel |              osha-hc |            niosh-rel |                   eu
Actual dose (%)                      133.4 |                133.4 |                519.2 |                516.2
8h TWA (dBA)                          92.1 |                 92.1 |                 92.2 |                 92.1
Projected 8h dose (%)                133.4 |                133.4 |                519.2 |                516.2
Projected 8h TWA                      92.1 |                 92.1 |                 92.2 |                 92.1
Projected shift dose                 133.4 |                133.4 |                519.2 |                516.2
Projected shift TWA                   92.1 |                 92.1 |                 92.2 |                 92.1
Status                          OVER LIMIT |           OVER LIMIT |           OVER LIMIT |           OVER LIMIT
Projection shift: 8.00 h (dose in %; TWA in dBA).
EU dose is an energy index relative to 85 dBA, not a legal dose limit.
Status uses actual exposure; projections assume the same exposure mix.
```

This command exits **2**. Open `/tmp/nd.html` to view the offline report. The sawmill's OSHA PEL TWA is approximately 92 dBA. The EU percentage is an informational energy index; the EU limit comparison uses LEX,8h and LCpeak.

Assess the workshop's known tasks, including repeated measurement samples:

```sh
noisedose tasks examples/workshop_tasks.csv \
  --worker "Workshop operator" --area "Fabrication" \
  --protector "foam:nrr=29" \
  --html workshop.html --json workshop.json --md workshop.md
```

```text
Exposure: 8.00 h | LAeq 90.8 dBA | LEX,8h 90.8 dBA
Standard                          osha-pel |              osha-hc |            niosh-rel |                   eu
Actual dose (%)                       49.5 |                 77.9 |                375.0 |                380.7
8h TWA (dBA)                          84.9 |                 88.2 |                 90.7 |                 90.8
Projected 8h dose (%)                 49.5 |                 77.9 |                375.0 |                380.7
Projected 8h TWA                      84.9 |                 88.2 |                 90.7 |                 90.8
Projected shift dose                  49.5 |                 77.9 |                375.0 |                380.7
Projected shift TWA                   84.9 |                 88.2 |                 90.7 |                 90.8
Status                        ACTION LEVEL |         ACTION LEVEL |           OVER LIMIT |           OVER LIMIT
Projection shift: 8.00 h (dose in %; TWA in dBA).
EU dose is an energy index relative to 85 dBA, not a legal dose limit.
Status uses actual exposure; projections assume the same exposure mix.
Simplified task uncertainty: u=1.88 dB; U=3.10 dB (k=1.65, one-sided ~95%; complete sampling budget)
```

The workshop exits **2** because the NIOSH and EU comparisons exceed their criteria. OSHA requires hearing-conservation action, while the independently calculated PEL dose remains below 100%. Grinding contributes approximately 78% of the acoustic energy. Protector estimates do not remove unprotected action obligations.

```sh
noisedose log examples/office_quiet.csv
```

The office exits **0**, with LAeq and LEX,8h approximately 54.5 dBA. Thresholded dosimeter doses are zero; their TWA is shown as `n/a`, not 0 dBA.

### Quick calculations

```sh
noisedose calc --level 95 --hours 4 --standard osha-pel
```

```text
Exposure: 4.00 h | LAeq 95.0 dBA | LEX,8h 92.0 dBA
Standard                          osha-pel
Actual dose (%)                      100.0
8h TWA (dBA)                          90.0
Projected 8h dose (%)                200.0
Projected 8h TWA                      95.0
Projected shift dose                 100.0
Projected shift TWA                   90.0
Status                        ACTION LEVEL
Projection shift: 4.00 h (dose in %; TWA in dBA).
EU dose is an energy index relative to 85 dBA, not a legal dose limit.
Status uses actual exposure; projections assume the same exposure mix.
Note: LCpeak is missing for some or all intervals; peak screening is incomplete. Missing peaks never imply zero peak exposure.
Note: This record covers less than 8 hours. Actual exposure excludes unmeasured periods; assess them before judging the full shift.
```

This exact 100% PEL dose exits **1**: hearing-conservation action applies and the permissible dose has been reached, without a strict exceedance.

```sh
noisedose allowed --level 100 --standard niosh-rel
```

```text
niosh-rel: 0.2500 h (15.00 min) until 100% dose at 100.0 dBA
```

```sh
noisedose protect --twa 100 --nrr 29 --type foam --method niosh
```

```text
Estimated protected level: 92.5 dBA (insufficient)
Rating-based estimate; verify individual fit and correct continuous use.
Historical NIOSH 1998 derating; individual quantitative fit testing is recommended by current NIOSH guidance.
```

This comparison implements the requested **historical 1998** NIOSH derating. Current NIOSH guidance favors individual quantitative fit testing; see [methodology and references](docs/methodology.md).

### Other options

```sh
# Project the observed exposure mix to a 12-hour shift; actual dose stays separate.
noisedose log examples/sawmill_dosimeter.csv --shift-hours 12

# Select criteria, including ACGIH, or use a known fixed logging interval.
noisedose log examples/office_quiet.csv --standards osha-hc,niosh-rel,acgih-tlv,eu
noisedose log examples/office_quiet.csv --interval-seconds 60

# OSHA Appendix B base estimate: 100 - (29 - 7) = 78 dBA.
noisedose protect --twa 100 --nrr 29 --method osha

# OSHA 50% variant: 100 - (29 - 7)/2 = 89 dBA.
noisedose protect --twa 100 --nrr 29 --method osha50

# SNR and HML need representative LC for the same period, never LCpeak.
noisedose protect --twa 98 --method snr --lc 100 --snr 30
noisedose protect --twa 98 --method hml --lc 100 --h 30 --m 25 --l 20

# Approximate combined nominal dual NRR: max(29, 25) + 5 = 34.
noisedose protect --twa 100 --nrr 29 --nrr2 25

# Time remaining until 100% when 50% is already accumulated.
noisedose allowed --level 100 --standard niosh-rel --current-dose 50
```

`--protector` may be repeated in `log` and `tasks`. Its default method is `osha50`; specify alternatives as `"foam:nrr=29,method=niosh"`, `"custom:snr=30,method=snr"`, or `"custom:h=30,m=25,l=20,method=hml"`. SNR/HML in reports also require `--lc`. The report baseline is unthresholded daily LEX,8h; command `protect --twa` uses the level you supply. `--nrr2` combines nominal ratings **before** the selected derating; it is a simplified approximation, not every OSHA dual-protection procedure.

Bare `--protector foam` and `--protector earmuff` use clearly labelled generic examples:

| Generic example | NRR | SNR |
|---|---:|---:|
| Foam plug | 29 | 34 |
| Earmuff | 25 | 30 |

These are illustrative ratings, not tested products or recommendations.

## Input formats

### Time-series CSV

```csv
timestamp,LAeq,LCpeak
2026-01-12T08:00:00,92.0,124.0
2026-01-12T08:01:00,93.0,126.0
```

Each reading describes its **forward interval**. The final interval uses the median of preceding intervals. This two-row example represents two minutes. Verify this convention against the instrument's export semantics. Use `--interval-seconds` for a known fixed interval or a file without timestamps.

Recognized A-weighted columns include `LAeq`, `LAeq,T`, `LAS`, `LAF`, `Lavg`, and `dBA`, with common unit suffixes. `LCpeak` or `Peak` supplies an optional C-weighted peak **only if its weighting is verified**. Multiple level columns require `--level-column`; multiple peaks require `--peak-column`. LAS/LAF snapshots and instrument-specific Lavg settings need professional interpretation before use as representative equivalent levels.

Comma, semicolon and tab delimiters, UTF-8 BOM, and preamble lines are supported. Decimal commas work in semicolon/tab files. Use ISO datetimes, clock times or numeric elapsed seconds; timestamps must strictly increase. Midnight rollover from clock-only data is not guessed. Malformed rows after the header produce an input error with location context.

### Task CSV or JSON

```csv
task,duration_hours,LAeq,LCpeak,n_measurements,samples,duration_uncertainty_hours
Grinding,1.5,97,128,3,96|97|98,0.1
Welding,3,88,118,3,87|88|89,0.2
Assembly,3.5,78,103,3,77|78|79,0.2
```

```json
{"tasks": [
  {"name": "Grinding", "hours": 1.5, "LAeq": 97,
   "LCpeak": 128, "samples": [96, 97, 98],
   "duration_uncertainty_hours": 0.1}
]}
```

JSON also accepts a top-level task array. Duration units are always hours; uncertainty is a **standard uncertainty in hours**. When a task's LAeq is absent, the loader derives the energy mean of equal-duration samples. Supplied summaries remain authoritative. A sample count without raw samples does not supply sampling uncertainty. Missing duration uncertainty assumes exact duration. See [input and uncertainty assumptions](docs/methodology.md).

## Library usage

```python
from noisedose import Segment, dose, leq, lex8, twa_from_dose
from noisedose.metrics import Standard, allowed_time, task_uncertainty, weekly_lex
from noisedose.io import load_tasks
from noisedose.report import build_report, to_html, to_json

tasks = [Segment("Saw", 4, 95), Segment("Assembly", 4, 78)]
assert dose(tasks, "osha-pel") == 100.0
assert twa_from_dose(100, "osha-pel") == 90.0
print(round(leq([80, 90], [1, 1]), 1))  # 87.4
print(round(lex8([Segment("Work", 10, 85)]), 2))  # 85.97

custom = Standard("custom-4dB", criterion_level=88, exchange_rate=4, threshold=80)
assert allowed_time(92, custom) == 4.0
assert weekly_lex([85, 85, 85, 85, 85]) == 85.0

plan = load_tasks("examples/workshop_tasks.csv")
uncertainty = task_uncertainty(plan, instrument_class=1)
report = build_report(plan, task_based=True, instrument_class=1, worker="Operator")
with open("assessment.html", "w", encoding="utf-8") as stream:
    stream.write(to_html(report))
```

`Segment` validates positive finite durations and finite level values. Custom dose criteria may use a different criterion duration via `criterion_hours`; built-in presets use 8 hours. JSON schema version `1.0` preserves zero-dose TWA as `null`. See the [report contract](docs/report-format.md).

## Reference settings

| Preset | Criterion dBA | Exchange dB | Integration threshold dBA | Interpretation |
|---|---:|---:|---:|---|
| `osha-pel` | 90 | 5 | 90 | PEL: 100% dose; separate HC action check |
| `osha-hc` | 90 | 5 | 80 | HC action: 50% dose / 85 dBA TWA |
| `niosh-rel` | 85 | 3 | 80 | REL: 100% dose |
| `acgih-tlv` | 85 | 3 | 80 | TLV screening: 100% dose; verify current edition |
| `eu` | 85 reference | exact energy | none | Unthresholded energy index; assess LEX/peak values below |

| EU value | LEX,8h dBA | LCpeak dBC |
|---|---:|---:|
| Lower action | 80 | 135 |
| Upper action | 85 | 137 |
| Limit, accounting for protection actually afforded | 87 | 140 |

EU action values always use unprotected exposure. Reports conservatively screen unprotected exposure against the limit and give separate estimated protected daily levels. A-weighted scalar attenuation does not demonstrate protected peak compliance. Each report includes the highest observed peak and flags incomplete peak records.

## Methodology summary

With task duration `t_i` in hours and level `L_i` in dB(A):

```text
LAeq,T = 10 log10(sum(t_i * 10^(L_i/10)) / sum(t_i))
LEX,8h = 10 log10(sum((t_i/8) * 10^(L_i/10)))
T_allowed(L) = 8 / 2^((L - Lc)/Q)
D (%) = 100 * sum(t_i / T_allowed(L_i)), counting L_i >= threshold
TWA = Lc + (Q/log10(2)) * log10(D/100)
```

The NIOSH/ACGIH reported TWA convention uses `85 + 10 log10(D/100)`. Exact 3 dB dose doubling and exact energy doubling differ slightly: 200% corresponds to 88.0103 dBA under this reporting convention, displayed as 88.0. OSHA uses the unrounded `5/log10(2)` coefficient internally rather than 16.61. The EU index uses exact energy without a threshold.

The simplified task model weights sampling and duration uncertainties by each task's energy share; shared instrument and position errors do not average down across tasks. `U = 1.65u` is an approximate **one-sided 95% upper uncertainty**, not a symmetric 95% interval or full ISO 9612 conformity. Unknown sampling variance yields a labelled partial budget. Status uses measured point estimates, without automatically adding uncertainty or assuming projected exposure occurred.

Full formulas, assumptions and primary references for OSHA 29 CFR 1910.95 Appendices A/B, NIOSH 98-126, ACGIH, Directive 2003/10/EC, ISO 9612:2009, ISO 4869-2 and EN 458 are in [docs/methodology.md](docs/methodology.md).

## Exit codes for automation

| Code | Meaning |
|---:|---|
| 0 | Below selected action levels; utility commands succeeded |
| 1 | Action level reached, including an exact limit boundary |
| 2 | Strictly above a selected permissible/recommended limit |
| 3 | Invalid input, invalid command syntax or file error |

The maximum severity across selected criteria wins. OSHA action screening always checks the HC threshold, even with only `osha-pel` selected; its over-limit check uses the separate PEL dose. NIOSH/ACGIH use 100% as their action/limit boundary. EU uses the lower action value, flags upper action separately, and screens both daily and peak limits. Equality at a limit is actionable. Labels are calculation conventions, not a legal determination. Projections and protector estimates do not lower the actual unprotected status.

Shell scripts should capture expected assessment codes explicitly:

```python
import subprocess

result = subprocess.run(["noisedose", "log", "examples/sawmill_dosimeter.csv"])
if result.returncode == 3:
    raise RuntimeError("Assessment input failed")
if result.returncode >= 1:
    print("Exposure requires review")
```

## Examples, development and verification

The repository includes three inputs and nine reports under [examples/output](examples/output): sawmill, workshop and office, each as HTML, JSON and Markdown. Regenerate them deterministically:

```sh
python3 examples/generate_examples.py
PYTHONPATH=src python3 -m pytest -q
```

Tests cover hand calculations, thresholds, inverse conversions, task uncertainty, parsing failures, CLI return codes, report escaping, strict JSON and committed report consistency. CI runs Python 3.9–3.13 on Ubuntu, Windows and macOS and checks the installed console script against all examples. No dependencies need to be installed when running with `PYTHONPATH=src` and an existing pytest.

## Limitations and disclaimer

**Not a substitute for a competent person's assessment with calibrated class 1/2 instruments.** Input must be representative of actual worker exposure, with known weighting, response, averaging settings and instrument calibration. Timestamp inference, incomplete shifts, missing peaks and thresholded exports can affect conclusions. Values already averaged or thresholded by an instrument cannot reconstruct missing acoustic information.

ISO 9612:2009 is a historical reference and the uncertainty model is simplified. Protector estimates assume correct, continuous use and do not assure individual fit. Historical NIOSH derating is retained for comparison; fit testing is preferred. ACGIH criteria require checking the current licensed edition. EU national implementation and other jurisdiction-specific obligations require professional interpretation. Read [docs/limitations.md](docs/limitations.md) before using results for a workplace decision.

## Roadmap

- Named, documented importer profiles for additional vendor exports.
- User-supplied fit-test attenuation and frequency-band protector data.
- Broader uncertainty models with explicit covariance and sampling strategies.
- Multiday CLI assessments and optional translation of report text.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Formula changes need a primary reference, explicit assumptions and an independent hand-checkable test. Use the issue templates for bug reports and feature requests.

## License

[MIT](LICENSE). Copyright (c) 2026 noisedose contributors.
