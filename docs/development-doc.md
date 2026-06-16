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

## 