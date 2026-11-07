# Changelog

## 0.1.0 — 2026-11-07

Initial project version.

- Python 3.10+ packaging with a `noisedose` console entry point and no runtime dependencies.
- Dose, TWA, LAeq, daily and weekly LEX, configurable exchange rates and thresholds, actual and projected exposure, and EU peak screening.
- CSV log and CSV/JSON task importers with measurement samples and simplified task uncertainty.
- OSHA, historical NIOSH, dual-protection, SNR and HML attenuation estimates.
- Offline HTML/SVG, Markdown and versioned JSON reports with synthetic examples and reproducible generation.
- Methodology and limitations documenting exposure, uncertainty, and hearing protection conventions.
- Contributor guidance, issue templates, and cross-platform CI for Python 3.10 through 3.14.

### Platform support and fixes before release

- Require Python 3.10+; test on 3.10–3.14 on Ubuntu, Windows and macOS.
- Fix Windows CSV fixtures by writing UTF-8 bytes without newline translation; cover LF, CRLF and lone CR inputs with and without a BOM.
- Accept trailing blank CSV lines while rejecting empty rows between records; write UTF-8 reports with LF endings and enforce LF checkouts for example outputs.
- Fix a CLI startup crash on Python 3.14 caused by unescaped `%` in argparse help strings.
