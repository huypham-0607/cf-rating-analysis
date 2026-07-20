# Reconstructing and Accelerating the Codeforces Rating Algorithm

This document derives the publicly documented Codeforces rating formula from first principles, explains the O(n²) bottleneck, and shows how replacing the pairwise sum with an FFT-based convolution reduces the dominant cost to O(D log D) where D is the rating-domain width.

---

## 1. Scope and Assumptions

This reconstruction follows the algorithm described in the [Codeforces blog (2015)](https://codeforces.com/blog/entry/20762). The production implementation may differ in undocumented ways; see `docs/findings.md` for a discussion of observed discrepancies.

**New-account true ratings.** Codeforces applies a ramping offset for new accounts' first six contests (+1400, +900, +550, +300, +150, +50). All computations use the *true* internal rating, not the displayed rating. This is confirmed by validation: the engine produces zero error on pure old-system contests only when using `trueOldRating`.

---

## 2. Pairwise Expected Performance

For players with ratings r_i and r_j, the probability that player i beats player j follows a logistic (Elo-style) model:

$$P(i \text{ beats } j) = \frac{1}{1 + 10^{(r_j - r_i)/400}}$$

**Symmetry:** P(i beats j) + P(j beats i) = 1.

**Interpretation:** Equal ratings → P = 0.5. A 400-point advantage roughly triples the odds. The scale parameter 400 is a fixed constant from the CF system.

---

## 3. Expected Seed

For participant i, the *expected seed* (expected finishing position) before the contest is:

$$\text{seed}_i = 1 + \sum_{j \neq i} P(j \text{ beats } i)$$

- The sum counts the expected number of participants who will outperform i.
- The leading 1 accounts for one-based indexing (minimum seed is 1, not 0).
- A lower seed means a stronger expected result.

---

## 4. Performance Rating

Let m_i = geometric mean of the expected seed and the actual rank:

$$m_i = \sqrt{\text{seed}_i \cdot \text{rank}_i}$$

The *performance rating* R_i is the hypothetical starting rating at which participant i would have had expected seed m_i:

$$\text{seed}_i(R_i) = m_i$$

Because expected seed is a strictly decreasing function of hypothetical rating (higher rating → fewer expected opponents who outperform → lower seed), R_i is well-defined and found by binary search.

---

## 5. Raw Rating Change

$$\Delta_i^{(0)} = \frac{R_i - r_i}{2}$$

The halving dampens the update: participants converge toward their "true" level over several contests rather than in one step.

---

## 6. Global Anti-Inflation Corrections

Two corrections are applied in sequence to prevent systematic rating inflation.

**Correction 1 — Sum correction.** Let t = Σ Δ_i^(0). Apply a uniform integer offset to every participant:

$$c_1 = \left\lfloor \frac{-t}{n} - 1 \right\rfloor$$
$$\Delta_i^{(1)} = \Delta_i^{(0)} + c_1$$

This guarantees Σ Δ_i^(1) ≤ 0: the contest cannot add net rating to the pool.

**Correction 2 — Top-player correction.** Let S be the top min(n, 4√n) participants by *pre-contest* rating. Compute:

$$c_2 = \min\!\left(\max\!\left(\left\lfloor \frac{-\sum_{i \in S} \Delta_i^{(1)}}{|S|} \right\rfloor, -10\right), 0\right)$$

Apply c_2 to every participant:

$$\Delta_i^{\text{final}} = \text{round}(\Delta_i^{(1)} + c_2)$$

This ensures the top-player group cannot collectively gain rating, bounded to at most −10 per participant to avoid extreme adjustments.

**New rating:**

$$r_i' = r_i + \Delta_i^{\text{final}}$$

---

## 7. Naïve Complexity

Computing seed_i requires summing over all j ≠ i: O(n) per participant, O(n²) total. The performance-rating binary search for participant i evaluates seed_i(R) at each candidate R, again O(n) per evaluation and O(n log MAX_RATING) per participant — dominated by the O(n²) seed cost. For contests with thousands of participants (modern CF rounds have 15,000–30,000), this is prohibitively slow.

---

## 8. Convolution Formulation

The key insight is that the seed computation has a convolution structure. Define:

- **Frequency array** f[x] = number of participants with rating x, for x ∈ [0, D).
- **Probability kernel** q[d] = P(a player with rating d lower than the target beats the target) = 1/(1 + 10^(d/400)), for d ∈ (-(D-1), D-1).

Then the *global seed curve* — the expected seed for a hypothetical player at any rating R, including all n participants — is:

$$C[R] = \sum_{x} f[x] \cdot q[R - x]$$

This is a **discrete convolution** of f and q. The convolution can be computed for all R simultaneously using the FFT in O(D log D) time.

---

## 9. Convolution Indexing — Worked Example

Ratings: {1000, 1000, 1200}. D = 8001 (ratings 0 to 8000).

Frequency array: f[1000] = 2, f[1200] = 1, all others 0.

For a hypothetical player at R = 1100:

$$C[1100] = f[1000] \cdot q[100] + f[1200] \cdot q[-100]$$
$$= 2 \cdot \frac{1}{1+10^{100/400}} + 1 \cdot \frac{1}{1+10^{-100/400}}$$
$$\approx 2 \cdot 0.360 + 1 \cdot 0.640 = 1.360$$

**Array representation.** Store the kernel as kern[i] = q[i − (D−1)] for i ∈ [0, 2D−2]. Then:

$$(f * \text{kern})[R + (D-1)] = C[R]$$

**Zero-padding.** The output of the linear convolution has length D + (2D−1) − 1 = 3D − 2 = 24,001 entries. Round up to the next power of two (32,768) for FFT efficiency.

---

## 10. Participant Self-Exclusion

C[R] sums over *all* n participants, including participant i themselves. The actual expected seed of participant i at hypothetical rating R must exclude i's self-contribution:

$$\text{seed}_i(R) = 1 + C[R] - P(i \text{ beats hypothetical at } R)$$

where P(i beats R) = 1/(1 + 10^((R − r_i)/400)).

**At the actual rating** (R = r_i): P(i beats r_i) = 0.5 (ties contribute exactly 0.5).

**During binary search** (R ≠ r_i): The subtracted term is not 0.5 and must be computed analytically from the participant's true rating r_i and the candidate R.

This self-exclusion step is critical. Omitting it causes the seed curve to overcount by one participant, producing systematically wrong performance ratings.

---

## 11. Performance-Rating Lookup Using the Seed Curve

Once C[R] is precomputed for all integer R in [0, 8000], the binary search for participant i's performance rating evaluates:

$$\text{seed}_i(R) = 1 + C[R] - \frac{1}{1 + 10^{(R - r_i)/400}}$$

at each candidate R. The lookup into C is O(1), so each evaluation is O(1). The binary search over [0, 8000] takes O(log 8000) ≈ 13 steps. Total cost for all n participants: O(n log D).

---

## 12. Numerical Accuracy

The FFT uses complex double-precision floating-point arithmetic. Numerical error accumulates in:

1. **Convolution rounding.** The imaginary parts of the IFFT result should be near zero; their magnitude characterizes convolution error. In practice this is < 10⁻⁸ for our domain sizes.
2. **Binary search threshold.** The seed curve is evaluated with floating-point values; a small error in C[R] can shift the binary search boundary by one integer rating point.
3. **Final rounding.** Performance ratings are integers; a 1-point shift translates to a 0.5-point shift in raw delta and, after halving and rounding, typically zero or one point in the final integer delta.

**Validation:** The test suite (`tests/test_engines.py`) compares FFT and naive final deltas on several synthetic contests. See `docs/benchmarks.md` for measured tolerance bounds.

---

## 13. Final Complexity

Let n = participant count, D = rating-domain width (8,001 for ratings 0–8,000).

| Step | Naïve | FFT |
|------|-------|-----|
| All seeds | O(n²) | O(D log D) — convolution |
| Performance ratings | O(n² log D) | O(n log D) — binary search |
| Correction steps | O(n log n) | O(n log n) |
| **Total** | **O(n²)** | **O(D log D + n log D)** |

With D = 8,001 fixed, the FFT engine scales near-linearly in participant count. The crossover (where FFT fixed overhead is recovered) is approximately n = 500 on the benchmark machine; beyond that, speedup grows quadratically with n.

A résumé-friendly summary: "Replaced O(n²) pairwise rating calculations with an O(D log D) FFT-based convolution, achieving 30–500× speedups on contest-scale inputs."

---

## 14. Limitations

- The supported rating domain is [0, 8000]. Participants with true ratings outside this range are rejected; preprocessing should clamp or filter such values.
- The reconstruction follows the 2015 public description. The production algorithm may have been modified since; see `docs/findings.md` for observed discrepancies.
- The convolution assumes all ratings are integers. Non-integer ratings are not supported.

---

## 15. References

- [Codeforces Rating System (2013)](https://codeforces.com/blog/entry/102)
- [Open CF Rating System (2015)](https://codeforces.com/blog/entry/20762)
- [New rating calculation for new accounts (2020)](https://codeforces.com/blog/entry/77890)
- [An Elo-like System for Massive Multiplayer Competitions](https://arxiv.org/abs/2101.00400)
- [Carrot extension](https://github.com/meooow25/carrot) — uses the same FFT approach
