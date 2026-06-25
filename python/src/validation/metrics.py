'''
    Takes data from loader.py & runner.py and return a list of metrics

    input: data - list of the following format
    
    [
     (id, time, [
                 (rank_1, old_rating_1, pred_delta_1, actual_delta_1),
                 ...
                ]
     ),
     ...
    ]

    return value: tuple of 2 lists - (per_participant, per_contest)

    per_participant: [(handle, contest_id, rank, old_rating, pred_delta,
                       actual_delta, error, abs_error, exact, within_1, within_5)...]
    per_contest: [(id, n, time_ms),...]
    
'''

import csv

from pathlib import Path
from utils import get_logger, _load, PROJECT_ROOT


def save_csv(rows: list[dict], path: Path):
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

def generate_metric(data: list, dir: Path):
    per_participant = []
    per_contest = []

    for contest_id, time_ms, delta_list in data:
        n_participants = len(delta_list)
        per_contest.append({
            "id": contest_id,
            "n": n_participants,
            "time_ms": time_ms
        })
        for rank, old, pred, actual in delta_list:
            error = pred - actual
            abs_error = abs(error)
            exact = abs_error == 0
            within_1 = abs_error <= 1
            within_5 = abs_error <= 5

            per_participant.append({
                "contest_id": contest_id,
                "rank": rank,
                "old_rating": old,
                "pred_delta": pred,
                "actual_delta": actual,
                "error": error,
                "abs_error": abs_error,
                "exact": exact,
                "within_1": within_1,
                "within_5": within_5,
            })
    
    Path.mkdir(dir, exist_ok=True, parents=True)
    save_csv(per_participant,dir/"per_participant.csv")
    save_csv(per_contest,dir/"per_contest.csv")

    return per_participant, per_contest

        

