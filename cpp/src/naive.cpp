#include <stdio.h>
#include <iostream>
#include <vector>
#include <cmath>
#include <chrono>
#include <numeric>
#include <algorithm>

/*
    Calculate rating changes for each participant in a contest in O(n^2)

    Input format:
    n
    r_old_1 rank_1
    r_old_2 rank_2
    ...
    r_old_n rank_n

    Output format:
    seed_1 perf_1 delta_raw_1 delta_adjusted_1 delta_final_1 new_rating_1
    seed_2 perf_2 delta_raw_2 delta_adjusted_2 delta_final_2 new_rating_2
    ...
    seed_n perf_n delta_raw_n delta_adjusted_n delta_final_n new_rating_n
*/

struct player {
    int rating;
    int ranking;

    player (int _rating=0, int _ranking=0): rating(_rating), ranking(_ranking) {};
};

constexpr int OFFSET = 10000;
constexpr int G_SIZE = 20001;
double g[G_SIZE];

// Generate reference table g (probabiltiy for i to beat j with rating delta d).
void generate_g_table();

// Calculate P_i_j .ie Probability that player i will beat player j in contest.
double compute_p(const int, const int);

// Calculate expected seed for player i with current rating r.
double get_seed(const std::vector<player> &, int, double); 

// Calculate performance (initial rating where delta equals 0) for player i at rank rnk.
int compute_perf(const std::vector<player> &, int, double);

int main() {
    // freopen("naive_test.in","r",stdin);
    // freopen("naive_test.out","w",stdout);
    int n = 0; fscanf(stdin,"%d\n", &n);

    // std::cerr << n << "\n";

    std::vector<player> players(n,player());
    for (int i=0; i<n; i++){
        fscanf(stdin,"%d %d", &players[i].rating, &players[i].ranking);
        // std::cerr << players[i].rating << " " << players[i].ranking << "\n";
    }

    auto t0 = std::chrono::high_resolution_clock::now();
    generate_g_table();
    std::vector<double> seed(n,0.0);
    std::vector<int> perf(n,0);
    std::vector<double> delta_raw(n,0.0);
    std::vector<double> delta_adj(n,0.0);
    double t = 0;
    for (int i=0; i<n; i++){
        // std::cerr << "raw_delta: " << i << " " << players[i].rating << " " << players[i].ranking << "\n";
        seed[i] = get_seed(players, i, players[i].rating);
        // std::cerr << "seed: " << seed[i] << "\n";
        double g_mean = sqrt(seed[i]*players[i].ranking);
        // std::cerr << "g_mean: " << g_mean << "\n";
        perf[i] = compute_perf(players, i, players[i].ranking);
        // std::cerr << "perf: " << perf[i] << "\n";
        delta_raw[i] = delta_adj[i] = (double)(compute_perf(players, i, g_mean)-players[i].rating)/2;
        
        t += delta_raw[i];
    }

    // std::cerr << "passed raw delta compute\n";

    for (int i=0; i<n; i++){
        delta_adj[i] += (-t)/n - 1;
    }
    std::vector<int> old_rating_order(n);
    std::iota(old_rating_order.begin(), old_rating_order.end(), 0);
    std::sort(old_rating_order.begin(), old_rating_order.end(),
              [&](int i, int j){return (players[i].rating > players[j].rating);});
    int m = std::min(n,4*(int)ceil(sqrt(n)));

    t = 0;
    for (int i=0; i<m; i++){
        t += delta_adj[old_rating_order[i]];
    }
    for (int i=0; i<n; i++){
        delta_adj[i] += std::min(std::max((-t)/m,(double)-10),(double)0);
    }
    
    auto t1 = std::chrono::high_resolution_clock::now();
    double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    fprintf(stderr, "%.3f\n", ms);
    
    for (int i=0; i<n; i++){
        int fdelta = round(delta_adj[i]);
        fprintf(stdout, "%f %d %f %f %d %d\n", seed[i], perf[i], delta_raw[i], delta_adj[i],
               fdelta, players[i].rating + fdelta);
    }
}

void generate_g_table() {
    for (int i=0; i<G_SIZE; i++){
        g[i] = (double)1/(1+pow(10,(double)(i-OFFSET)/400));
    }
}

double compute_p(const int i, const int j) {
    return g[j-i+OFFSET];
}

double get_seed(const std::vector<player> &players, int i, double rating) {
    double res = 1;
    for (int j=0; j<(int)players.size(); j++){
        //if (i==j) continue;
        res += compute_p(players[j].rating, rating);
    }
    return res;
}

int compute_perf(const std::vector<player> &players, int i, double rank) {
    int l = -OFFSET/2, r = +OFFSET/2;
    int ans = OFFSET/2;
    while (l<=r) {
        int mid = (l+r)/2;
        if (get_seed(players, i, mid) < rank) {
            ans = mid;
            r = mid-1;
        }
        else {
            l = mid+1;
        }
    }
    return ans;
}