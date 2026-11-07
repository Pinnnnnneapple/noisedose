"""Protector formulas, parser contracts, validation and reporting safeguards."""

import json
import math

import pytest

from noisedose.protectors import (
    GENERIC_PROTECTORS,
    analyze_protector,
    dual_nrr,
    hml_exposure,
    hml_pnr,
    niosh_exposure,
    osha_exposure,
    parse_protector,
    protection_rating,
    snr_exposure,
)


def test_osha_unadjusted():
    assert osha_exposure(100, 29) == 78


def test_osha_50_percent_follows_a_weighting():
    assert osha_exposure(100, 29, safety_factor=True) == 89


@pytest.mark.parametrize("nrr", [0, 3, 7])
@pytest.mark.parametrize("safety_factor", [False, True])
def test_osha_low_nrr_never_amplifies(nrr, safety_factor):
    assert osha_exposure(90, nrr, safety_factor) == 90


@pytest.mark.parametrize("kind, expected", [
    ("foam", 92.5), ("formable foam", 92.5),
    ("earmuff", 85.25), ("muff", 85.25),
    ("other", 98.3), ("plug", 98.3),
])
def test_niosh_retention_then_a_weighting(kind, expected):
    assert niosh_exposure(100, 29, kind) == pytest.approx(expected)


def test_niosh_default_is_foam():
    assert niosh_exposure(100, 29) == 92.5


@pytest.mark.parametrize("kind", ["foam", "muff", "plug"])
def test_niosh_low_rating_does_not_manufacture_attenuation(kind):
    assert niosh_exposure(90, 5, kind) == 90


def test_niosh_unknown_type_is_an_error():
    with pytest.raises(ValueError, match="protector_type"):
        niosh_exposure(90, 29, "unknown")


def test_niosh_type_normalizes_case_and_whitespace():
    assert niosh_exposure(100, 29, " Formable  FOAM ") == 92.5


@pytest.mark.parametrize("first, second, expected", [(29, 25, 34), (25, 29, 34), (20, 20, 25), (0, 0, 5)])
def test_dual_nrr_uses_max_plus_five(first, second, expected):
    assert dual_nrr(first, second) == expected


def test_snr_uses_c_weighted_level_without_nrr_correction():
    assert snr_exposure(102, 30) == 72


@pytest.mark.parametrize("delta, expected", [(-2, 36), (0, 32), (2, 28), (6, 24), (10, 20)])
def test_hml_equations_on_both_branches(delta, expected):
    assert hml_pnr(36, 28, 20, delta) == expected


def test_hml_is_continuous_at_branch_boundary():
    assert hml_pnr(36, 28, 20, 2 - 1e-8) == pytest.approx(28)
    assert hml_pnr(36, 28, 20, 2 + 1e-8) == pytest.approx(28)


def test_hml_negative_reduction_is_floored():
    assert hml_pnr(30, 20, 0, 20) == 0
    assert hml_exposure(80, 100, 30, 20, 0) == 80


def test_hml_does_not_require_rating_order():
    assert hml_pnr(20, 25, 30, 10) == 30


def test_hml_exposure_uses_lc_minus_la():
    assert hml_exposure(100, 106, 36, 28, 20) == 76


@pytest.mark.parametrize("level, rating", [
    (64.9999, "too much attenuation"), (65, "acceptable"),
    (69.9999, "acceptable"), (70, "good"), (75, "good"),
    (75.0001, "acceptable"), (80, "acceptable"), (80.0001, "insufficient"),
])
def test_protection_rating_boundaries(level, rating):
    assert protection_rating(level) == rating


def test_generic_labels_and_ratings():
    assert GENERIC_PROTECTORS["foam"] == {"name": "Generic foam", "nrr": 29, "snr": 34}
    assert GENERIC_PROTECTORS["earmuff"] == {"name": "Generic earmuff", "nrr": 25, "snr": 30}


def test_parse_cli_example_and_default():
    assert parse_protector("foam:nrr=29") == {"kind": "foam", "nrr": 29.0, "method": "osha50"}


@pytest.mark.parametrize("method", ["osha", "osha50", "niosh"])
def test_parse_nrr_method_override(method):
    assert parse_protector(f"foam:nrr=29,method={method}")["method"] == method


def test_parse_case_whitespace_and_decimal():
    assert parse_protector(" FOAM : NRR = 29.5, METHOD = OSHA ") == {
        "kind": "foam", "nrr": 29.5, "method": "osha",
    }


def test_parse_bare_generic_uses_examples_and_returns_fresh_mapping():
    parsed = parse_protector("foam")
    assert parsed == {"kind": "foam", "nrr": 29.0, "snr": 34.0, "method": "osha50"}
    parsed["nrr"] = 1
    assert parse_protector("foam")["nrr"] == 29


def test_parse_generic_method_only_and_alias():
    assert parse_protector("muff:method=snr")["snr"] == 30


def test_parse_snr_does_not_require_unused_nrr():
    assert parse_protector("custom:snr=30,method=snr") == {
        "kind": "custom", "snr": 30.0, "method": "snr",
    }


def test_parse_hml_requires_only_hml_ratings():
    parsed = parse_protector("custom:h=36,m=28,l=20,method=hml")
    assert (parsed["h"], parsed["m"], parsed["l"], parsed["method"]) == (36, 28, 20, "hml")


@pytest.mark.parametrize("spec", [
    "", " ", ":nrr=29", "foam:", "foam:nrr", "foam:nrr=", "foam:nrr=29,",
    "foam:nrr=29,nrr=25", "foam:nrr=29,NRR=25", "foam:nrr=29,extra=1",
    "foam:nrr=29,method=osha,method=osha50", "foam:nrr=29,method=unknown",
    "foam:nrr=abc", "foam:nrr=nan", "foam:nrr=inf", "foam:nrr=-1", "foam:nrr=101",
    "unknown", "custom:method=osha", "foam:snr=30", "foam:nrr=29,method=snr",
    "foam:nrr=29,h=30,m=20,method=hml", "custom:nrr=29,method=niosh",
    "foam:snr=-1,method=snr", "foam:h=30,m=20,l=nan,method=hml",
])
def test_parse_rejects_malformed_or_incomplete_specifications(spec):
    with pytest.raises(ValueError):
        parse_protector(spec)


def test_analysis_osha50_schema_numbers_and_json():
    result = analyze_protector(90, "foam:nrr=29")
    assert set(result) == {"name", "method", "attenuation_db", "protected_level_db", "rating", "assumptions"}
    assert result["name"] == "foam"
    assert result["method"] == "osha50"
    assert result["attenuation_db"] == 11
    assert result["protected_level_db"] == 79
    assert result["rating"] == "acceptable"
    assert json.loads(json.dumps(result, allow_nan=False)) == result


def test_analysis_osha_without_safety_factor():
    result = analyze_protector(90, "foam:nrr=29,method=osha")
    assert result["attenuation_db"] == 22
    assert result["protected_level_db"] == 68


def test_analysis_niosh_type_is_used():
    result = analyze_protector(100, "earmuff:nrr=28,method=niosh")
    assert result["attenuation_db"] == 14
    assert result["protected_level_db"] == 86
    assert any("75%" in assumption for assumption in result["assumptions"])


def test_analysis_snr_attenuation_is_referenced_to_twa():
    result = analyze_protector(100, "foam:snr=34,method=snr", lc=104)
    assert result["protected_level_db"] == 70
    assert result["attenuation_db"] == 30
    assert result["rating"] == "good"


def test_analysis_snr_cannot_manufacture_attenuation_when_lc_is_high():
    result = analyze_protector(90, "custom:snr=5,method=snr", lc=100)
    assert result["protected_level_db"] == 95
    assert result["attenuation_db"] == 0
    assert any("SNR estimate exceeds input LA" in note for note in result["assumptions"])


def test_analysis_hml_labels_twa_as_la_estimate():
    result = analyze_protector(100, "custom:h=36,m=28,l=20,method=hml", lc=106)
    assert result["attenuation_db"] == 24
    assert result["protected_level_db"] == 76
    assert any("TWA as an estimate of LA" in note for note in result["assumptions"])


@pytest.mark.parametrize("spec", ["foam:method=snr", "custom:h=36,m=28,l=20,method=hml"])
def test_analysis_requires_lc_and_explains_peak_caveat(spec):
    with pytest.raises(ValueError, match="LCpeak is not LC"):
        analyze_protector(100, spec)


def test_analysis_rejects_lcpeak_keyword():
    with pytest.raises(TypeError):
        analyze_protector(100, "foam:method=snr", lcpeak=110)


def test_analysis_generic_assumptions_disclose_illustrative_ratings():
    result = analyze_protector(90, "foam")
    assert any("illustrative" in note for note in result["assumptions"])
    assert any("not assured" in note for note in result["assumptions"])
    explicit = analyze_protector(90, "foam:nrr=29")
    assert not any("illustrative" in note for note in explicit["assumptions"])


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, True, "90", None])
@pytest.mark.parametrize("operation", [
    lambda x: osha_exposure(x, 29), lambda x: niosh_exposure(x, 29),
    lambda x: snr_exposure(x, 30), lambda x: hml_exposure(x, 100, 30, 20, 10),
    lambda x: hml_exposure(90, x, 30, 20, 10), lambda x: hml_pnr(30, 20, 10, x),
    protection_rating, lambda x: analyze_protector(x, "foam"),
])
def test_nonfinite_and_nonnumeric_levels_are_rejected(bad, operation):
    with pytest.raises(ValueError):
        operation(bad)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, True, "100"])
def test_analysis_rejects_invalid_optional_lc_even_for_nrr_method(bad):
    with pytest.raises(ValueError, match="lc"):
        analyze_protector(90, "foam", lc=bad)


def test_analysis_zero_lc_is_supplied_and_not_treated_as_missing():
    result = analyze_protector(0, "custom:snr=0,method=snr", lc=0)
    assert result["attenuation_db"] == 0
    assert result["protected_level_db"] == 0


@pytest.mark.parametrize("bad", [None, True, 29])
def test_parse_rejects_nonstring_specifications(bad):
    with pytest.raises(ValueError, match="spec"):
        parse_protector(bad)


def test_explicit_snr_never_borrows_generic_nrr():
    with pytest.raises(ValueError, match="requires ratings: nrr"):
        parse_protector("foam:snr=34,method=osha50")


@pytest.mark.parametrize("bad", [-1, 101, math.nan, math.inf, -math.inf, True, "29", None])
@pytest.mark.parametrize("operation", [
    lambda x: osha_exposure(90, x), lambda x: niosh_exposure(90, x),
    lambda x: dual_nrr(x, 25), lambda x: dual_nrr(25, x),
    lambda x: snr_exposure(100, x), lambda x: hml_pnr(x, 20, 10, 2),
    lambda x: hml_pnr(30, x, 10, 2), lambda x: hml_pnr(30, 20, x, 2),
])
def test_invalid_ratings_are_rejected(bad, operation):
    with pytest.raises(ValueError):
        operation(bad)


def test_invalid_safety_flag_is_rejected():
    with pytest.raises(ValueError, match="safety_factor"):
        osha_exposure(90, 29, safety_factor="false")


def test_hml_overflow_cannot_escape_as_infinite_attenuation():
    with pytest.raises(ValueError, match="finite"):
        hml_pnr(100, 0, 0, -1e308)


def test_extreme_lc_la_difference_must_remain_finite():
    with pytest.raises(ValueError, match="finite"):
        hml_exposure(-1e308, 1e308, 30, 20, 10)
