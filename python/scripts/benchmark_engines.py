"""
Benchmark naive vs FFT engine across participant counts and rating distributions.

Produces:
  results/benchmark.csv
  img/runtime_comparison.png
  img/speedup_comparison.png

Usage
-----
  uv run python python/scripts/benchmark_engines.py

Environment
-----------
  CPU: see /proc/cpuinfo
  Build: cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release && cmake --build cpp/build -j
  Engines are single-threaded; timing from engine's own stderr (wall clock).
"""

import json
import random
import statistics
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from utils import PROJECT_ROOT

BINARY_DIR = PROJECT_ROOT / "cpp" / "build"
RESULTS    = PROJECT_ROOT / "results"
IMG        = PROJECT_ROOT / "img"
RC_DIR     = PROJECT_ROOT / "data" / "final" / "rating_changes"

PARTICIPANT_COUNTS = [100, 250, 500, 1000, 2000, 4000]
N_RUNS    = 5
WARMUP    = 1
RAND_SEED = 42

# Real contests: small / medium / large / very-large
REAL_CONTESTS = [1000, 1300, 2000, 2050]


# ── Synthetic rating generators ───────────────────────────────────────────────

def _uniform(n: int, rng: random.Random) -> list[tuple[int, int]]:
    ratings = sorted([rng.randint(0, 4000) for _ in range(n)], reverse=True)
    return [(r, i + 1) for i, r in enumerate(ratings)]


def _clustered(n: int, rng: random.Random) -> list[tuple[int, int]]:
    ratings = sorted([max(0, min(4000, int(rng.gauss(1400, 300)))) for _ in range(n)],
                     reverse=True)
    return [(r, i + 1) for i, r in enumerate(ratings)]


def _bimodal(n: int, rng: random.Random) -> list[tuple[int, int]]:
    half = n // 2
    lo = [max(0, min(4000, int(rng.gauss(800,  200)))) for _ in range(half)]
    hi = [max(0, min(4000, int(rng.gauss(2200, 200)))) for _ in range(n - half)]
    ratings = sorted(lo + hi, reverse=True)
    return [(r, i + 1) for i, r in enumerate(ratings)]


DISTRIBUTIONS = {
    "uniform":   _uniform,
    "clustered": _clustered,
    "bimodal":   _bimodal,
}


# ── Engine runner ─────────────────────────────────────────────────────────────

def _run_engine(engine: str, participants: list[tuple[int, int]]) -> float:
    """Returns runtime in ms from engine stderr."""
    lines = [str(len(participants))]
    for rating, rank in participants:
        lines.append(f"{rating} {rank}")
    result = subprocess.run(
        [str(BINARY_DIR / engine)],
        input="\n".join(lines),
        text=True,
        capture_output=True,
        check=True,
    )
    return float(result.stderr.strip().split()[0])


def _median_runtime(engine: str, participants: list[tuple[int, int]]) -> float:
    """Warm up once, then take median of N_RUNS."""
    _run_engine(engine, participants)  # warm-up
    times = [_run_engine(engine, participants) for _ in range(N_RUNS)]
    return statistics.median(times)


def _delta_stats(participants: list[tuple[int, int]]) -> dict:
    """Compare final_delta between naive and fft, return difference stats."""
    def _parse_deltas(engine: str) -> list[int]:
        lines = [str(len(participants))]
        for r, k in participants:
            lines.append(f"{r} {k}")
        res = subprocess.run([str(BINARY_DIR / engine)], input="\n".join(lines),
                             text=True, capture_output=True, check=True)
        return [int(l.split()[4]) for l in res.stdout.strip().split("\n")]

    naive_d = _parse_deltas("naive")
    fft_d   = _parse_deltas("fft")
    diffs   = [abs(n - f) for n, f in zip(naive_d, fft_d)]
    exact   = sum(1 for d in diffs if d == 0) / len(diffs)
    return {
        "mean_abs_final_delta_diff": sum(diffs) / len(diffs),
        "max_abs_final_delta_diff":  max(diffs),
        "exact_final_delta_rate":    exact,
    }


# ── Benchmark groups ──────────────────────────────────────────────────────────

def benchmark_synthetic() -> list[dict]:
    rng = random.Random(RAND_SEED)
    rows = []
    for dist_name, dist_fn in DISTRIBUTIONS.items():
        print(f"\n  Distribution: {dist_name}")
        for n in PARTICIPANT_COUNTS:
            participants = dist_fn(n, rng)
            ratings = [r for r, _ in participants]
            naive_ms = _median_runtime("naive", participants)
            fft_ms   = _median_runtime("fft",   participants)
            diff     = _delta_stats(participants)
            row = {
                "source":        "synthetic",
                "distribution":  dist_name,
                "contest_id":    None,
                "n":             n,
                "rating_min":    min(ratings),
                "rating_max":    max(ratings),
                "rating_span":   max(ratings) - min(ratings),
                "naive_median_ms": round(naive_ms, 3),
                "fft_median_ms":   round(fft_ms,   3),
                "speedup":         round(naive_ms / fft_ms, 3) if fft_ms > 0 else None,
                **diff,
            }
            rows.append(row)
            print(f"    n={n:5d}  naive={naive_ms:7.1f}ms  fft={fft_ms:7.1f}ms  "
                  f"speedup={naive_ms/fft_ms:.2f}x  "
                  f"max_diff={diff['max_abs_final_delta_diff']}")
    return rows


def benchmark_real() -> list[dict]:
    rows = []
    print("\n  Real contests")
    for cid in REAL_CONTESTS:
        rc_path = RC_DIR / f"{cid}.json"
        if not rc_path.exists():
            print(f"    Contest {cid}: data missing, skipping")
            continue
        data = json.loads(rc_path.read_text())
        data.sort(key=lambda x: x["rank"])
        # Clamp ratings to engine's supported domain [0, 8000]
        participants = [(max(0, min(8000, r["trueOldRating"])), r["rank"]) for r in data]
        n = len(participants)
        ratings = [r for r, _ in participants]
        naive_ms = _median_runtime("naive", participants)
        fft_ms   = _median_runtime("fft",   participants)
        diff     = _delta_stats(participants)
        row = {
            "source":        "real",
            "distribution":  "historical",
            "contest_id":    cid,
            "n":             n,
            "rating_min":    min(ratings),
            "rating_max":    max(ratings),
            "rating_span":   max(ratings) - min(ratings),
            "naive_median_ms": round(naive_ms, 3),
            "fft_median_ms":   round(fft_ms,   3),
            "speedup":         round(naive_ms / fft_ms, 3) if fft_ms > 0 else None,
            **diff,
        }
        rows.append(row)
        print(f"    contest={cid:5d}  n={n:6d}  naive={naive_ms:7.1f}ms  "
              f"fft={fft_ms:7.1f}ms  speedup={naive_ms/fft_ms:.2f}x  "
              f"max_diff={diff['max_abs_final_delta_diff']}")
    return rows


# ── Plots ─────────────────────────────────────────────────────────────────────

def plot_runtime(df: pd.DataFrame) -> None:
    IMG.mkdir(parents=True, exist_ok=True)
    synth = df[(df["source"] == "synthetic") & (df["distribution"] == "clustered")]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(synth["n"], synth["naive_median_ms"], "o-", color="steelblue",
            linewidth=2, label="Naïve O(n²)")
    ax.plot(synth["n"], synth["fft_median_ms"],   "s-", color="tomato",
            linewidth=2, label="FFT O(D log D)")
    ax.set_xlabel("Participants (n)")
    ax.set_ylabel("Median runtime (ms)")
    ax.set_title("Runtime vs Participant Count — clustered distribution", fontweight="bold")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(IMG / "runtime_comparison.png", dpi=150)
    plt.close(fig)
    print("Wrote → img/runtime_comparison.png")


def plot_speedup(df: pd.DataFrame) -> None:
    IMG.mkdir(parents=True, exist_ok=True)
    synth = df[df["source"] == "synthetic"]
    colors = {"uniform": "steelblue", "clustered": "tomato", "bimodal": "seagreen"}

    fig, ax = plt.subplots(figsize=(9, 5))
    for dist, grp in synth.groupby("distribution"):
        grp = grp.sort_values("n")
        ax.plot(grp["n"], grp["speedup"], "o-", color=colors.get(str(dist), "gray"),
                linewidth=2, label=dist)

    ax.axhline(1.0, color="black", linewidth=0.8, linestyle="--", label="Breakeven (1×)")
    ax.set_xlabel("Participants (n)")
    ax.set_ylabel("Speedup (naïve / FFT)")
    ax.set_title("FFT Speedup vs Participant Count", fontweight="bold")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(IMG / "speedup_comparison.png", dpi=150)
    plt.close(fig)
    print("Wrote → img/speedup_comparison.png")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=== Synthetic benchmarks ===")
    rows = benchmark_synthetic()
    print("\n=== Real contest benchmarks ===")
    rows += benchmark_real()

    df = pd.DataFrame(rows)
    RESULTS.mkdir(parents=True, exist_ok=True)
    df.to_csv(RESULTS / "benchmark.csv", index=False)
    print(f"\nWrote {len(df)} rows → results/benchmark.csv")

    plot_runtime(df)
    plot_speedup(df)


if __name__ == "__main__":
    main()
