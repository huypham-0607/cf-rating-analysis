'''
Deflation analysis across old-era (1000-1585) and new-era (>2000) contests.

For each contest, computes:
  - sum / mean of CF actual trueDelta
  - sum / mean of our engine's predicted delta
  - breakdown by stage (stage-0, stage-1+, old-sys)

Caches per-participant results in data/validation/deflation/per_participant.csv
Outputs a per-contest summary to data/validation/deflation/summary.csv
'''

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from validation.loader import load_contest
from validation.runner import run_naive_engine
from utils import get_logger, _load, PROJECT_ROOT

OLD_ERA_CONTESTS = [1000, 1100, 1200, 1300, 1400, 1500, 1585]
NEW_ERA_CONTESTS  = [2000, 2050, 2130, 2200, 2234]

RC_DIR     = PROJECT_ROOT / 'data' / 'final' / 'rating_changes'
OUT_DIR    = PROJECT_ROOT / 'data' / 'validation' / 'deflation'
CACHE_PATH = OUT_DIR / 'per_participant.csv'
SUMMARY_PATH = OUT_DIR / 'summary.csv'

OFFSETS = [1400, 900, 550, 300, 150, 50, 0]

logger = get_logger(__name__)


def get_stage(true_old: int, old: int) -> int:
    diff = true_old - old
    for k, o in enumerate(OFFSETS[:-1]):
        if o == diff:
            return k          # 0 = stage-0, 1..5 = stage-1+
    return 7                  # old-sys


def load_cache() -> dict[int, list[dict]]:
    '''Returns {contest_id: [row, ...]} from cache CSV.'''
    if not CACHE_PATH.exists():
        return {}
    by_contest: dict[int, list[dict]] = {}
    with open(CACHE_PATH, newline='') as f:
        for row in csv.DictReader(f):
            cid = int(row['contest_id'])
            by_contest.setdefault(cid, []).append(row)
    return by_contest


def save_cache(rows: list[dict]):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_header = not CACHE_PATH.exists()
    with open(CACHE_PATH, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def run_contest(contest_id: int) -> list[dict]:
    raw_json = json.loads((RC_DIR / f'{contest_id}.json').read_text())
    raw_json.sort(key=lambda x: x['rank'])

    data = load_contest(contest_id)                         # (trueOld, rank, trueDelta, handle)
    true_olds  = [r['trueOldRating'] for r in raw_json]
    old_ratings = [r['oldRating']     for r in raw_json]

    delta_list = [(t[0], t[1], t[2]) for t in data]
    _, _, engine_out = run_naive_engine(delta_list)

    rows = []
    for i, ((true_old, rank, actual_delta, handle), (seed, perf, dr, _, pred, _)) in enumerate(
            zip(data, engine_out)):
        rows.append({
            'contest_id':  contest_id,
            'handle':      handle,
            'rank':        rank,
            'old_rating':  old_ratings[i],
            'true_old':    true_old,
            'stage':       get_stage(true_old, old_ratings[i]),
            'pred_delta':  pred,
            'actual_delta': actual_delta,
            'error':       pred - actual_delta,
        })
    return rows


STAGE_KEYS = list(range(6)) + [7]   # 0,1,2,3,4,5 = ramp-up stages; 7 = old-sys


def summarise(contest_id: int, rows: list[dict], era: str) -> dict:
    n = len(rows)
    n_s0  = sum(1 for r in rows if int(r['stage']) == 0)
    n_s1p = sum(1 for r in rows if 0 < int(r['stage']) < 7)
    n_old = sum(1 for r in rows if int(r['stage']) == 7)

    sum_pred   = sum(int(r['pred_delta'])   for r in rows)
    sum_actual = sum(int(r['actual_delta']) for r in rows)

    result = {
        'contest_id':   contest_id,
        'era':          era,
        'n':            n,
        'n_s0':         n_s0,
        'n_s1plus':     n_s1p,
        'n_old':        n_old,
        'new_sys_frac': round((n_s0 + n_s1p) / n, 4),
        'sum_pred':     sum_pred,
        'sum_actual':   sum_actual,
        'sum_diff':     sum_pred - sum_actual,
        'mean_pred':    round(sum_pred / n, 3),
        'mean_actual':  round(sum_actual / n, 3),
        'mean_err':     round((sum_pred - sum_actual) / n, 3),
        # coarse-group means (kept for notebook cells 2-5)
        'mean_actual_s0':     round(sum(int(r['actual_delta']) for r in rows if int(r['stage']) == 0) / n_s0, 3) if n_s0 else None,
        'mean_actual_s1plus': round(sum(int(r['actual_delta']) for r in rows if 0 < int(r['stage']) < 7) / n_s1p, 3) if n_s1p else None,
        'mean_actual_old':    round(sum(int(r['actual_delta']) for r in rows if int(r['stage']) == 7) / n_old, 3) if n_old else None,
        'mean_pred_s0':       round(sum(int(r['pred_delta'])   for r in rows if int(r['stage']) == 0) / n_s0, 3) if n_s0 else None,
        'mean_pred_s1plus':   round(sum(int(r['pred_delta'])   for r in rows if 0 < int(r['stage']) < 7) / n_s1p, 3) if n_s1p else None,
        'mean_pred_old':      round(sum(int(r['pred_delta'])   for r in rows if int(r['stage']) == 7) / n_old, 3) if n_old else None,
    }

    # fine-grained per-stage breakdown (stages 0–5 and 7)
    for k in STAGE_KEYS:
        subset = [r for r in rows if int(r['stage']) == k]
        nk = len(subset)
        label = f'stage{k}' if k < 7 else 'old'
        result[f'n_{label}'] = nk
        if nk:
            sa = sum(int(r['actual_delta']) for r in subset)
            sp = sum(int(r['pred_delta'])   for r in subset)
            result[f'mean_actual_{label}'] = round(sa / nk, 3)
            result[f'mean_pred_{label}']   = round(sp / nk, 3)
            result[f'mean_err_{label}']    = round((sp - sa) / nk, 3)
        else:
            result[f'mean_actual_{label}'] = None
            result[f'mean_pred_{label}']   = None
            result[f'mean_err_{label}']    = None

    return result


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cache = load_cache()

    summary_rows = []
    all_new_rows: list[dict] = []

    contest_eras = (
        [(cid, 'old') for cid in OLD_ERA_CONTESTS] +
        [(cid, 'new') for cid in NEW_ERA_CONTESTS]
    )

    for contest_id, era in contest_eras:
        rc_path = RC_DIR / f'{contest_id}.json'
        if not rc_path.exists():
            logger.warning(f'Contest {contest_id}: data file missing, skipping')
            continue

        if contest_id in cache:
            logger.info(f'Contest {contest_id}: loaded from cache ({len(cache[contest_id])} rows)')
            rows = cache[contest_id]
        else:
            logger.info(f'Contest {contest_id}: running engine...')
            rows = run_contest(contest_id)
            all_new_rows.extend(rows)
            logger.info(f'Contest {contest_id}: done ({len(rows)} participants)')

        summary_rows.append(summarise(contest_id, rows, era))

    if all_new_rows:
        save_cache(all_new_rows)
        logger.info(f'Cached {len(all_new_rows)} new rows to {CACHE_PATH}')

    with open(SUMMARY_PATH, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=summary_rows[0].keys())
        writer.writeheader()
        writer.writerows(summary_rows)

    logger.info(f'Summary written to {SUMMARY_PATH}')

    stage_labels = [f's{k}' if k < 7 else 'old' for k in STAGE_KEYS]
    hdr_stages = ''.join(f"{lbl:>9}" for lbl in stage_labels)
    print('\n=== Deflation Summary — mean_err per stage ===')
    print(f"{'contest':>8} {'era':>4} {'n':>6} {'new%':>5} {'mean_err':>9}  " + hdr_stages)
    print('-' * (42 + 9 * len(STAGE_KEYS)))
    for r in summary_rows:
        stage_errs = ''
        for k in STAGE_KEYS:
            col = f'mean_err_stage{k}' if k < 7 else 'mean_err_old'
            val = r[col]
            stage_errs += f"{val:>+9.1f}" if val is not None else f"{'—':>9}"
        print(f"{r['contest_id']:>8} {r['era']:>4} {r['n']:>6} {100*r['new_sys_frac']:>4.0f}%"
              f" {r['mean_err']:>+9.2f}  {stage_errs}")


if __name__ == '__main__':
    main()
