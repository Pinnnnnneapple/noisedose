"""Screening estimates of hearing-protector attenuation, in decibels.

NRR, SNR and H/M/L are laboratory ratings, not assurances of field fit or
individual protection. Generic ratings are illustrative, not product data.
These estimates do not model leakage, poor fit, impulse noise or peak levels.
SNR/HML require a representative C-weighted level (LC), never LCpeak. For HML,
``analyze_protector`` uses the supplied A-weighted TWA as an estimate of LA;
LA and LC should describe the same exposure period. NRR and HML reductions are
floored at zero. The SNR calculation retains LC-SNR even when it exceeds input LA; that
case establishes no positive attenuation. The qualitative rating is a screening
category, not a compliance decision.
"""

from __future__ import annotations

import math
from numbers import Real
from typing import Any, Dict, Optional


GENERIC_PROTECTORS: Dict[str, Dict[str, Any]] = {
    "foam": {"name": "Generic foam", "nrr": 29.0, "snr": 34.0},
    "earmuff": {"name": "Generic earmuff", "nrr": 25.0, "snr": 30.0},
}
"""Illustrative laboratory ratings; these do not identify tested products."""

_RETAINED = {
    "foam": 0.5,
    "formable foam": 0.5,
    "earmuff": 0.75,
    "muff": 0.75,
    "other": 0.3,
    "plug": 0.3,
}
_METHODS = {"osha", "osha50", "niosh", "snr", "hml"}
_RATINGS = {"nrr", "snr", "h", "m", "l"}


def _finite(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite number")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number")
    return number


def _rating(value: float, name: str) -> float:
    number = _finite(value, name)
    if not 0 <= number <= 100:
        raise ValueError(f"{name} must be between 0 and 100 dB")
    return number


def _text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")
    return " ".join(value.lower().split())


def osha_exposure(twa: float, nrr: float, safety_factor: bool = False) -> float:
    """Return TWA - max(0, NRR - 7), optionally halving that attenuation.

    ``safety_factor=True`` applies the OSHA 50% attenuation adjustment after
    the 7 dB A-weighting correction. This is not an individual fit guarantee.
    Nominal ratings must be finite and within the sanity range 0–100 dB.
    """
    level = _finite(twa, "twa")
    rating = _rating(nrr, "nrr")
    if not isinstance(safety_factor, bool):
        raise ValueError("safety_factor must be a bool")
    attenuation = max(0.0, rating - 7.0)
    if safety_factor:
        attenuation *= 0.5
    return level - attenuation


def niosh_exposure(twa: float, nrr: float, protector_type: str = "foam") -> float:
    """Return TWA minus max(0, retained NRR - 7) for A-weighted exposure.

    Foam/formable foam retains 50%, earmuff/muff 75%, and other/plug 30%.
    The 7 dB correction follows derating. Ratings must be in 0–100 dB.
    """
    level = _finite(twa, "twa")
    rating = _rating(nrr, "nrr")
    kind = _text(protector_type, "protector_type")
    if kind not in _RETAINED:
        raise ValueError(f"unsupported NIOSH protector_type: {protector_type!r}")
    return level - max(0.0, rating * _RETAINED[kind] - 7.0)


def dual_nrr(nrr1: float, nrr2: float) -> float:
    """Estimate combined NRR as max(NRR1, NRR2) + 5, without adding ratings.

    Each nominal rating must be in 0–100 dB. The rule estimates combined
    laboratory-rated protection; simultaneous use does not assure field fit.
    """
    return max(_rating(nrr1, "nrr1"), _rating(nrr2, "nrr2")) + 5.0


def snr_exposure(lc: float, snr: float) -> float:
    """Estimate protected A-weighted level as LC - SNR (0–100 dB rating).

    LC must be a representative C-weighted exposure level, not LCpeak.
    """
    return _finite(lc, "lc") - _rating(snr, "snr")


def hml_pnr(h: float, m: float, l: float, lc_minus_la: float) -> float:
    """Return HML predicted noise reduction, floored at zero.

    For delta = LC - LA <= 2, use M - (H-M)/4 * (delta-2); otherwise use
    M - (M-L)/8 * (delta-2). H, M and L must be finite 0–100 dB ratings.
    No spectral ordering is imposed on H/M/L. Extrapolation is approximate.
    """
    high, middle, low = _rating(h, "h"), _rating(m, "m"), _rating(l, "l")
    delta = _finite(lc_minus_la, "lc_minus_la")
    if delta <= 2.0:
        reduction = middle - (high - middle) / 4.0 * (delta - 2.0)
    else:
        reduction = middle - (middle - low) / 8.0 * (delta - 2.0)
    return max(0.0, _finite(reduction, "calculated HML reduction"))


def hml_exposure(la: float, lc: float, h: float, m: float, l: float) -> float:
    """Return LA minus HML reduction using representative, matched LA/LC.

    LCpeak cannot substitute for LC. Ratings must be in 0–100 dB.
    """
    a_level, c_level = _finite(la, "la"), _finite(lc, "lc")
    return _finite(a_level - hml_pnr(h, m, l, c_level - a_level),
                   "protected level")


def protection_rating(protected_level: float) -> str:
    """Classify a finite protected level with inclusive good range 70–75 dB.

    Below 65: too much attenuation; 65–<70 and >75–80: acceptable;
    70–75: good; above 80: insufficient. Categories do not assure field fit.
    """
    level = _finite(protected_level, "protected_level")
    if level < 65.0:
        return "too much attenuation"
    if level < 70.0:
        return "acceptable"
    if level <= 75.0:
        return "good"
    if level <= 80.0:
        return "acceptable"
    return "insufficient"


def parse_protector(spec: str) -> Dict[str, Any]:
    """Parse ``kind:key=value,key=value``; the default method is ``osha50``.

    Methods: osha, osha50, niosh, snr, hml. Allowed ratings: nrr, snr, h, m,
    l (finite 0–100 dB). NRR methods require nrr; SNR requires snr; HML
    requires h/m/l. Bare foam/earmuff names (or method-only specifications)
    use illustrative generic ratings. Explicit ratings replace those defaults
    as a group, so a custom NRR never silently acquires a generic SNR/HML.
    Unknown labels are allowed with explicit ratings, except for NIOSH,
    which requires a recognized protector type. Duplicate/unknown keys fail.
    """
    if not isinstance(spec, str) or not spec.strip():
        raise ValueError("spec must be a nonempty string")
    raw_kind, separator, parameters = spec.partition(":")
    kind = _text(raw_kind, "kind")
    parsed: Dict[str, Any] = {"kind": kind, "method": "osha50"}
    seen = set()
    if separator:
        for parameter in parameters.split(","):
            key, equals, raw_value = parameter.partition("=")
            key = key.strip().lower()
            if not equals or not raw_value.strip():
                raise ValueError("protector parameters must be key=value pairs")
            if key not in _RATINGS | {"method"}:
                raise ValueError(f"unknown protector parameter: {key!r}")
            if key in seen:
                raise ValueError(f"duplicate protector parameter: {key!r}")
            seen.add(key)
            if key == "method":
                parsed[key] = _text(raw_value, "method")
            else:
                try:
                    number = float(raw_value)
                except ValueError as exc:
                    raise ValueError(f"{key} must be a finite numeric rating") from exc
                parsed[key] = _rating(number, key)
    if not seen.intersection(_RATINGS):
        generic_kind = {"formable foam": "foam", "muff": "earmuff"}.get(kind, kind)
        generic = GENERIC_PROTECTORS.get(generic_kind, {})
        parsed.update({key: generic[key] for key in _RATINGS if key in generic})
    method = parsed["method"]
    if method not in _METHODS:
        raise ValueError(f"unsupported protector method: {method!r}")
    required = {"snr"} if method == "snr" else {"h", "m", "l"} if method == "hml" else {"nrr"}
    missing = required.difference(parsed)
    if missing:
        raise ValueError(f"{method} requires ratings: {', '.join(sorted(missing))}")
    if method == "niosh" and kind not in _RETAINED:
        raise ValueError(f"unsupported NIOSH protector_type: {kind!r}")
    return parsed


def analyze_protector(twa: float, spec: str, lc: Optional[float] = None) -> Dict[str, Any]:
    """Return name, method, attenuation_db, protected_level_db, rating, assumptions.

    Attenuation is the nonnegative difference from A-weighted TWA. If an SNR
    estimate LC-SNR exceeds TWA, retain that conservative estimate and credit
    zero attenuation, with a note. HML uses TWA as an LA estimate and labels
    that assumption. SNR/HML require measured representative LC, not LCpeak.
    The assumptions value is a list of strings; results are JSON-compatible.
    """
    level = _finite(twa, "twa")
    c_level = None if lc is None else _finite(lc, "lc")
    parameters = parse_protector(spec)
    method = parameters["method"]
    assumptions = [
        "Laboratory ratings estimate attenuation; individual field fit and protection are not assured.",
        "Attenuation is floored at zero; impulse noise and peak protection are not assessed.",
    ]
    # Reparse the parameter keys to distinguish explicit ratings from examples.
    supplied = spec.partition(":")[2]
    explicit_ratings = any(part.partition("=")[0].strip().lower() in _RATINGS
                           for part in supplied.split(","))
    if not explicit_ratings:
        assumptions.append("Generic ratings are illustrative examples, not product-specific data.")
    if method in {"snr", "hml"}:
        if c_level is None:
            raise ValueError(f"{method} requires representative C-weighted lc; LCpeak is not LC")
        assumptions.append("LC is a representative C-weighted exposure level for the same period, not LCpeak.")
    if method in {"osha", "osha50"}:
        estimate = osha_exposure(level, parameters["nrr"], method == "osha50")
        assumptions.append("NRR minus 7 dB for A weighting" +
                           (", then 50% attenuation retained." if method == "osha50" else "."))
    elif method == "niosh":
        estimate = niosh_exposure(level, parameters["nrr"], parameters["kind"])
        assumptions.append("Historical NIOSH 1998 derating; current NIOSH guidance recommends individual quantitative fit testing.")
        assumptions.append(f"Retain {_RETAINED[parameters['kind']]:.0%} of NRR, then subtract 7 dB for A weighting.")
    elif method == "snr":
        estimate = snr_exposure(c_level, parameters["snr"])
        assumptions.append("Protected A-weighted level estimated as LC minus SNR; attenuation referenced to TWA.")
    else:
        estimate = hml_exposure(level, c_level, parameters["h"], parameters["m"], parameters["l"])
        assumptions.append("HML uses A-weighted TWA as an estimate of LA; matched LA and LC periods are assumed.")
        assumptions.append("The HML interpolation formula is used; spectral extrapolation is approximate.")
    protected = _finite(estimate, "protected level")
    if protected > level:
        assumptions.append("SNR estimate exceeds input LA; no positive attenuation is established. Review spectral suitability and matched measurements.")
    attenuation = _finite(max(0.0, level - protected), "attenuation")
    return {
        "name": parameters["kind"],
        "method": method,
        "attenuation_db": attenuation,
        "protected_level_db": protected,
        "rating": protection_rating(protected),
        "assumptions": assumptions,
    }
