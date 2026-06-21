# Development Doc for CFRatingAnalysis

Codeforces rating changes calculator, naive $\mathcal{O}(n^{2})$ baseline & FFT accelerated $\mathcal{O}(n\log n)$ computation. Validations against actual data from Codeforces.

## References
- Codeforces Rating System - https://codeforces.com/blog/entry/102 
- Open Codeforces Rating System  - https://codeforces.com/blog/entry/20762 
- Codeforces: Problem Difficulties - https://codeforces.com/blog/entry/62865 
- An Elo-like System for Massive Multiplayer Competitions - https://arxiv.org/abs/2101.00400
- New rating calculation for new accounts - https://codeforces.com/blog/entry/77890
- Carrot (Uses the same FFT idea for delta calc) - https://github.com/meooow25/carrot

## Project overview
- Implement baseline rating delta calculation in $\mathcal{O}(n^{2})$
- Implement fast rating delta calculation in $\mathcal{O}(n\log n)$ (Floating point FFT with Python/NP, C++ FFT/NTT, High-performance C++, etc...)
- Pull contest data from CF, validate model against said data, compare predicted to actual data. Analyze metrics.
- Investigate CF rating system design (Is CF rating zero-sum? How significant is CF rating deflation/inflation? How much correction is needed each contest?...)
- Optional Dashboard/Firefox extension.

## Core computational theory

Read rating-system.md

## Project structure
```
cf-ratinglab/
├── README.md
├── docs/
│   ├── rating-system.md
│   ├── development-doc.md
│   └── 
├── cpp/
│   ├── CMakeLists.txt
│   ├── src/
│   │   ├── naive.cpp
│   │   ├── fft.cpp
│   │   ├── 
│   │   └── 
│   ├── include/
│   │   ├── 
│   │   ├── 
│   │   └── 
│   ├── tests/
│   │   ├── 
│   │   ├── 
│   │   └── 
│   └── bench/
│       └── bench_naive_vs_fft.cpp
├── python/
│   ├── notebooks/
│   │   ├── validation.ipynb
│   │   └── rating_distribution.ipynb
│   │   scripts/
│   │   ├── fetch_data.py
│   │   ├── validate_contests.py
│   │   └── plot_benchmarks.py
│   └── src/
│       └── fetch_cf_data
│           └── fetch_cf_data.py
├── data/
│   └── raw/
│       ├── contest_list.json
│       └── rating_changes/
│           └── {contest_id}.json
│        
└── app/
    └── 
```

## Phase 1: Fetch contest data using Codeforces API.

Target endpoints:
- `api/contest.list`
- `api/contest.ratingChanges`

Contest list is saved in data/raw/contest_list.json
Rating changes is saved in data/raw/rating_changes/{contest_id}.json

Since Codeforces only uses the current system after round 327 (ID: 591), Old contests (ID  < 600) will be omitted.

## Phase 2: Naive implementation

## Phase 3: Validation

Run `naive.cpp` on contest rating changes data.

There is one challenge. 