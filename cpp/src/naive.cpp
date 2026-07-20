/**
 * Direct O(n^2) implementation of the publicly documented Codeforces rating algorithm.
 *
 * Expected seeds are computed via pairwise Elo probabilities — O(n) per participant,
 * O(n^2) total. Performance-rating lookup uses binary search over the seed function.
 * This engine serves as the correctness baseline for the FFT implementation.
 *
 * Input (stdin):
 *   n
 *   rating_1 rank_1
 *   ...
 *   rating_n rank_n
 *   (participants in rank order; duplicate ranks allowed)
 *
 * Output (stdout):
 *   One line per participant:
 *   seed performance_rating raw_delta adjusted_delta final_delta new_rating
 *
 * Timing (stderr):
 *   runtime_ms correction_offset
 */

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <numeric>
#include <vector>

struct Participant {
    int rating;
    int rank;
    Participant(int r = 0, int k = 0) : rating(r), rank(k) {}
};

// Precomputed win-probability lookup table.
// g[d + OFFSET] = P(player with rating d higher than opponent beats opponent)
//               = 1 / (1 + 10^(-d/400))
constexpr int PROB_OFFSET = 16000;
constexpr int PROB_SIZE   = 32001;
constexpr int MAX_PERF    = 8000;
static double g[PROB_SIZE];

static void build_prob_table() {
    for (int i = 0; i < PROB_SIZE; i++)
        g[i] = 1.0 / (1.0 + std::pow(10.0, (double)(i - PROB_OFFSET) / 400.0));
}

// P(player with rating b beats player with rating a).
static inline double win_prob(int a, int b) {
    return g[b - a + PROB_OFFSET];
}

// Expected seed of a hypothetical player at `rating`, excluding participant `self`.
static double expected_seed(const std::vector<Participant>& ps, int self, double rating) {
    double s = 1.0;
    for (int j = 0; j < (int)ps.size(); j++) {
        if (j == self) continue;
        s += win_prob(ps[j].rating, (int)rating);
    }
    return s;
}

// Largest integer rating R in [0, MAX_PERF] where expected_seed(R) >= target.
static int performance_rating(const std::vector<Participant>& ps, int self, double target) {
    int lo = 0, hi = MAX_PERF, ans = 0;
    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        if (expected_seed(ps, self, mid) >= target) {
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
    }

    // Normalize tied ranks to upper-bound (same as CF: all tied participants
    // receive the rank of the last among them).
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

    build_prob_table();

    std::vector<double> seed(n), raw_delta(n), adj_delta(n);
    double sum_raw = 0.0;

    for (int i = 0; i < n; i++) {
        seed[i]      = expected_seed(ps, i, ps[i].rating);
        double m     = std::sqrt(seed[i] * ps[i].rank);
        raw_delta[i] = adj_delta[i] = (performance_rating(ps, i, m) - ps[i].rating) / 2.0;
        sum_raw     += raw_delta[i];
    }

    // Correction 1: keep total delta <= 0 (sum correction).
    int sc1 = (int)((-sum_raw) / n - 1);
    for (int i = 0; i < n; i++) adj_delta[i] += sc1;

    // Correction 2: keep top-player group sum <= 0 (top-player correction).
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
        int final_delta = (int)std::round(adj_delta[i]);
        std::fprintf(stdout, "%f %d %f %f %d %d\n",
                     seed[i], performance_rating(ps, i, ps[i].rank),
                     raw_delta[i], adj_delta[i],
                     final_delta, ps[i].rating + final_delta);
    }
    return 0;
}
