"""
Produce error-metric reports and the ramp-stage chart from cached validation data.

Reads:
  data/validation/naive/per_participant.csv
  data/validation/deflation/per_participant.csv  (for stage labels)

Writes:
  results/error_metrics.csv    — overall + per-contest signed/absolute metrics
  results/grouped_metrics.csv  — metrics grouped by ramp-up stage
  img/error_by_ramp_stage.png  — bar chart of mean error per stage

Usage
-----
  uv run python python/scripts/analyze_errors.py
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import PROJECT_ROOT
from validation.metrics import summarize_errors

NAIVE_PP   = PROJECT_ROOT / "data" / "validation" / "naive"    / "per_participant.csv"
DEFL_PP    = PROJECT_ROOT / "data" / "validation" / "deflation" / "per_participant.csv"
RESULTS    = PROJECT_ROOT / "results"
IMG        = PROJECT_ROOT / "img"

STAGE_LABELS = {0: "s1", 1: "s2", 2: "s3", 3: "s4", 4: "s5", 5: "s6", 7: "old"}
OFFSETS      = {0: 1400, 1: 900, 2: 550, 3: 300, 4: 150, 5: 50, 7: 0}

# ── Contests used in the new-system analysis (mix of old/new era) ──────────────
OLD_ERA = {1000, 1100, 1200, 1300, 1500}            # pure old-sys
NEW_ERA = {1400, 1585, 2000, 2050, 2130, 2200, 2234} # mixed new-sys


def load_data() -> pd.DataFrame:
    if not NAIVE_PP.exists():
        print(f"ERROR: {NAIVE_PP} not found. Run validate_engines.py first.")
        sys.exit(1)

    pp = pd.read_csv(NAIVE_PP)

    # Attach stage from deflation cache if available
    if DEFL_PP.exists():
        defl = pd.read_csv(DEFL_PP)[["contest_id", "handle", "stage"]]
        pp = pp.merge(defl, on=["contest_id", "handle"], how="left")
        pp["stage"] = pp["stage"].fillna(-1).astype(int)
    else:
        pp["stage"] = -1

    return pp


def write_error_metrics(pp: pd.DataFrame) -> None:
    rows = []

    # Overall
    stats = summarize_errors(pp["error"].tolist())
    rows.append({"scope": "overall", "contest_id": "all",
                 "era": "all", **stats})

    # Per contest
    era_map = {c: "old" for c in OLD_ERA}
    era_map.update({c: "new" for c in NEW_ERA})
    for cid, grp in pp.groupby("contest_id"):
        stats = summarize_errors(grp["error"].tolist())
        rows.append({"scope": "per-contest", "contest_id": int(cid),
                     "era": era_map.get(int(cid), "?"), **stats})

    df = pd.DataFrame(rows)
    RESULTS.mkdir(parents=True, exist_ok=True)
    df.to_csv(RESULTS / "error_metrics.csv", index=False)
    print(f"Wrote {len(df)} rows → results/error_metrics.csv")


def write_grouped_metrics(pp: pd.DataFrame) -> None:
    """Group by ramp-up stage; uses only contests with new-sys participants."""
    rows = []

    # Overall across all stages
    for stage, label in STAGE_LABELS.items():
        grp = pp[pp["stage"] == stage]
        if grp.empty:
            continue
        stats = summarize_errors(grp["error"].tolist())
        rows.append({"group": "stage", "label": label,
                     "stage_key": stage, "offset": OFFSETS[stage], **stats})

    # Rating bucket (5 broad bins)
    bins   = [0, 1200, 1600, 2000, 2400, 9999]
    labels = ["<1200", "1200–1599", "1600–1999", "2000–2399", "≥2400"]
    pp["rating_bin"] = pd.cut(pp["old_rating"], bins=bins, labels=labels, right=False)
    for label, grp in pp.groupby("rating_bin", observed=True):
        if grp.empty:
            continue
        stats = summarize_errors(grp["error"].tolist())
        rows.append({"group": "rating_bucket", "label": str(label),
                     "stage_key": None, "offset": None, **stats})

    df = pd.DataFrame(rows)
    RESULTS.mkdir(parents=True, exist_ok=True)
    df.to_csv(RESULTS / "grouped_metrics.csv", index=False)
    print(f"Wrote {len(df)} rows → results/grouped_metrics.csv")
    return df


def plot_stage_error(grouped: pd.DataFrame) -> None:
    stage_df = (grouped[grouped["group"] == "stage"]
                .sort_values("offset", ascending=False))

    fig, ax = plt.subplots(figsize=(9, 4))
    x = np.arange(len(stage_df))
    bars = ax.bar(x, stage_df["bias"], color="steelblue", alpha=0.8,
                  label="Signed bias (mean error)")
    ax.bar(x, stage_df["mae"], bottom=0, color="none",
           edgecolor="tomato", linewidth=1.5, linestyle="--",
           label="MAE")

    ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax.set_xticks(x)
    ax.set_xticklabels(
        [f"{row['label']}\n(+{int(row['offset'])})" for _, row in stage_df.iterrows()],
        fontsize=9)
    ax.set_ylabel("Rating points")
    ax.set_title("Prediction Error by Ramp-up Stage (all mixed-era contests)",
                 fontsize=11, fontweight="bold")
    ax.legend(fontsize=9)

    for bar, val in zip(bars, stage_df["bias"]):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.3,
                f"{val:+.1f}", ha="center", va="bottom", fontsize=8)

    IMG.mkdir(parents=True, exist_ok=True)
    path = IMG / "error_by_ramp_stage.png"
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Wrote → img/error_by_ramp_stage.png")


def print_summary(pp: pd.DataFrame) -> None:
    stats = summarize_errors(pp["error"].tolist())
    print("\n=== Overall error metrics ===")
    for k, v in stats.items():
        if isinstance(v, float):
            print(f"  {k:<30} {v:+.3f}")
        else:
            print(f"  {k:<30} {v}")


def main() -> None:
    pp = load_data()
    print(f"Loaded {len(pp)} participant rows from {pp['contest_id'].nunique()} contests")
    print_summary(pp)
    write_error_metrics(pp)
    grouped = write_grouped_metrics(pp)
    plot_stage_error(grouped)


if __name__ == "__main__":
    main()
