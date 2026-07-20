# cf-rating-analysis

Reimplementation and empirical analysis of the Codeforces rating algorithm.
Includes an O(n²) naive baseline and an FFT-accelerated engine that achieves
30–500× speedups on contest-scale inputs.

---

## What this is

The Codeforces rating system uses a pairwise Elo model to assign expected ranks,
then applies two anti-inflation corrections. Computing expected seeds naively
requires O(n²) pairwise comparisons. This project replaces that step with an
O(D log D) FFT convolution over the rating domain (D = 8,001), producing
identical final integer deltas at a fraction of the cost.

Beyond the algorithmic work, the project validates both engines against 12 real
contests (137,069 participant records) and investigates where the publicly
documented formula diverges from CF's actual output.

---

## Implementation status

| Component | Status |
|-----------|--------|
| Naive O(n²) engine (`cpp/src/naive.cpp`) | Complete |
| FFT O(D log D) engine (`cpp/src/fft.cpp`) | Complete |
| Validation against real CF data | Complete (12 contests) |
| Error metric analysis | Complete |
| Benchmark suite | Complete |
| Rating system design analysis | In progress (see `docs/findings.md`) |

---

## Key results

### Prediction accuracy (12 contests, 137,069 records)

| Contest era | n | Bias | MAE | Exact rate | Within-1 |
|-------------|---|------|-----|-----------|---------|
| Old-system (1000, 1100, 1200, 1300, 1500) | 25,265 | ≈ 0.0 | 0.44 | 55% | 100% |
| Mixed / new-system (remaining 7) | 111,804 | +7.5 | 8.7 | 6% | 15% |
| **Overall** | **137,069** | **+6.1** | **7.4** | **14%** | **30%** |

The engine reproduces CF rating changes exactly for pure old-system contests.
Errors appear only when new-account ramp-up offsets are involved and scale with
the proportion of participants still in their ramp-up period. The root cause
is not fully explained by the publicly documented algorithm; see `docs/findings.md`.

### Benchmark — real contests (Release build, single-threaded)

| Contest | n | Naive (ms) | FFT (ms) | Speedup | Max Δ diff |
|---------|---|-----------|---------|---------|-----------|
| 1000 | 3,832 | 90 | 3.1 | 29× | 0 |
| 1300 | 8,675 | 433 | 4.2 | 103× | 0 |
| 2050 | 17,951 | 1,824 | 6.5 | 282× | 0 |
| 2000 | 27,828 | 4,412 | 8.9 | **494×** | 0 |

FFT fixed overhead ≈ 2–9 ms (one convolution over D = 8,001); crossover with naive ≈ 500 participants. Max Δ diff = 0 across all tested cases — FFT floating-point error does not propagate into the final integer deltas.

---

## How the FFT works

The expected seed for participant i is:

```
seed_i = 1 + Σ_j P(j beats i)
```

Define the rating frequency array `f[x]` (# participants at rating x) and the
win-probability kernel `q[d] = 1/(1 + 10^(d/400))`. Then:

```
C[R] = Σ_x f[x] · q[R - x]     (global seed curve for any hypothetical R)
```

`C` is a discrete convolution of `f` and `q`, computed for all R simultaneously
via FFT in O(D log D). Each participant's actual seed corrects for self-inclusion
(`seed_i = 1 + C[r_i] − 0.5`), and the performance-rating binary search evaluates
the curve in O(log D) per participant, bringing the total to O(D log D + n log D).

Full derivation: [`docs/rating-system.md`](docs/rating-system.md).

---

## Building

Requires a C++17 compiler and CMake ≥ 3.15.

```bash
cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build cpp/build -j
```

Produces `cpp/build/naive` and `cpp/build/fft`.

---

## Running

Both engines share the same I/O contract.

**Input** (stdin):
```
n
rating_1 rank_1
rating_2 rank_2
...
```

**Output** (stdout, one row per participant):
```
rating  rank  seed  perf  final_delta  new_rating
```

**Runtime** (stderr): `<ms> ms`

Example:
```bash
echo "3
1200 1
1000 2
800 3" | ./cpp/build/naive
```

---

## Validation and analysis

```bash
# Validate naive engine against all cached contests
uv run python python/scripts/validate_engines.py --engine naive --all-cached

# Produce error_metrics.csv, grouped_metrics.csv, and img/error_by_ramp_stage.png
uv run python python/scripts/analyze_errors.py

# Produce benchmark.csv and runtime plots
uv run python python/scripts/benchmark_engines.py
```

---

## Tests

```bash
uv sync --dev
uv run pytest
```

41 tests: engine regression tests (parametrized over naive and FFT), differential
FFT-vs-naive agreement tests (seed error < 10⁻⁴, final Δ diff ≤ 1), and unit
tests for the `summarize_errors` metric function. Runs in < 1 s.

---

## Project structure

```
cf-rating-analysis/
├── cpp/
│   ├── CMakeLists.txt
│   └── src/
│       ├── naive.cpp          # O(n²) baseline
│       └── fft.cpp            # FFT-accelerated engine
├── python/
│   ├── scripts/
│   │   ├── validate_engines.py
│   │   ├── analyze_errors.py
│   │   └── benchmark_engines.py
│   └── src/
│       └── validation/
│           ├── runner.py      # subprocess engine runner
│           └── metrics.py     # summarize_errors()
├── tests/
│   ├── conftest.py
│   ├── test_engines.py
│   └── test_metrics.py
├── docs/
│   ├── rating-system.md       # algorithm derivation
│   ├── findings.md            # empirical results
│   └── benchmarks.md          # methodology and tables
├── results/
│   ├── error_metrics.csv
│   ├── grouped_metrics.csv
│   └── benchmark.csv
└── img/
```

---

## Limitations

- True ratings below 0 or above 8,000 are not supported. The benchmark clamps real contest data to [0, 8,000]; two participants in contest 1300 required this.
- The engine follows the 2015 public description of the CF algorithm. For contests with new-account participants, predicted deltas diverge from CF actual by 5–30 points on average. The mechanism is not fully identified.
- FFT precision is double-precision complex arithmetic. Convolution error < 10⁻⁸; validated to produce zero integer-delta differences against naive.

---

## References

- [Codeforces Rating System](https://codeforces.com/blog/entry/102)
- [Open CF Rating System](https://codeforces.com/blog/entry/20762)
- [New rating calculation for new accounts](https://codeforces.com/blog/entry/77890)
- [An Elo-like System for Massive Multiplayer Competitions](https://arxiv.org/abs/2101.00400)
- [Carrot extension](https://github.com/meooow25/carrot) — same FFT approach
- [Inconsistencies in Codeforces Rating System](https://codeforces.com/blog/entry/154911) — findings blog post
