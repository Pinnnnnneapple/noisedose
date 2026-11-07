# Contributing

Use Python 3.10 or newer. Runtime code must use the standard library; setuptools is the build backend and pytest is a development dependency.

In a local virtual environment, install the development extra and run the tests:

```sh
python -m venv .venv
# Activate .venv using the command for your shell.
python -m pip install -e ".[dev]"
python -m pytest
```

CI runs the tests and CLI acceptance examples on Ubuntu, Windows, and macOS with Python 3.10 through 3.14. The sawmill and workshop examples must return status 2; the office example must return status 0. Acceptance checks use Python `subprocess` with argument lists and inspect return codes so an expected nonzero status is handled consistently across shells.

Keep changes focused. Include a reproducer and a test when fixing a calculation or input validation bug. For a scientific change, give the governing equation, units, source and edition, an independently calculated example, and relevant boundary cases. Preserve the distinction between exchange-rate dose and exact energy exposure, actual and projected dose, and action values and exposure limits. Compare unrounded values; changing display precision must not change classification.

Read [methodology](docs/methodology.md) and [limitations](docs/limitations.md) before changing scientific behavior. Document assumptions and missing uncertainty components. Do not describe a partial uncertainty budget as a full ISO assessment, use hearing protector estimates to claim compliance, or reproduce copyrighted standards or TLV tables. Link to official sources and identify the edition consulted. Update the methodology and changelog when behavior changes.

Use the issue templates for bugs and feature requests. Supply synthetic or anonymized exposure records, the exact command, Python and operating system versions, expected results, and actual results. Remove worker identifiers, credentials, and confidential workplace details.

Contributions are distributed under the repository's [MIT license](LICENSE). Third-party standards and publications retain their own copyrights.
