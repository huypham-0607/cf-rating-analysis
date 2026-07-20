"""
Shared fixtures for the test suite.

All tests invoke the compiled binaries directly — no network access required.
"""

import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
BINARY_DIR   = PROJECT_ROOT / "cpp" / "build"


def _run_engine(engine: str, input_text: str) -> subprocess.CompletedProcess:
    binary = BINARY_DIR / engine
    return subprocess.run(
        [str(binary)],
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


def run_engine(engine: str, participants: list[tuple[int, int]]) -> list[dict]:
    """
    Run engine on (rating, rank) pairs and return parsed output rows.

    Each returned dict has keys: seed, perf, raw_delta, adj_delta, final_delta, new_rating.
    """
    lines = [str(len(participants))]
    for rating, rank in participants:
        lines.append(f"{rating} {rank}")
    result = _run_engine(engine, "\n".join(lines))
    assert result.returncode == 0, f"{engine} failed:\n{result.stderr}"
    rows = []
    for line in result.stdout.strip().split("\n"):
        parts = line.split()
        assert len(parts) == 6, f"Expected 6 fields, got: {line!r}"
        rows.append({
            "seed":        float(parts[0]),
            "perf":        int(parts[1]),
            "raw_delta":   float(parts[2]),
            "adj_delta":   float(parts[3]),
            "final_delta": int(parts[4]),
            "new_rating":  int(parts[5]),
        })
    return rows


def run_engine_raw(engine: str, input_text: str) -> subprocess.CompletedProcess:
    return _run_engine(engine, input_text)


@pytest.fixture(params=["naive", "fft"])
def engine(request: pytest.FixtureRequest) -> str:
    return request.param
