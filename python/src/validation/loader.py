'''
    Load and curate data to feed to rating engine.
    Filter out contests with Id < 600 (Old contests uses different rating logic)
    Output a list of (old_rating, rank, actual_delta) tuple
'''

import json

from pathlib import Path
from utils import get_logger, _load, PROJECT_ROOT

DATA_PATH = PROJECT_ROOT/"data/final/rating_changes"

logger = get_logger(__name__)

def load_contest(contest_id: int) -> list[tuple[int,int,int]]:
    rating_changes = []
    try:
        rating_changes = _load(DATA_PATH/f"{contest_id}.json")
    except Exception as e:
        raise e
    
    logger.info(f"Fetched rating changes for id: {contest_id}")
    
    delta_list: list[tuple[int,int,int]] = []

    for rating_change in rating_changes:
        delta_list.append((rating_change["trueOldRating"],
                           rating_change["rank"],
                           rating_change["trueNewRating"] - rating_change["trueOldRating"]))

    logger.info(f"rating changes count: {len(delta_list)}")

    return delta_list