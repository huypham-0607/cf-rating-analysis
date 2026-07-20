"""
Unit tests for the summarize_errors() metric function.

Uses a small known error vector to verify each statistic by hand.
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from validation.metrics import summarize_errors


ERRORS = [0, 1, -2, 3]   # known vector for hand-verification


def test_count() -> None:
    assert summarize_errors(ERRORS)["count"] == 4


def test_bias() -> None:
    # (0 + 1 - 2 + 3) / 4 = 0.5
    assert summarize_errors(ERRORS)["bias"] == pytest.approx(0.5, abs=1e-9)


def test_mae() -> None:
    # (0 + 1 + 2 + 3) / 4 = 1.5
    assert summarize_errors(ERRORS)["mae"] == pytest.approx(1.5, abs=1e-9)


def test_rmse() -> None:
    # sqrt((0 + 1 + 4 + 9) / 4) = sqrt(3.5)
    assert summarize_errors(ERRORS)["rmse"] == pytest.approx(math.sqrt(3.5), abs=1e-9)


def test_median_error() -> None:
    # sorted: [-2, 0, 1, 3] → median = (0+1)/2 = 0.5
    assert summarize_errors(ERRORS)["median_error"] == pytest.approx(0.5, abs=1e-9)


def test_median_absolute_error() -> None:
    # abs: [0, 1, 2, 3] → median = (1+2)/2 = 1.5
    assert summarize_errors(ERRORS)["median_absolute_error"] == pytest.approx(1.5, abs=1e-9)


def test_exact_rate() -> None:
    # 1 out of 4 exactly zero
    assert summarize_errors(ERRORS)["exact_rate"] == pytest.approx(0.25, abs=1e-9)


def test_within_one_rate() -> None:
    # |0|=0<=1, |1|=1<=1, |-2|=2>1, |3|=3>1 → 2/4=0.5
    assert summarize_errors(ERRORS)["within_one_rate"] == pytest.approx(0.5, abs=1e-9)


def test_within_five_rate() -> None:
    # all |e|<=5 → 1.0
    assert summarize_errors(ERRORS)["within_five_rate"] == pytest.approx(1.0, abs=1e-9)


def test_empty_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        summarize_errors([])


def test_all_zeros() -> None:
    s = summarize_errors([0, 0, 0])
    assert s["bias"]       == pytest.approx(0.0)
    assert s["mae"]        == pytest.approx(0.0)
    assert s["rmse"]       == pytest.approx(0.0)
    assert s["exact_rate"] == pytest.approx(1.0)


def test_single_value() -> None:
    s = summarize_errors([5])
    assert s["count"] == 1
    assert s["bias"]  == pytest.approx(5.0)
    assert s["mae"]   == pytest.approx(5.0)
