import json

from fetch_cf_data import FetchCFData
from utils import get_logger

logger = get_logger(__name__)

collector = FetchCFData()
collector.get_contest_list()
logger.info(f"Finished collecting contest list.")

contest_ids = [];

with open(collector.raw_dir/"contest_list.json",'r') as f:
    data = json.load(f)
    for obj in data:
        contest_ids.append(obj["id"])

for id in contest_ids:
    if (id <= 600):
        logger.warning(f"Skipping contest: Contest too old")
        continue
    try:
        collector.get_contest_rating_changes(str(id))
    except RuntimeError as e:
        logger.warning(f"Skipping contest: {type(e).__name__} {e}")
    logger.info(f"Finished collecting rating changes for contest id {id}.")