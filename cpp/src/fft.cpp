/**
 * FFT-accelerated implementation of the Codeforces rating algorithm.
 *
 * The dominant O(n^2) bottleneck in the naive engine is computing each
 * participant's expected seed — a sum over all other participants. By
 * representing the contest's rating histogram as a frequency array f[r]
 * and the win-probability function as a kernel q[d] = 1/(1+10^(d/400)),
 * the full seed curve over all ratings becomes a discrete convolution:
 *
 *   C[R] = sum_x  f[x] * q[R - x]
 *
 * This is evaluated in O(D log D) via FFT, where D is the supported rating
 * domain width. Individual participant seeds and performance-rating lookups
 * then follow from the precomputed curve in O(n log D) total.
 *
 * See docs/rating-system.md for the full mathematical derivation.
 *
 * Input/output/timing format: identical to naive.cpp.
 */

#include <algorithm>
#include <chrono>
#include <cmath>
#include <complex>
#include <cstdio>
#include <numeric>
#include <vector>

using cd     = std::complex<double>;
using vec_cd = std::vector<cd>;

static const double PI = std::acos(-1.0);

// In-place iterative Cooley–Tukey FFT; a.size() must be a power of two.
static void fft(vec_cd& a, bool invert) {
    int n = (int)a.size();
    for (int i = 1, j = 0; i < n; i++) {
        int bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) std::swap(a[i], a[j]);
    }
    for (int len = 2; len <= n; len <<= 1) {
        double ang = 2.0 * PI / len * (invert ? -1 : 1);
        cd wlen(std::cos(ang), std::sin(ang));
        for (int i = 0; i < n; i += len) {
            cd w(1.0);
            for (int j = 0; j < len / 2; j++) {
                cd u = a[i + j], v = a[i + j + len / 2] * w;
                a[i + j]         = u + v;
                a[i + j + len/2] = u - v;
                w *= wlen;
            }
        }
    }
    if (invert)
        for (cd& x : a) x /= n;
}

// Linear convolution of two real-valued sequences.
static std::vector<double> convolve(const std::vector<double>& f,
                                    const std::vector<double>& g) {
    size_t result_len = f.size() + g.size() - 1;
    size_t n = 1;
    while (n < result_len) n <<= 1;

    vec_cd fa(n), fb(n);
    for (size_t i = 0; i < f.size(); i++) fa[i] = f[i];
    for (size_t i = 0; i < g.size(); i++) fb[i] = g[i];

    fft(fa, false);
    fft(fb, false);
    for (size_t i = 0; i < n; i++) fa[i] *= fb[i];
    fft(fa, true);

    std::vector<double> result(result_len);
    for (size_t i = 0; i < result_len; i++)
        result[i] = fa[i].real();
    return result;
}

constexpr int MIN_RATING = 0;
constexpr int MAX_RATING = 8000;
constexpr int D          = MAX_RATING - MIN_RATING + 1;  // 8001

struct Participant {
    int rating;
    int rank;
    Participant(int r = 0, int k = 0) : rating(r), rank(k) {}
};

// Seed curve C[R] = sum_x f[x] * q[R-x], where q[d] = 1/(1+10^(d/400)).
// Convolution identity: (f * kern)[R + (D-1)] = C[R],
// where kern[i] = q[i - (D-1)] for i in [0, 2D-2].
static std::vector<double> build_seed_curve(const std::vector<double>& freq) {
    // kernel[i] = q[i - (D-1)] = 1/(1+10^((i-(D-1))/400))
    std::vector<double> kern(2 * D - 1);
    for (int i = 0; i < 2 * D - 1; i++) {
        double d = i - (D - 1);
        kern[i]  = 1.0 / (1.0 + std::pow(10.0, d / 400.0));
    }

    auto conv = convolve(freq, kern);

    // Extract C[R] = conv[R - MIN_RATING + (D-1)] for R in [MIN_RATING, MAX_RATING]
    std::vector<double> curve(D);
    for (int r = MIN_RATING; r <= MAX_RATING; r++)
        curve[r - MIN_RATING] = conv[r - MIN_RATING + (D - 1)];
    return curve;
}

// Inline win probability (no table needed; called rarely in binary search).
static inline double win_prob(int a, int b) {
    return 1.0 / (1.0 + std::pow(10.0, (double)(b - a) / 400.0));
}

// Expected seed of participant `p` at hypothetical rating R,
// using the precomputed seed curve.
// Self-exclusion: subtract p's own contribution from C[R].
static inline double hyp_seed(int p_rating, int R,
                               const std::vector<double>& curve) {
    return 1.0 + curve[R - MIN_RATING] - win_prob(p_rating, R);
}

// Largest integer R in [MIN_RATING, MAX_RATING] where hyp_seed(R) >= target.
static int performance_rating(int p_rating, double target,
                               const std::vector<double>& curve) {
    int lo = MIN_RATING, hi = MAX_RATING, ans = MIN_RATING;
    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        if (hyp_seed(p_rating, mid, curve) >= target) {
            ans = mid;
            lo  = mid + 1;
        } else {
            hi = mid - 1;
        }
    }
    return ans;
}

int main() {
    int n = 0;
    if (std::fscanf(stdin, "%d", &n) != 1 || n <= 0) {
        std::fprintf(stderr, "error: invalid participant count\n");
        return 1;
    }

    std::vector<Participant> ps(n);
    for (int i = 0; i < n; i++) {
        if (std::fscanf(stdin, "%d %d", &ps[i].rating, &ps[i].rank) != 2) {
            std::fprintf(stderr, "error: malformed input at participant %d\n", i);
            return 1;
        }
        if (ps[i].rating < MIN_RATING || ps[i].rating > MAX_RATING) {
            std::fprintf(stderr, "error: rating %d out of supported range [%d, %d]\n",
                         ps[i].rating, MIN_RATING, MAX_RATING);
            return 1;
        }
    }

    // Normalize tied ranks to upper-bound.
    {
        int prev = 0;
        for (int i = 1; i < n; i++) {
            if (ps[i].rank != ps[prev].rank) {
                for (int k = prev; k < i; k++) ps[k].rank = i;
                prev = i;
            }
        }
        for (int k = prev; k < n; k++) ps[k].rank = n;
    }

    auto t0 = std::chrono::high_resolution_clock::now();

    // Build frequency array.
    std::vector<double> freq(D, 0.0);
    for (const auto& p : ps) freq[p.rating - MIN_RATING] += 1.0;

    // Build seed curve via FFT convolution.
    auto curve = build_seed_curve(freq);

    // Compute seeds and raw deltas.
    std::vector<double> seed(n), raw_delta(n), adj_delta(n);
    double sum_raw = 0.0;

    for (int i = 0; i < n; i++) {
        // Actual seed: C[r_i] minus self (P(i beats i) = 0.5).
        seed[i] = 1.0 + curve[ps[i].rating - MIN_RATING] - 0.5;

        double m     = std::sqrt(seed[i] * ps[i].rank);
        int    perf  = performance_rating(ps[i].rating, m, curve);
        raw_delta[i] = adj_delta[i] = (perf - ps[i].rating) / 2.0;
        sum_raw     += raw_delta[i];
    }

    // Correction 1: sum correction.
    int sc1 = (int)((-sum_raw) / n - 1);
    for (int i = 0; i < n; i++) adj_delta[i] += sc1;

    // Correction 2: top-player correction.
    int m = std::min(n, 4 * (int)std::round(std::sqrt(n)));
    std::vector<int> by_rating(n);
    std::iota(by_rating.begin(), by_rating.end(), 0);
    std::sort(by_rating.begin(), by_rating.end(),
              [&](int a, int b) { return ps[a].rating > ps[b].rating; });

    double sum_top = 0.0;
    for (int i = 0; i < m; i++) sum_top += adj_delta[by_rating[i]];
    int sc2 = std::min(std::max((int)(-sum_top / m), -10), 0);
    for (int i = 0; i < n; i++) adj_delta[i] += sc2;

    auto t1  = std::chrono::high_resolution_clock::now();
    double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    std::fprintf(stderr, "%.3f %d\n", ms, sc1 + sc2);

    for (int i = 0; i < n; i++) {
        // perf output uses actual rank (not geometric-mean target) — matches naive.
        int perf_out    = performance_rating(ps[i].rating, ps[i].rank, curve);
        int final_delta = (int)std::round(adj_delta[i]);
        std::fprintf(stdout, "%f %d %f %f %d %d\n",
                     seed[i], perf_out,
                     raw_delta[i], adj_delta[i],
                     final_delta, ps[i].rating + final_delta);
    }
    return 0;
}
