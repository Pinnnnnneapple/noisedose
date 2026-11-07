"""Generate deterministic synthetic inputs and reports, without external packages.

Run from any directory: python3 examples/generate_examples.py
This is illustrative data, not measurements from a workplace or product.
"""
from __future__ import annotations

import csv
import math
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Regenerate all committed fixtures and CLI-produced HTML/JSON/Markdown."""
    folder = ROOT / "examples"
    (folder / "output").mkdir(exist_ok=True)
    for name, quiet in [("sawmill_dosimeter", False), ("office_quiet", True)]:
        with (folder / (name + ".csv")).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["timestamp", "LAeq", "LCpeak"])
            for minute in range(480):
                wave = math.sin(2 * math.pi * minute / 60)
                level = 54 + 3 * wave if quiet else 92 + 1.5 * wave
                peak = 73 + 4 * wave if quiet else 116 + 8 * wave
                stamp = datetime(2026, 1, 12, 8) + timedelta(minutes=minute)
                writer.writerow([stamp.isoformat(), "%.2f" % level, "%.2f" % peak])
    with (folder / "workshop_tasks.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["task", "duration_hours", "LAeq", "LCpeak", "n_measurements", "samples", "duration_uncertainty_hours"])
        writer.writerows([
            ["Grinding", 1.5, 97, 128, 3, "96|97|98", 0.1],
            ["Welding", 3, 88, 118, 3, "87|88|89", 0.2],
            ["Assembly", 3.5, 78, 103, 3, "77|78|79", 0.2],
        ])
    environment = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    for name, command, expected in [("sawmill_dosimeter", "log", 2),
                                    ("workshop_tasks", "tasks", 2),
                                    ("office_quiet", "log", 0)]:
        args = [sys.executable, "-m", "noisedose", command, "examples/" + name + ".csv",
                "--worker", "Synthetic operator", "--area", name.replace("_", " ")]
        for fmt in ("html", "json", "md"):
            args += ["--" + fmt, "examples/output/" + name + "." + fmt]
        if command == "tasks":
            args += ["--protector", "foam:nrr=29"]
        result = subprocess.run(args, cwd=ROOT, env=environment, capture_output=True, text=True)
        if result.returncode != expected:
            raise RuntimeError("%s: expected exit %d, got %d\n%s\n%s" % (name, expected, result.returncode, result.stdout, result.stderr))
        print(name + ": exit " + str(result.returncode))
        print(result.stdout, end="")


if __name__ == "__main__":
    main()
