"""Command-line interface with assessment statuses suitable for automation."""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Optional, Sequence

from . import __version__
from .io import load_log, load_tasks
from .metrics import DEFAULT_STANDARDS, STANDARDS, get_standard, time_until_100
from .models import Segment
from .protectors import (dual_nrr, hml_exposure, niosh_exposure, osha_exposure,
                         protection_rating, snr_exposure)
from .report import build_report, console_table, to_html, to_json, to_markdown


class InputError(ValueError):
    """Invalid CLI syntax or a physically invalid value."""


class Parser(argparse.ArgumentParser):
    """Use the documented input-error code rather than argparse's code 2."""

    def error(self, message: str) -> None:
        raise InputError(message)


def _parser() -> Parser:
    parser = Parser(prog="noisedose", description="Occupational noise dose and exposure reports (dB, hours).")
    parser.add_argument("--version", action="version", version="noisedose " + __version__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("log", "tasks"):
        sub = commands.add_parser(name, help="Assess a " + ("time-series CSV" if name == "log" else "task CSV/JSON plan"))
        sub.add_argument("file", type=Path)
        sub.add_argument("--standards", default=",".join(DEFAULT_STANDARDS))
        sub.add_argument("--shift-hours", type=float, help="Project representative measured mix to this shift; actual dose is unchanged")
        sub.add_argument("--protector", action="append", default=[], help="e.g. foam:nrr=29 or foam:nrr=29,method=niosh; repeatable")
        sub.add_argument("--worker", default="Not specified")
        sub.add_argument("--area", default="Not specified")
        sub.add_argument("--lc", type=float, help="Representative daily C-weighted exposure for SNR/HML (not LCpeak)")
        sub.add_argument("--instrument-class", type=int, choices=(1, 2), default=2)
        for fmt in ("html", "json", "md"):
            sub.add_argument("--" + fmt, type=Path)
        if name == "log":
            sub.add_argument("--interval-seconds", type=float, help="Override inferred interval duration")
            sub.add_argument("--level-column", help="Explicit A-weighted level column")
            sub.add_argument("--peak-column", help="Explicit C-weighted peak column")
    calc = commands.add_parser("calc", help="Calculate dose and 8h TWA at a constant level")
    calc.add_argument("--level", type=float, required=True)
    calc.add_argument("--hours", type=float, required=True)
    calc.add_argument("--standard", choices=STANDARDS, default="osha-pel")
    allowed = commands.add_parser("allowed", help="Hours to 100%% dose under preset settings")
    allowed.add_argument("--level", type=float, required=True)
    allowed.add_argument("--standard", choices=STANDARDS, default="osha-pel")
    allowed.add_argument("--current-dose", type=float, default=0)
    protect = commands.add_parser("protect", help="Estimate level beneath a hearing protector")
    protect.add_argument("--twa", type=float, required=True, help="Unprotected A-weighted level")
    protect.add_argument("--nrr", type=float)
    protect.add_argument("--nrr2", type=float, help="Second protector NRR for dual protection")
    protect.add_argument("--type", default="foam", choices=("foam", "earmuff", "muff", "other", "plug"))
    protect.add_argument("--method", choices=("osha", "osha50", "niosh", "snr", "hml"), default="osha")
    protect.add_argument("--safety-factor", action="store_true", help="Apply OSHA 50%% attenuation variant")
    for field in ("snr", "lc", "h", "m", "l"):
        protect.add_argument("--" + field, type=float)
    commands.add_parser("standards", help="List settings and exposure criteria")
    return parser


def _required(args: argparse.Namespace, *names: str) -> None:
    for name in names:
        if getattr(args, name) is None:
            raise InputError("--" + name + " is required for " + args.method)


def _run(args: argparse.Namespace) -> int:
    if args.command == "standards":
        print("Preset       Lc dBA   Q dB   Threshold dBA   Criterion h")
        for key, standard in STANDARDS.items():
            print("%-12s %6g %6g %15s %13g" % (key, standard.criterion_level, standard.exchange_rate,
                  "none" if standard.threshold is None else "%g" % standard.threshold, standard.criterion_hours))
        print("OSHA HC action: 50% dose / 85 dBA TWA; PEL: 100% / 90 dBA.")
        print("NIOSH REL / ACGIH TLV: 100% / 85 dBA (guidance criteria).")
        print("EU LEX,8h: lower action 80, upper action 85, limit 87 dBA (with protection).")
        print("EU LCpeak: lower action 135, upper action 137, limit 140 dBC.")
        print("EU dose is an unthresholded energy index, not a legal dose limit.")
        return 0
    if args.command == "allowed":
        # Segment validates the same range as the assessment input layer.
        Segment("level", 1, args.level)
        hours = time_until_100(args.level, args.current_dose, args.standard)
        if math.isinf(hours):
            print("Below integration threshold: no counted dose (not unlimited safe exposure).")
        else:
            print("%s: %.4f h (%.2f min) until 100%% dose at %.1f dBA" % (args.standard, hours, hours * 60, args.level))
        return 0
    if args.command == "calc":
        task = Segment("Constant exposure", args.hours, args.level)
        report = build_report([task], [args.standard])
        print(console_table(report))
        for warning in report["warnings"]:
            print("Note: " + warning)
        return report["exit_code"]
    if args.command == "protect":
        Segment("Unprotected level", 1, args.twa)
        if args.method in ("osha", "osha50", "niosh"):
            _required(args, "nrr")
            nrr = dual_nrr(args.nrr, args.nrr2) if args.nrr2 is not None else args.nrr
            if args.method == "niosh":
                protected = niosh_exposure(args.twa, nrr, args.type)
            else:
                protected = osha_exposure(args.twa, nrr, args.safety_factor or args.method == "osha50")
        elif args.method == "snr":
            _required(args, "lc", "snr")
            protected = snr_exposure(args.lc, args.snr)
        else:
            _required(args, "lc", "h", "m", "l")
            protected = hml_exposure(args.twa, args.lc, args.h, args.m, args.l)
        print("Estimated protected level: %.1f dBA (%s)" % (protected, protection_rating(protected)))
        print("Rating-based estimate; verify individual fit and correct continuous use.")
        if args.method == "hml":
            print("HML uses supplied TWA as an estimate of LA; LC must represent the same period, not LCpeak.")
        if args.method == "niosh":
            print("Historical NIOSH 1998 derating; individual quantitative fit testing is recommended by current NIOSH guidance.")
        return 0
    standards = [key.strip() for key in args.standards.split(",")]
    if len(set(standards)) != len(standards):
        raise InputError("standards must not contain duplicates")
    for key in standards:
        get_standard(key)
    if args.command == "log":
        segments = load_log(args.file, interval_seconds=args.interval_seconds,
                            level_column=args.level_column, peak_column=args.peak_column)
    else:
        segments = load_tasks(args.file)
    report = build_report(segments, standards, shift_hours=args.shift_hours, worker=args.worker,
                          area=args.area, source=str(args.file), task_based=args.command == "tasks",
                          instrument_class=args.instrument_class, protectors=args.protector, lc=args.lc)
    outputs = [(args.html, to_html), (args.json, to_json), (args.md, to_markdown)]
    targets = [path.resolve() for path, _ in outputs if path is not None]
    if len(set(targets)) != len(targets) or args.file.resolve() in targets:
        raise InputError("report paths must differ from each other and the input file")
    for path, render in outputs:
        if path is not None:
            path.write_text(render(report), encoding="utf-8", newline="\n")
    print(console_table(report))
    if report["uncertainty"]:
        u = report["uncertainty"]
        print(
            "Simplified task uncertainty: u=%.2f dB; U=%.2f dB "
            "(k=1.65, one-sided ~95%%; %s sampling budget)"
            % (u["combined_standard_db"], u["expanded_db"],
               "complete" if u["complete_sampling"] else "partial")
        )
    for warning in report["warnings"]:
        print("Note: " + warning)
    return report["exit_code"]


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Execute a command; return 0 below action, 1 action, 2 over limit, 3 error.

    Help/version exit normally through argparse. Assessment codes use actual
    exposure and are the maximum across selected criteria.
    """
    try:
        return _run(_parser().parse_args(argv))
    except (ValueError, OSError, OverflowError) as error:
        print("noisedose: error: " + str(error), file=sys.stderr)
        return 3
