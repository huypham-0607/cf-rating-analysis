"""
Metric computation for engine validation.

generate_metric() writes per_participant.csv and per_contest.csv.
summarize_errors() returns a dict of aggregate statistics for any error sequence.
"""

import csv
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from utils import get_logger

logger = get_logger(__name__)


def summarize_errors(errors: Sequence[float]) -> dict[str, float]:
    """
    Compute aggregate error statistics for a sequence of signed errors.

    Parameters
    ----------
    errors : sequence of float
        Signed prediction errors (predicted - actual).

    Returns
    -------
    dict with keys: count, bias, mae, rmse, median_error,
    median_absolute_error, absolute_error_p75, absolute_error_p90,
    absolute_error_p95, exact_rate, within_one_rate, within_five_rate,
    within_ten_rate.
    """
    values = np.asarray(errors, dtype=float)
    if values.size == 0:
        raise ValueError("Cannot summarize an empty error sequence")

    absolute = np.abs(values)
    return {
        "count":                  int(values.size),
        "bias":                   float(np.mean(values)),
        "mae":                    float(np.mean(absolute)),
        "rmse":                   float(np.sqrt(np.mean(values ** 2))),
        "median_error":           float(np.median(values)),
        "median_absolute_error":  float(np.median(absolute)),
        "absolute_error_p75":     float(np.quantile(absolute, 0.75)),
        "absolute_error_p90":     float(np.quantile(absolute, 0.90)),
        "absolute_error_p95":     float(np.quantile(absolute, 0.95)),
        "exact_rate":             float(np.mean(absolute == 0)),
        "within_one_rate":        float(np.mean(absolute <= 1)),
        "within_five_rate":       float(np.mean(absolute <= 5)),
        "within_ten_rate":        float(np.mean(absolute <= 10)),
    }


def _save_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def generate_metric(data: list, out_dir: Path) -> tuple[list[dict], list[dict]]:
    """
    Write per_participant.csv and per_contest.csv from engine results.

    Parameters
    ----------
    data : list of (contest_id, time_ms, correction, delta_list)
        delta_list items: (rank, handle, old_rating, seed, perf,
                           pred_delta_raw, pred_delta, actual_delta)

    Returns
    -------
    (per_participant rows, per_contest rows)
    """
    per_participant: list[dict] = []
    per_contest: list[dict] = []

    for contest_id, time_ms, correction, delta_list in data:
        errors = []
        for rank, handle, old, seed, perf, delta_raw, pred, actual in delta_list:
            error     = pred - actual
            abs_error = abs(error)
            errors.append(error)
            per_participant.append({
                "contest_id":     contest_id,
                "rank":           rank,
                "handle":         handle,
                "old_rating":     old,
                "seed":           seed,
                "performance":    perf,
                "pred_delta_raw": delta_raw,
                "pred_delta":     pred,
                "actual_delta":   actual,
                "error":          error,
                "abs_error":      abs_error,
                "exact":          abs_error == 0,
                "within_1":       abs_error <= 1,
                "within_5":       abs_error <= 5,
            })

        stats = summarize_errors(errors)
        per_contest.append({
            "contest_id": contest_id,
            "n":          len(delta_list),
            "time_ms":    time_ms,
            "correction": correction,
            **stats,
        })

    _save_csv(per_participant, out_dir / "per_participant.csv")
    _save_csv(per_contest,     out_dir / "per_contest.csv")
    logger.info(
        f"Wrote {len(per_participant)} participant rows and "
        f"{len(per_contest)} contest rows to {out_dir}"
    )
    return per_participant, per_contest
