"""
Black-box regression tests for both compiled rating engines.

Tests run against pre-built binaries — no network or API calls.
The naive engine is the correctness baseline; differential tests
verify that the FFT engine produces the same results.
"""

import math
import subprocess

import pytest

from conftest import run_engine, run_engine_raw, PROJECT_ROOT


# ── Helpers ───────────────────────────────────────────────────────────────────

def _elo_prob(r_a: int, r_b: int) -> float:
    """P(a beats b) in the CF Elo model."""
    return 1.0 / (1.0 + 10.0 ** ((r_b - r_a) / 400.0))


# ── Test 1: Output shape ───────────────────────────────────────────────────────

def test_output_shape(engine: str) -> None:
    participants = [(1500, 1), (1400, 2), (1300, 3), (1200, 4)]
    rows = run_engine(engine, participants)
    assert len(rows) == 4
    for row in rows:
        assert all(k in row for k in ("seed", "perf", "raw_delta", "adj_delta",
                                      "final_delta", "new_rating"))
        assert row["new_rating"] == pytest.approx(
            participants[rows.index(row)][0] + row["final_delta"], abs=1
        )


# ── Test 2: Equal-rating symmetry ─────────────────────────────────────────────

def test_equal_rating_seed(engine: str) -> None:
    """All equal-rated participants must have seed = 2.5 (n=4)."""
    rows = run_engine(engine, [(1500, i + 1) for i in range(4)])
    for row in rows:
        assert row["seed"] == pytest.approx(2.5, abs=1e-4)


# ── Test 3: Two-player expected seed ──────────────────────────────────────────

def test_two_player_seed(engine: str) -> None:
    """
    2-player contest: player A=1600, player B=1400.
    Expected seed_A = 1 + P(B beats A) = 1 + _elo_prob(1400, 1600).
    Expected seed_B = 1 + P(A beats B) = 1 + _elo_prob(1600, 1400).
    """
    rows = run_engine(engine, [(1600, 1), (1400, 2)])
    expected_seed_a = 1.0 + _elo_prob(1400, 1600)
    expected_seed_b = 1.0 + _elo_prob(1600, 1400)
    assert rows[0]["seed"] == pytest.approx(expected_seed_a, abs=1e-5)
    assert rows[1]["seed"] == pytest.approx(expected_seed_b, abs=1e-5)


# ── Test 4: Tied ranks ─────────────────────────────────────────────────────────

def test_tied_ranks(engine: str) -> None:
    """Tied ranks must not crash and must produce consistent output."""
    participants = [(1500, 1), (1500, 1), (1400, 3), (1400, 3)]
    rows = run_engine(engine, participants)
    assert len(rows) == 4
    # Tied participants at positions 0–1 should have same seed and final_delta
    assert rows[0]["seed"]        == pytest.approx(rows[1]["seed"],        abs=1e-4)
    assert rows[0]["final_delta"] == rows[1]["final_delta"]
    assert rows[2]["seed"]        == pytest.approx(rows[3]["seed"],        abs=1e-4)
    assert rows[2]["final_delta"] == rows[3]["final_delta"]


# ── Test 5: Determinism ────────────────────────────────────────────────────────

def test_determinism(engine: str) -> None:
    """Identical input must produce identical rating output across two runs."""
    participants = [(1800, 1), (1600, 2), (1400, 3), (1200, 4), (1000, 5)]
    rows_a = run_engine(engine, participants)
    rows_b = run_engine(engine, participants)
    for a, b in zip(rows_a, rows_b):
        assert a["final_delta"] == b["final_delta"]
        assert a["new_rating"]  == b["new_rating"]


# ── Test 6: Invalid input → non-zero exit ─────────────────────────────────────

@pytest.mark.parametrize("bad_input", [
    "",               # empty
    "0\n",            # non-positive n
    "-1\n",           # negative n
    "2\n1500",        # truncated
    "2\nabc 1\n",     # bad rating
])
def test_invalid_input_nonzero_exit(engine: str, bad_input: str) -> None:
    result = run_engine_raw(engine, bad_input)
    assert result.returncode != 0


# ── Test 7: new_rating consistency ────────────────────────────────────────────

def test_new_rating_equals_old_plus_delta(engine: str) -> None:
    """new_rating must equal old_rating + final_delta for every participant."""
    participants = [(2000, 1), (1800, 2), (1600, 3), (1400, 4), (1200, 5)]
    rows = run_engine(engine, participants)
    for i, (row, (old, _)) in enumerate(zip(rows, participants)):
        assert row["new_rating"] == old + row["final_delta"], f"row {i}"


# ── Differential: naive vs FFT ────────────────────────────────────────────────

SYNTH_CONTESTS = [
    # (description, [(rating, rank), ...])
    ("two_equal",    [(1500, 1), (1500, 2)]),
    ("two_spread",   [(2000, 1), (1000, 2)]),
    ("small_n10",    [(1800 - i * 50, i + 1) for i in range(10)]),
    ("n50_uniform",  [(int(500 + 3500 * i / 49), i + 1) for i in range(50)]),
    ("n50_cluster",  [(1400 + (i % 5) * 20, i + 1) for i in range(50)]),
    ("tied_ranks",   [(1500, 1), (1500, 1), (1400, 3), (1300, 4), (1300, 4)]),
    ("bimodal",      [(800 + i * 10, i + 1) for i in range(25)]
                   + [(2000 + i * 10, i + 26) for i in range(25)]),
]


@pytest.mark.parametrize("description,participants", SYNTH_CONTESTS,
                          ids=[c[0] for c in SYNTH_CONTESTS])
def test_fft_matches_naive(description: str, participants: list[tuple[int, int]]) -> None:
    """FFT final deltas must match naive within 1 point for all participants."""
    naive_rows = run_engine("naive", participants)
    fft_rows   = run_engine("fft",   participants)
    assert len(naive_rows) == len(fft_rows)
    max_diff = 0
    for i, (n, f) in enumerate(zip(naive_rows, fft_rows)):
        diff = abs(n["final_delta"] - f["final_delta"])
        max_diff = max(max_diff, diff)
        assert diff <= 1, (
            f"[{description}] row {i}: naive={n['final_delta']}, fft={f['final_delta']}"
        )
    # Seeds should agree to floating-point tolerance
    for i, (n, f) in enumerate(zip(naive_rows, fft_rows)):
        assert abs(n["seed"] - f["seed"]) < 1e-4, (
            f"[{description}] row {i} seed: naive={n['seed']:.6f}, fft={f['seed']:.6f}"
        )
