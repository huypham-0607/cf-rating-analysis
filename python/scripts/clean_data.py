"""
Clean raw data pulled from Codeforces API.

Runs all cleaning steps in sequence: contest list, rating changes, delta
history validation, and trueRating annotation.
"""

from cleaner import DataCleaner
from utils import get_logger

logger = get_logger(__name__)

cleaner = DataCleaner()

cleaner.clean_contest_data(True)
logger.info("Finished cleaning contest_list data.")
cleaner.clean_rating_change_data(True)
logger.info("Finished cleaning rating_change data.")
cleaner.create_and_validate_delta_hist(True)
logger.info("Finished validating delta_history.")
cleaner.add_contest_true_rating()
logger.info("Finished adding trueRating to all contest rating changes.")
