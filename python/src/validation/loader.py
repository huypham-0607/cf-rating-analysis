"""
Load contest rating-change data and format it for the engine runner.

Returns a list of (trueOldRating, rank, actual_delta, handle) tuples
read from data/final/rating_changes/<contest_id>.json.
"""

from pathlib import Path
from utils import get_logger, _load, PROJECT_ROOT

DATA_PATH = PROJECT_ROOT / "data" / "final" / "rating_changes"

logger = get_logger(__name__)


def load_contest(contest_id: int) -> list[tuple[int, int, int, str]]:
    """Return [(trueOldRating, rank, actual_delta, handle), ...] for a contest."""
    rating_changes = _load(DATA_PATH / f"{contest_id}.json")
    logger.info(f"Loaded {len(rating_changes)} rating changes for contest {contest_id}")
    return [
        (
            rc["trueOldRating"],
            rc["rank"],
            rc["trueNewRating"] - rc["trueOldRating"],
            rc["handle"],
        )
        for rc in rating_changes
    ]
