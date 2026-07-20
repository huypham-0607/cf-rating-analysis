# Empirical Findings

## 1. Research Questions

**Primary:** How closely does an implementation of the publicly documented Codeforces rating algorithm reproduce historical rating changes?

**Secondary:** Are residual prediction errors associated with the participant composition of a contest?

---

## 2. Data and Contest Selection

**Source:** Codeforces API (`/contest.ratingChanges`). Rating changes include `oldRating`, `trueOldRating`, `newRating`, and `trueNewRating`. All computations use `trueOldRating` and `trueNewRating`; see §3.

**Sample:** 12 hand-selected contests analyzed in detail, covering 137,069 participant records.

| Era | Contest IDs |
|-----|-------------|
| Old (pre-new-account system) | 1000, 1100, 1200, 1300, 1500 |
| Transitional / mixed | 1400, 1585 |
| New (post-2020) | 2000, 2050, 2130, 2200, 2234 |

**Selection rationale:** Contests were chosen before observing results to represent a range of sizes, eras, and new-account fractions. They were not optimized post-hoc to maximize or minimize any metric. The sample is small and not random; generalizing beyond it requires caution.

**Exclusions:** Contests with missing API data were skipped. No per-participant exclusions were applied beyond what the raw data provides.

---

## 3. Prediction Baseline

The baseline follows the publicly documented algorithm:

1. Pairwise Elo win probabilities.
2. Expected seed per participant (sum of pairwise probabilities).
3. Geometric-mean target rank.
4. Performance rating via binary search on the seed function.
5. Raw delta = (performance rating − current rating) / 2.
6. Sum correction: ensure Σ Δ ≤ 0.
7. Top-player correction: ensure top min(n, 4√n) participants' sum ≤ 0.
8. Integer rounding.

All computations use `trueOldRating`, not the displayed rating. This is necessary for new-system accounts whose displayed rating differs by a ramp-up offset (+1400, +900, +550, +300, +150, or +50). Using displayed ratings instead of true ratings produces large errors even for pure old-system contests.

For full mathematical derivation, see `docs/rating-system.md`.

---

## 4. Evaluation Metrics

| Metric | Definition |
|--------|-----------|
| Signed bias | mean(predicted − actual) |
| MAE | mean(\|predicted − actual\|) |
| RMSE | √mean((predicted − actual)²) |
| Median error | median(predicted − actual) |
| Median absolute error | median(\|predicted − actual\|) |
| P90 absolute error | 90th percentile of \|error\| |
| Exact rate | fraction with \|error\| = 0 |
| Within-5 rate | fraction with \|error\| ≤ 5 |

Error sign convention: positive error = our engine predicted a higher rating change than CF actually applied (overprediction).

---

## 5. Confirmed Observations

The following findings are reproducible from `results/error_metrics.csv` and `results/grouped_metrics.csv`.

**5.1 Engine is exact on pure old-system contests.**

Contests 1000, 1100, 1200, 1300, and 1500 contain exclusively old-system participants (no ramp-up accounts). For all five, mean error = 0.00 and exact rate = 100%. This confirms that the implementation faithfully reproduces the documented algorithm for the unambiguous case.

**5.2 Positive signed bias on mixed-era contests.**

Across all 12 contests, the overall signed bias is **+6.1 rating points** (MAE = 7.4, RMSE = 13.8). The bias is always positive — our engine consistently overpredicts rating changes. A negative bias is never observed at the per-contest level.

**5.3 Bias scales with new-account fraction.**

Contests with no new-system participants have zero bias. Bias increases with the fraction of participants still in their ramp-up period. For contests 1585 (~60% new-system) and 2000 (~37% new-system), the mean error reaches +22 and +8 respectively. The relationship is not perfectly monotone across all contests, but the direction is consistent.

**5.4 Observed deflation exceeds the documented bound.**

The two documented correction stages imply a theoretical lower bound on mean delta of −11 per participant per contest (−1 from the sum correction, up to −10 from the top-player correction). Several analyzed contests show mean CF actual deltas below −11, which is mathematically impossible under the publicly described algorithm alone.

| Contest | Mean actual Δ | Implied mean correction | Within bound? |
|---------|--------------|------------------------|---------------|
| 1000 | −10.78 | −10.78 | Yes |
| 1585 | −33.31 | −33.31 | **No** (bound: −11) |
| 2050 | −20.64 | −20.64 | **No** |

**5.5 Residual errors are not uniform across participants.**

Among participants in the same contest, prediction error varies systematically:
- Participants in their **first rated contest** (s1, +1400 offset) have error ≈ 0, matching old-system accounts on pure-old contests.
- Participants in **subsequent ramp-up contests** (s2–s6) have progressively larger errors.
- Fully established (**old**-system) participants have the largest errors in mixed-era contests.

This pattern is reported in detail in §6.

**5.6 Rank-ordering violations observed in historical data.**

Under the CF consistency property ("if A had worse rating than B before the contest and finished on a worse place, then A's rating cannot exceed B's after"), no rank inversion should occur. However, historical data contains documented violations of this property — examples are noted in the published blog post (entry/154911).

---

## 6. Exploratory Patterns

The following patterns are observed in the analyzed sample but are not sufficiently consistent or explained to be stated as confirmed findings.

**6.1 Per-stage error approximation.**

Across the analyzed mixed-era contests, mean prediction error by ramp-up stage follows an approximate power-law relation:

$$\text{error}_{\text{stage}} \approx C \cdot \left(1 - \frac{\text{offset}}{1400}\right)^{\alpha}$$

where C is the mean error for fully established participants in that contest, and α ≈ 0.60 (aggregate fit). However, α varies across contests (range 0.20–1.27), indicating the shape is not stable and the model is not predictive. See `img/error_by_ramp_stage.png` for a summary chart.

**6.2 s1 accounts as an anchor.**

Participants in their first rated contest (s1, offset +1400) always have error ≈ 0. This constrains the space of possible hidden mechanisms: any mechanism that generates additional deflation for other participants must not affect s1 accounts.

---

## 7. Candidate Explanations

Multiple explanations are consistent with the observed data. No single explanation has been confirmed.

| Explanation | Evidence for | Evidence against |
|-------------|-------------|-----------------|
| Undocumented per-stage adjustment (e.g., s1 excluded from sum correction) | s1 zero-error, monotone stage pattern | Mechanism unknown; pattern inconsistent across contests |
| Formula change since 2015 | Deflation exceeds theoretical bound | No public announcement found |
| Special handling of new-account ratings | Positive bias appears exactly when new-sys accounts are present | Doesn't explain why error scales with stage rather than being uniform |
| Incorrect true-rating reconstruction | Would produce non-zero error on pure-old contests | Engine is exact on pure-old contests |
| Data-pipeline or API errors | Possible rounding in API responses | Error is systematic and directional, not random |
| Rounding/boundary behavior differences | Integer arithmetic diverges at boundaries | Differences are too large (up to 40 points) to be rounding only |

**Note:** The hypothesis that s1 accounts are excluded from the sum correction calculation is the most parsimonious explanation consistent with the data but has not been confirmed against CF's source code or official documentation.

---

## 8. Threats to Validity

- **Contest-selection bias:** Contests were hand-selected, not randomly sampled. Results may not generalize to all CF contests or time periods.
- **Limited sample:** 12 contests covering one specific era. Formula changes, seasonal effects, and contest-type differences are not controlled for.
- **Hidden production implementation:** The official blog describes the algorithm at a high level. The production system may differ in ways that are not publicly documented.
- **True-rating reconstruction:** `trueOldRating` is taken from the API; we assume it is the exact value used internally. If CF applies additional undocumented transformations before rating calculation, our baseline would be wrong.
- **Dependence between observations:** Participants' rating changes in the same contest are not independent (the correction stages create global coupling). Standard error estimates do not apply without adjustment.
- **Temporal confounding:** Old-era and new-era contests differ in many ways beyond new-account fraction (participant pool, problem difficulty calibration, etc.).

---

## 9. Conclusion

The publicly documented Codeforces rating formula reproduces historical rating changes exactly when all participants are fully established (no ramp-up offsets). For contests with new-system participants, the implementation consistently overpredicts rating changes, with the error correlated with — but not fully explained by — the proportion of ramping-up accounts.

The observed deflation in some contests exceeds what the documented correction stages can produce. This implies an additional mechanism, but the available evidence does not identify it uniquely. The results are consistent with the hypothesis that the production system handles new-account ramping differently than the publicly described formula suggests, but this remains speculative.

---

## 10. Non-Goals

This project does not claim to:
- Discover or reverse-engineer the complete current Codeforces production implementation.
- Guarantee exact prediction of any participant's rating change.
- Build a production-ready rating service.
- Establish causal mechanisms from observational data.

---

## 11. Reproduction

Ensure both engines are built:

```bash
cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build cpp/build -j
```

Run validation:

```bash
uv run python python/scripts/validate_engines.py --engine naive --all-cached
```

Produce error reports and charts:

```bash
uv run python python/scripts/analyze_errors.py
```

Run benchmarks:

```bash
uv run python python/scripts/benchmark_engines.py
```

Output files:
- `results/error_metrics.csv` — overall and per-contest metrics
- `results/grouped_metrics.csv` — metrics by stage and rating bucket
- `results/benchmark.csv` — runtime and correctness comparison
- `img/error_by_ramp_stage.png` — error by ramp-up stage
- `img/runtime_comparison.png` — runtime scaling
- `img/speedup_comparison.png` — FFT speedup curve
