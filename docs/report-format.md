# Report contract

`noisedose log` and `noisedose tasks` accept `--json`, `--md` and `--html` together. HTML is one file with inline CSS and SVG, without scripts, external fonts, images or network requests. All input-derived HTML text is escaped. Markdown also escapes raw HTML and table delimiters.

## JSON version 1.0

The root `schema_version` string is `"1.0"`; `generator` identifies the package version. Existing fields retain their meaning within this schema version. Consumers should allow additional fields and select metric rows by `standard`, not array position. Missing, undefined or unassessed numeric quantities are `null`, never nonstandard JSON `NaN`/`Infinity`. In particular, a zero thresholded dose has no finite TWA.

| Field | Meaning |
|---|---|
| `worker`, `area`, `source` | User information and input path |
| `measurement_hours` | Sum of actual recorded/task durations |
| `projection_shift_hours` | Assumed shift for representative-pattern projection |
| `laeq_db`, `lex8_db` | Unthresholded actual energy average and eight-hour normalized exposure |
| `metrics` | One object per selected preset |
| `exit_code` | Maximum unprotected actual status across selected presets |
| `segments` | Validated input records, including samples, timing uncertainty and optional timestamps |
| `contributions` | Per-record acoustic energy shares and additive dose contributions per standard |
| `protectors` | Estimated attenuation and protected daily level, method, assumptions, selection rating and EU daily limit estimate |
| `uncertainty` | Simplified task budget, or null for log assessments |
| `warnings`, `recommendations` | Human-readable assessment notes and recommended responses |
| `methodology`, `disclaimer` | Interpretation and assessment limits |

Each metric includes `dose_percent`, `dose_basis`, `twa_db`, `lex8_db`, `criterion_db`, `threshold_db`, `exchange_db`, `status`, `exit_code`, projected 8-hour and shift dose/TWA, the separate OSHA HC dose when applicable, and EU upper-action/peak information. EU dose is an energy index relative to 85 dBA, not a legal dose. Actual status is independent of projections and protector estimates.

`peak` is present for EU rows. If no LCpeak observations exist, its level is null and its status is `NOT ASSESSED`. With partial peak observations, it reports the observed maximum and a root warning identifies incomplete coverage. Scalar protector attenuation is never subtracted from peak levels.

`contributions[].energy_percent` sums to 100 over the record. `dose_percent_by_standard` contains additive dose **percentage points**, summing to each standard's actual dose. These quantities differ because OSHA uses an exchange rule and threshold distinct from energy averaging. For logs, records are labelled readings; the HTML shows the largest 30 contributions, while JSON and Markdown retain all records.

Task uncertainty records each energy weight, known sampling standard uncertainty and duration contribution. `complete_sampling=false` means some sampling components are unknown. The numeric subtotal and upper estimate are then partial, not a validated complete coverage bound. Defaults for instrument, position and exact timing are modeling assumptions even when `complete_sampling=true`.

Reports are deterministic: they contain no generated-at timestamp, random ID or environment-dependent absolute path unless an absolute source path was supplied. Run `python3 examples/generate_examples.py` to reproduce the committed examples.

The console and Markdown outputs identify the projected shift duration explicitly. A projection describes a repeating exposure mix and does not add unobserved dose to the actual-status calculation.
