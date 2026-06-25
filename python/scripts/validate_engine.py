'''

'''

import sys

from validation.loader import load_contest
from validation.runner import run_naive_engine
from validation.metrics import generate_metric
from utils import get_logger,_load, PROJECT_ROOT
from pathlib import Path

FINAL_DIR = PROJECT_ROOT/"data"/"final"
VALIDATION_DIR = PROJECT_ROOT/"data"/"validation"
NAIVE_DIR = VALIDATION_DIR/"naive"


logger = get_logger(__name__)

contest_list = None
try:
    contest_list = _load(Path(PROJECT_ROOT/"data/cleaned/contest_list.json"))
except Exception as e:
    logger.error(f"Failed to get contest list. Error: {e}")
    sys.exit()

naive_raw_data = []
fft_raw_data = []

for contest in contest_list:
    if (contest["id"] < 2000 or contest["id"] >= 2010):
        continue
    delta_list = None
    try:
        delta_list = load_contest(contest["id"])
    except Exception as e:
        logger.warning(f"Failed to load contest id (error: {e}) {contest["id"]}, skipping...")
        continue

    logger.info(f"Executing for contest id: {contest["id"]}")
    naive_result = run_naive_engine(delta_list)

    naive_merged = [(rank, old, delta_final, actual)
              for (old, rank, actual), (_,_,_,_,delta_final,_) in zip(delta_list, naive_result[1])]
    
    naive_raw_data.append((contest["id"], naive_result[0], naive_merged))

if naive_raw_data:
    generate_metric(naive_raw_data, NAIVE_DIR)
else:
    logger.warning(f"No data found!")



