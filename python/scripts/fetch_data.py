"""
Fetch contest list and rating changes from the Codeforces API.

Pulls all contests and their rating-change records, saving JSON to data/raw/.
Re-runs skip existing files unless is_forced=True is set in the calls below.
"""

import json

from fetch_cf_data import FetchCFData
from utils import get_logger

logger = get_logger(__name__)

collector = FetchCFData()
collector.get_contest_list(True)
logger.info("Finished collecting contest list.")

contest_ids = []
with open(collector.raw_dir / "contest_list.json", "r") as f:
    data = json.load(f)
    for obj in data:
        contest_ids.append(obj["id"])

for contest_id in contest_ids:
    try:
        collector.get_contest_rating_changes(str(contest_id), True)
    except RuntimeError as e:
        logger.warning(f"Skipping contest {contest_id}: {type(e).__name__} {e}")
    logger.info(f"Finished collecting rating changes for contest {contest_id}.")
