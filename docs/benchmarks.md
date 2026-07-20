# Benchmark Methodology and Results

## Machine Environment

| Property | Value |
|----------|-------|
| Platform | Linux (Arch Linux) |
| Compiler | GCC 16.1.1 |
| Build type | Release (`-DCMAKE_BUILD_TYPE=Release`) |
| Timing method | `std::chrono::high_resolution_clock` inside the binary |
| Threads | Single-threaded |
| Runs per case | 5 (median reported); 1 warm-up run excluded |

Benchmarks were run on an otherwise idle machine. Results are representative of algorithmic scaling, not absolute performance under production conditions.

---

## Correctness Claim

The FFT engine computes the expected-rank convolution using floating-point complex arithmetic and is validated against the direct O(n²) implementation.

Across all benchmark cases, the maximum difference between naive and FFT final integer deltas was **0 points** — both engines produced identical final rating changes for every participant in every tested case.

Seed values agreed to within 10⁻⁴ in all cases. Small floating-point errors in the FFT convolution are absorbed during binary-search rounding, resulting in no observable difference in the integer-valued final deltas.

---

## Runtime Claim

The FFT engine has greater fixed overhead (~2 ms) from building and transforming the frequency array and kernel. This overhead is amortized across participants as n grows.

**Crossover point:** approximately n = 500 participants (clustered distribution).  
Beyond the crossover, speedup grows approximately as n² / (D log D).

---

## Complexity Claim

The naive engine performs O(n²) pairwise operations for expected-seed computation.

The FFT engine replaces this with:
- O(D log D) FFT convolution over the rating domain of width D = 8,001
- O(n log D) per-participant performance-rating lookup

A résumé-accurate phrasing: "Accelerated pairwise rating calculations using FFT-based convolution, replacing quadratic participant interactions with near-linear scaling over a bounded rating domain."

Do not state this as simply O(n log n) without defining D; the full bound is O(D log D + n log D).

---

## Synthetic Benchmark Results

Three rating distributions across six participant counts. Median runtime over 5 runs.

### Clustered Distribution (Gaussian around rating 1400, σ = 300)

| n | Naïve (ms) | FFT (ms) | Speedup | Max Δ diff |
|---|-----------|---------|---------|-----------|
| 100 | 0.4 | 2.2 | 0.18× | 0 |
| 250 | 0.7 | 2.2 | 0.33× | 0 |
| 500 | 1.9 | 2.2 | 0.87× | 0 |
| 1,000 | 6.7 | 2.3 | 2.90× | 0 |
| 2,000 | 25.7 | 2.5 | 10.3× | 0 |
| 4,000 | 96.9 | 2.8 | 35.3× | 0 |

### Uniform Distribution (ratings drawn uniformly from [0, 4000])

| n | Naïve (ms) | FFT (ms) | Speedup | Max Δ diff |
|---|-----------|---------|---------|-----------|
| 500 | 2.0 | 2.2 | 0.90× | 0 |
| 1,000 | 6.9 | 2.3 | 2.96× | 0 |
| 2,000 | 26.0 | 2.5 | 10.4× | 0 |
| 4,000 | 99.3 | 2.9 | 34.4× | 0 |

### Bimodal Distribution (half ~N(800,200), half ~N(2200,200))

| n | Naïve (ms) | FFT (ms) | Speedup | Max Δ diff |
|---|-----------|---------|---------|-----------|
| 500 | 1.9 | 2.2 | 0.87× | 0 |
| 1,000 | 6.7 | 2.3 | 2.90× | 0 |
| 2,000 | 25.8 | 2.5 | 10.4× | 0 |
| 4,000 | 97.2 | 2.8 | 34.8× | 0 |

The distribution type has negligible effect on FFT runtime (FFT cost is dominated by D, not the rating distribution). The naïve engine also shows no distribution dependence, as expected.

---

## Real Contest Benchmark Results

Four historical contests covering a range of participant counts.

| Contest | n | Naïve (ms) | FFT (ms) | Speedup | Max Δ diff |
|---------|---|-----------|---------|---------|-----------|
| 1000 | 3,832 | 90.1 | 3.1 | 29× | 0 |
| 1300 | 8,675 | 432.7 | 4.2 | 103× | 0 |
| 2000 | 27,828 | 4,412 | 8.9 | 494× | 0 |
| 2050 | 17,951 | 1,824 | 6.5 | 282× | 0 |

Note: Two participants in contest 1300 had `trueOldRating < 0` (a ramp-up edge case). These were clamped to 0 before processing.

---

## Interpretation

**FFT overhead.** The ~2–9 ms FFT baseline is the cost of constructing the 16,001-element kernel, zero-padding to 32,768, and performing the transform. This is independent of n, which is why small contests run slower than naive.

**Scaling.** Beyond the crossover, runtime scales roughly as:
- Naïve: O(n²) → quadratic growth clearly visible
- FFT: O(D log D) = O(constant) for fixed D → nearly flat

**Distribution insensitivity.** The FFT's cost depends only on D (rating domain width), not on participant rating distribution. Clustered, uniform, and bimodal inputs take effectively the same FFT time at equal n.

**Integer-exact results.** Final integer deltas matched exactly (0 differences) across all cases. This confirms that FFT floating-point error does not propagate into rating changes for this domain size.

---

## Reproduction

```bash
cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build cpp/build -j
uv run python python/scripts/benchmark_engines.py
```

Output: `results/benchmark.csv`, `img/runtime_comparison.png`, `img/speedup_comparison.png`.

Random seed is fixed (RAND_SEED = 42) for reproducibility.
