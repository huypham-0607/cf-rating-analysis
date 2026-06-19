"""
    Fetch contest data from Codeforces and store it json format.

    Fetches data from two endpoints:
    - api/contest.list
    - api/contest.ratingChanges

    Store in data/raw in json format.

    From Codeforces API website:
    
    "Each method call returns a JSON-object with three possible fields: status, comment and result.
        - Status is either "OK" or "FAILED".
        - If status is "FAILED" then comment contains the reason why the request failed.
        - If status is "OK", then there is no comment.
        - If status is "OK" then result contains method-dependent JSON-element which
          will be described for each method separately. If status is "FAILED", then there
          is no result.

    Contest object: https://codeforces.com/apiHelp/objects#Contest
"""

import requests
import json
import time
import logging
from utils import get_logger

logger = logging.getLogger(__name__)

from pathlib import Path

BASE_URL = "https://codeforces.com/api/"
CONTEST_LIST_SUFFIX = "contest.list"
CONTEST_RATING_CHANGE_SUFFIX = "contest.ratingChanges"
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

class FetchCFData:
    def __init__(self):
        # timeout is the value (in seconds) client waits for server response.
        self.timeout: float = 5.0

        # backoff_base is the initial backoff delay if fetch failed.
        # backoff_inc is the value backoff delay increments by after failing.
        self.backoff_base: float = 2.0
        self.backoff_inc: float = 2.0

        # max_retries is maximum no of retries if fetch failed.
        self.max_retries: int = 3

        # Destination for fetched JSON data 
        self.raw_dir = Path(PROJECT_ROOT/"data/raw")
        self.raw_rating_changes_dir = Path(self.raw_dir/"rating_changes")

        # parents=True creates all parent directory not exist yet.
        # exist_ok=True prevents crashing when directory already exist.
        Path(PROJECT_ROOT/self.raw_dir).mkdir(parents=True, exist_ok=True)

    def get_contest_list(self, is_forced: bool = False):
        if (not is_forced and Path(self.raw_dir/"contest_list.json").exists()):
            return
        
        endpoint = BASE_URL + CONTEST_LIST_SUFFIX
        data = self._get(endpoint)
        logger.info(f"Fetched {len(data)} contests data from {endpoint}.")
        
        dir = self.raw_dir/"contest_list.json"
        self._save(dir, data)
        logger.info(f"Saved contests data to {dir}.")

        
    def get_contest_rating_changes(self, contest_id: str, is_forced: bool = False):
        self.raw_rating_changes_dir.mkdir(parents=True, exist_ok=True)
        if (not is_forced and Path(self.raw_rating_changes_dir/Path(contest_id+".json")).exists()):
            return
        
        endpoint = BASE_URL + CONTEST_RATING_CHANGE_SUFFIX + "?contestId=" + contest_id;
        data = self._get(endpoint)
        logger.info(f"Fetched {len(data)} rating changes for contest {contest_id} from {endpoint}.")
        
        dir = self.raw_rating_changes_dir/Path(contest_id+".json");
        self._save(dir,data)
        logger.info(f"Saved rating changes for contest {contest_id} to {dir}.")


    def _get(self, endpoint: str, **kwargs)->list:
        for i in range (self.max_retries):
            logger.info(f"Attemping to fetch from {endpoint}, attempt {i}")
            # request can fail in two different ways
            # - requests.get itself raises an exception
            # - JSON status code is "FAILED"
            try:
                response = requests.get(endpoint, params=kwargs, timeout = self.timeout)
                response.raise_for_status()
                data = response.json()
                if (data["status"] == "OK"):
                    return data["result"]
                logger.warning(f"Fetch failed: Endpoint returned data with status FAILED.\n Comment: {data["comment"]}")
                # If not then it is Codeforces-level exception, retry.
            except requests.HTTPError as e:
                if e.response is not None and 400 <= e.response.status_code < 500:
                    raise RuntimeError(f"Failed to fetch data: {type(e).__name__} {e}.")
                logger.warning(f"Fetch failed: {type(e).__name__} {e}")
                pass
            except requests.RequestException as e:
                # requests.RequestException encapsulates all other possible exceptions
                # related to requests
                logger.warning(f"Fetch failed: {type(e).__name__} {e}")
                pass
            if (i < self.max_retries-1):
                time.sleep(self.backoff_base + self.backoff_inc * i)
        raise RuntimeError(f"Failed to fetch data: All {self.max_retries} attempts exhausted.")
    
    def _save(self, dir: Path, data: list):
        try:
            with open(dir,'w') as f:
                f.write(json.dumps(data))
        except PermissionError:
            raise RuntimeError("Write Failed: No write permission.")
        except FileNotFoundError:
            raise RuntimeError("Write Failed: File not found.")
        except IsADirectoryError:
            raise RuntimeError("Write Failed: Invalid Directory.")

            



