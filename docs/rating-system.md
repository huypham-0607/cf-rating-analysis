# Codeforces Rating System Overview
Improved rating predictor for Codeforces

## References
- Codeforces Rating System - https://codeforces.com/blog/entry/102 
- Open Codeforces Rating System  - https://codeforces.com/blog/entry/20762 
- Codeforces: Problem Difficulties - https://codeforces.com/blog/entry/62865 
- An Elo-like System for Massive Multiplayer Competitions - https://arxiv.org/abs/2101.00400
- New rating calculation for new accounts - https://codeforces.com/blog/entry/77890


## How CF rating system works

### What rating number represents

On Codeforces, each account is characterized by their rating. Generally speaking, the higher the rating, the better then contest performance. 

Rating is updated to best satisfy this equality

$P_{i,j} = \frac{1}{1+10^{\frac{r_{j}-r_{i}}{400}}}$

Where $P_{i,j}$ is the probability that Player $i$ will beat player $j$ in a contest.

### Expected ranking

Before the contest, an expected ranking $seed_{i}$ is calculated for each player.

$seed_{i} = \sum_{\substack{j=1 \\ j \neq i}}^{n} P_{i,j} + 1$

That is, sum over all other players of probability of beating the $i$-th player (offset by $1$ due to indexing).

The high level idea is to increase rating if actual ranking is better than expected ranking, and vice versa.

### Calculating Raw Delta

To calculate the rating change, we first calculate geometric mean of $seed_{i}$ and $actual_{i}$. Let's call it $m_{i}$. We can find rating value $R$ such that if player $i$ has initial rating $R$, then $seed_{i} = m_{i}$.

Then, rating change will be $d_{i} = \frac{R-r_{i}}{2}$

### Anti-inflation correction.

This model works conceptually, but there are 2 main issues we have to address

- Total rating change $d_{i}$ should not be positive.
- Total rating change for top participants should not be positive (ie "the rich get richer" phenomenon mentioned in the blog).

To combat this. Codeforces employs two tactics.

First, $r_{i} = r_{i} + inc$, where $inc = \frac{\sum_{i = 1}^{n}d_{i}}{n} - 1$. This makes sum of all $d_{i}$ near zero and non-positive at the same time.

Then, we choose a group of $min(n,4\sqrt{n})$ highest rated players before the contest. Lets call this group $S$. Then, set $r_{i} = r_{i} + inc$ for all participants in contest, where $inc = min(max(-\frac{\sum_{i}^{i \in S}d_{i}}{|S|},-10),0)$. That is, $inc$ is the negative of average $d_{i}$ of all players in $S$, bounded by $[-10,0]$

Combined, these two corrections prevents global rating inflation while also keep rating value of top players in check. This method also seems to cause slight rating deflation, but perhaps it isn't an issue in practice.

### Optimization

We need a fast way to quickly calculate delta of all participant in the contest. Fortunately, most of the calculations are pretty straight forward. The only issue is calculating expected seed of each participant, which, if done naively, would take $\mathcal{O}(n)$ for each player.

We will solve this problem using FFT. Define $f(i)$ as the frequency table of rating for participants of a contest, $g(i)$ as the function $\frac{1}{1+10^{\frac{i}{400}}}$. Then, expected seed of $j$-th player is the following.

$S[j] = \sum_{min(r_{i})}^{max(r_{i})}f[i]\cdot g[i-j]$

We precompute $g[i]$ for every possible value of $r_{i}$, then commpute $S[i]$. Total complexity is $\mathcal{O}(d\log d)$ where $d = max(r_{i}) - min(r_{i})$.

The last obstacle is to find performance rating $R$, which can be trivially done with a binary search.