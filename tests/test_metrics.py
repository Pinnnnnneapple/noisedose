"""Independent arithmetic checks for exposure and uncertainty calculations."""
import math

import pytest

from noisedose.metrics import (Standard, allowed_time, assess, dose, dose_from_twa,
                               get_standard, leq, lex8, peak_evaluation,
                               task_uncertainty, time_until_100, twa_from_dose, weekly_lex)
from noisedose.models import Segment


@pytest.mark.parametrize("standard,level,hours,expected", [
    ("osha-pel", 90, 8, 100), ("osha-pel", 95, 4, 100),
    ("osha-pel", 100, 2, 100), ("osha-hc", 85, 8, 50),
    ("osha-hc", 79.9, 8, 0), ("osha-hc", 80, 8, 25),
    ("osha-pel", 89.9, 8, 0), ("niosh-rel", 85, 8, 100),
    ("niosh-rel", 88, 4, 100), ("niosh-rel", 100, .25, 100),
    ("niosh-rel", 79.9, 8, 0), ("acgih-tlv", 85, 8, 100),
])
def test_dose_hand_calculation(standard, level, hours, expected):
    assert dose([Segment("task", hours, level)], standard) == pytest.approx(expected)


@pytest.mark.parametrize("standard,percent,expected", [
    ("osha-pel", 100, 90), ("osha-hc", 50, 85),
    ("osha-pel", 200, 95), ("niosh-rel", 200, 88.0102999566),
    ("niosh-rel", 100, 85),
])
def test_twa(standard, percent, expected):
    assert twa_from_dose(percent, standard) == pytest.approx(expected)


@pytest.mark.parametrize("standard", ["osha-pel", "osha-hc", "niosh-rel", "acgih-tlv", "eu"])
@pytest.mark.parametrize("percent", [0, .001, 50, 100, 200, 5000])
def test_twa_inverse(standard, percent):
    assert dose_from_twa(twa_from_dose(percent, standard), standard) == pytest.approx(percent)


def test_smallest_positive_dose_has_finite_twa():
    percent = 5e-324
    assert math.isfinite(twa_from_dose(percent))
    assert dose_from_twa(twa_from_dose(percent)) == percent


def test_q4_custom_and_criterion_duration():
    standard = Standard("custom", 88, 4, 70, criterion_hours=10)
    assert allowed_time(92, standard) == 5
    assert dose([Segment("work", 5, 92)], standard) == 100
    assert twa_from_dose(200, standard) == 92


def test_energy_average():
    assert leq([80, 90], [1, 1]) == pytest.approx(87.4036269)


@pytest.mark.parametrize("hours,level,expected", [(4, 90, 86.98970004), (10, 85, 85.96910013), (8, 90, 90)])
def test_daily_lex(hours, level, expected):
    assert lex8([Segment("work", hours, level)]) == pytest.approx(expected)


def test_task_combination():
    tasks = [Segment("a", 2, 90), Segment("b", 6, 80)]
    expected = 10 * math.log10((2 * 10 ** 9 + 6 * 10 ** 8) / 8)
    assert lex8(tasks) == pytest.approx(expected)


def test_weekly_normalization():
    assert weekly_lex([85] * 5) == pytest.approx(85)
    assert weekly_lex([85, None, None, None, None]) == pytest.approx(78.0102999566)
    assert weekly_lex([85] * 7) == pytest.approx(86.46128036)
    assert weekly_lex([None] * 5) == -math.inf


def test_allowed_and_remaining():
    assert allowed_time(100, "niosh-rel") == .25
    assert time_until_100(100, 50, "niosh-rel") == .125
    assert time_until_100(100, 101, "niosh-rel") == 0
    assert math.isinf(allowed_time(79, "osha-hc"))


def test_projection_and_extended_shift():
    row = assess([Segment("work", 10, 90)], ["osha-pel"], 12)[0]
    assert row["dose_percent"] == 125
    assert row["projected_8h_dose_percent"] == 100
    assert row["projected_shift_dose_percent"] == 150
    assert row["twa_db"] > 90
    assert row["projected_8h_twa_db"] == 90


def test_partial_record_status_is_not_projection():
    row = assess([Segment("work", 1, 90)], ["osha-pel"], 12)[0]
    assert row["exit_code"] == 0
    assert row["projected_shift_dose_percent"] == 150


def test_osha_action_uses_separate_hc_threshold():
    row = assess([Segment("work", 8, 85)], ["osha-pel"])[0]
    assert row["dose_percent"] == 0
    assert row["twa_db"] is None
    assert row["exit_code"] == 1


@pytest.mark.parametrize("level,code", [(79.99, 0), (80, 1), (85, 1), (87, 1), (87.01, 2)])
def test_eu_action_boundaries(level, code):
    assert assess([Segment("x", 8, level)], ["eu"])[0]["exit_code"] == code


@pytest.mark.parametrize("peak,code", [(None, 0), (134.9, 0), (135, 1), (137, 1), (140, 1), (140.1, 2)])
def test_peak_boundaries(peak, code):
    assert peak_evaluation(peak)["exit_code"] == code


def test_peak_can_dominate_quiet_daily_exposure():
    assert assess([Segment("work", 8, 50, 141)], ["eu"])[0]["exit_code"] == 2


def test_uncertainty_hand_calculation():
    task = Segment("work", 8, 90, samples=(89, 90, 91), duration_uncertainty_hours=.5)
    u = task_uncertainty([task], 1)
    expected = math.sqrt(1 / 3 + (10 / math.log(10) * .5 / 8) ** 2 + .7 ** 2 + 1)
    assert u["combined_standard_db"] == pytest.approx(expected)
    assert u["expanded_db"] == pytest.approx(1.65 * expected)
    assert u["upper_95_db"] == pytest.approx(90 + 1.65 * expected)
    assert u["complete_sampling"]


def test_shared_instrument_uncertainty_does_not_average_down():
    tasks = [Segment(str(i), 1, 85, samples=(85, 85, 85)) for i in range(8)]
    assert task_uncertainty(tasks, 2)["combined_standard_db"] == pytest.approx(math.sqrt(1.5 ** 2 + 1))


def test_missing_sampling_is_partial():
    result = task_uncertainty([Segment("work", 8, 90)])
    assert not result["complete_sampling"]
    assert result["tasks"][0]["sampling_standard_db"] is None


@pytest.mark.parametrize("fn,args", [
    (leq, ([], [])), (leq, ([80], [0])), (leq, ([80], [-1])),
    (leq, ([80, 90], [1])), (leq, ([math.nan], [1])),
    (twa_from_dose, (-1,)), (twa_from_dose, (math.inf,)),
    (allowed_time, (math.nan,)), (time_until_100, (90, -1)),
    (weekly_lex, ([],)), (weekly_lex, ([85] * 8,)),
    (task_uncertainty, ([],)), (task_uncertainty, ([Segment("x", 8, 90)], 3)),
    (get_standard, ("unknown",)), (assess, ([],)),
    (assess, ([Segment("x", 8, 90)], ["eu"], -1)),
    (Standard, ("bad", 90, 0, 80)), (Standard, ("bad", 90, 5, math.nan)),
])
def test_invalid_calculations(fn, args):
    with pytest.raises(ValueError):
        fn(*args)
