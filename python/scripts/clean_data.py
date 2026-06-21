'''
    Clean data pulled from codeforces
'''
import json
import logging
import sys 

from cleaner import DataCleaner
from utils import get_logger
from pathlib import Path

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
RAW_DATA = PROJECT_ROOT/"data/raw"
PROCESSED_DATA = PROJECT_ROOT/"data/processed"

cleaner = DataCleaner()

cleaner.clean_contest_data(False)
logger.info(f"Finished cleaning contest_list data.")
cleaner.clean_rating_change_data(False)
logger.info(f"Finished cleaning rating_change data.")
cleaner.create_and_validate_delta_hist(False)
logger.info(f"Finished validating delta_history.")
