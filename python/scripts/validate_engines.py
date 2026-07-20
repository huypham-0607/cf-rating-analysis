"""
Run validation against cached contest data and write error metrics.

Usage
-----
# Validate specific contests with the naive engine:
  uv run python python/scripts/validate_engines.py --engine naive --contests 1000 1585 2000

# Validate all cached deflation contests with naive:
  uv run python python/scripts/validate_engines.py --engine naive --all-cached

# Validate with fft engine:
  uv run python python/scripts/validate_engines.py --engine fft --all-cached

Output
------
  data/validation/naive/per_participant.csv   (or fft/)
  data/validation/naive/per_contest.csv
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import get_logger, PROJECT_ROOT
from validation.loader import load_contest
from validation.runner import run_engine
from validation.metrics import generate_metric

CACHED_CONTESTS = [1000, 1100, 1200, 1300, 1400, 1500, 1585, 2000, 2050, 2130, 2200, 2234]
RC_DIR = PROJECT_ROOT / "data" / "final" / "rating_changes"

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate engine against CF rating data")
    p.add_argument("--engine", choices=["naive", "fft"], default="naive",
                   help="Which compiled engine to use (default: naive)")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--contests", type=int, nargs="+", metavar="ID",
                       help="Contest IDs to validate")
    group.add_argument("--all-cached", action="store_true",
                       help="Validate all deflation-cached contests")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    contest_ids = CACHED_CONTESTS if args.all_cached else args.contests

    out_dir = PROJECT_ROOT / "data" / "validation" / args.engine
    raw_data = []
    skipped = 0

    for cid in contest_ids:
        rc_path = RC_DIR / f"{cid}.json"
        if not rc_path.exists():
            logger.warning(f"Contest {cid}: data file missing, skipping")
            skipped += 1
            continue

        try:
            data = load_contest(cid)
        except Exception as exc:
            logger.warning(f"Contest {cid}: load failed ({exc}), skipping")
            skipped += 1
            continue

        delta_list = [(t[0], t[1], t[2]) for t in data]
        handles    = [t[3] for t in data]

        logger.info(f"Contest {cid}: running {args.engine} engine on {len(delta_list)} participants…")
        try:
            runtime_ms, correction, engine_out = run_engine(args.engine, delta_list)
        except Exception as exc:
            logger.error(f"Contest {cid}: engine failed ({exc}), skipping")
            skipped += 1
            continue

        merged = [
            (rank, handle, old, seed, perf, delta_raw, delta_final, actual)
            for (old, rank, actual), (seed, perf, delta_raw, _, delta_final, _), handle
            in zip(delta_list, engine_out, handles)
        ]
        raw_data.append((cid, runtime_ms, correction, merged))
        logger.info(f"Contest {cid}: done — {runtime_ms:.1f} ms, correction={correction}")

    if not raw_data:
        logger.error("No contests processed successfully.")
        sys.exit(1)

    generate_metric(raw_data, out_dir)
    logger.info(f"Results written to {out_dir}/")
    if skipped:
        logger.warning(f"{skipped} contest(s) skipped.")


if __name__ == "__main__":
    main()
