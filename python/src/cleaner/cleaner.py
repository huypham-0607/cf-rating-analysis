'''
    Clean data pulled from codeforces
'''
import json
import logging
import sys 

from utils import get_logger
from pathlib import Path

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
RAW_DATA = PROJECT_ROOT/"data/raw"
CLEANED_DATA = PROJECT_ROOT/"data/cleaned"

class DataCleaner:
    def __init__(self)->None:
        Path(CLEANED_DATA).mkdir(parents=True, exist_ok=True)
        Path(CLEANED_DATA/"rating_changes").mkdir(parents=True, exist_ok=True)
    
    def clean_contest_data(self, is_forced:bool = False)->None:
        if not is_forced and Path(CLEANED_DATA/"contest_list.json").exists():
            return
        data = []
        contest_list = []
        try:
            with open(RAW_DATA/"contest_list.json",'r') as f:
                data = json.load(f)
                logger.info(f"Loaded contest list from {Path(f.name).resolve()}")
        except PermissionError as e:
            raise e
        except FileNotFoundError as e:
            raise e

        dup_count = 0;

        data.sort(key=lambda x : x["id"])
        for obj in data:
            if len(contest_list) and obj["id"] == contest_list[-1]["id"]:
                logger.warning(f"Duplicate contest record for id {obj["id"]} detected.")
                dup_count += 1
                continue
            contest_list.append(obj)

        logger.info(f"Eliminated {dup_count} invalid contest record.")

        DataCleaner._save(Path(CLEANED_DATA/"contest_list.json"),contest_list)

    
    def clean_rating_change_data(self, is_forced:bool = False)->None:
        contest_list = DataCleaner._load(Path(CLEANED_DATA/"contest_list.json"))

        invalid_record_count = 0
        cleaned_contest = 0

        for contest in contest_list:
            cleaned_dir = Path(CLEANED_DATA/"rating_changes"/(str(contest["id"])+".json"))
            raw_dir = Path(RAW_DATA/"rating_changes"/(str(contest["id"])+".json"))

            if not is_forced and cleaned_dir.exists():
                continue;

            data = []
            try:
                data = DataCleaner._load(raw_dir)
            except FileNotFoundError as e:
                # logger.warning(f"Rating changes for contest {contest["id"]} not found.")
                continue
            except PermissionError as e:
                logger.warning(f"Read access denied for {raw_dir}")
                continue

            handles = set()
            rating_changes = []
            dup_count = 0
            for rating_change in data:
                handle = rating_change["handle"]
                if handle in handles:
                    dup_count += 1
                    logger.warning(f"Duplicate rating change record for handle {handle} from contest {contest["id"]}.")
                else:
                    handles.add(handle)
                    rating_changes.append(rating_change)

            DataCleaner._save(cleaned_dir,rating_changes)
            if (dup_count):
                logger.info(f"Removed {dup_count} duplicate records from contest {contest["id"]}.")
            cleaned_contest += 1
            invalid_record_count += dup_count

        logger.info(f"Cleaned and Saved {cleaned_contest} contests.")
        logger.info(f"Removed {invalid_record_count} invalid records from all cleaned contests.")


    def create_and_validate_delta_hist(self, is_forced:bool = False)->None:
        delta_hist = {}
        init_rating = {}
        
        # If forced or file doesn't exist, then create new delta_hist.json
        if is_forced or not Path(CLEANED_DATA/"delta_hist.json").exists():
            contest_list = DataCleaner._load(Path(CLEANED_DATA)/"contest_list.json")
            contest_list.sort(key=lambda x: x["startTimeSeconds"])

            for contest in contest_list:
                rating_changes = []
                dir = Path(CLEANED_DATA/"rating_changes"/(str(contest["id"])+".json"))
                try:
                    rating_changes = DataCleaner._load(dir)
                    logger.info(f"Loaded rating changes for contest{contest["id"]}.")
                except FileNotFoundError as e:
                    # logger.warning(f"Rating changes for contest {contest["id"]} not found.")
                    pass
                except PermissionError as e:
                    logger.warning(f"Read access denied for {dir}")

                for rating_change in rating_changes:
                    handle = rating_change["handle"]
                    if (handle not in delta_hist):
                        delta_hist[handle] = []
                        init_rating[handle] = rating_change["oldRating"]
                    delta_hist[handle].append({
                        "contest_id": rating_change["contestId"],
                        "rank": rating_change["rank"],
                        "old_rating": rating_change["oldRating"],
                        "new_rating": rating_change["newRating"]
                    })
            try:
                with open(Path(CLEANED_DATA/"delta_hist.json"),'w') as f:
                    f.write(json.dumps(delta_hist))
                with open(Path(CLEANED_DATA/"init_rating.json"),'w') as f:
                    f.write(json.dumps(init_rating))
            except Exception as e:
                raise e
        else:
            try:
                with open(Path(CLEANED_DATA/"delta_hist.json"),'r') as f:
                    delta_hist = json.load(f)
                    logger.info(f"Loaded {Path(f.name).resolve()}")
                with open(Path(CLEANED_DATA/"init_rating.json"),'r') as f:
                    init_rating = json.load(f)
                    logger.info(f"Loaded {Path(f.name).resolve()}")
            except Exception as e:
                raise e
            
        # Analyze rating discrepancy for each user
        for key, value in delta_hist.items():
            flag = False
            if (init_rating[key] != 0 and init_rating[key] != 1500):
                logger.warning(f"Initial rating discrepancy for handle {key}")
                flag = True
            if (init_rating[key] != value[0]["old_rating"]):
                logger.warning(f"Rating discrepancy between contest {-1} and contest {0} for handle {key}.\nExpected {0} or {1500}, found {value[0]["old_rating"]}")
                flag = True
            for i in range(1,len(value)):
                if (value[i-1]["new_rating"] != value[i]["old_rating"]):
                    logger.warning(f"Rating discrepancy between contest {i-1} and contest {i} for handle {key}.\nExpected {value[i-1]["new_rating"]}, found {value[i]["old_rating"]}")
                    flag = True
            if (flag):
                message = f"Rating history for {key}:\n"
                for i in range(0,len(value)):
                    message += f"{i}: Contest {value[i]["contest_id"]} - Old: {value[i]["old_rating"]} | New: {value[i]["new_rating"]}\n"
                logger.info(message)
        logger.info(f"Total handles: {len(delta_hist)}")
        
    @staticmethod
    def _load(dir: Path)->list:
        try:
            with open(dir,'r') as f:
                data = json.load(f)
                return data
        except PermissionError as e:
            raise e
        except IsADirectoryError as e:
            raise e
        except FileNotFoundError as e:
            raise e


    @staticmethod
    def _save(dir: Path, data: list)->None:
        try:
            with open(dir,'w') as f:
                f.write(json.dumps(data))
        except PermissionError:
            raise RuntimeError("Write Failed: No write permission.")
        except FileNotFoundError:
            raise RuntimeError("Write Failed: File not found.")
        except IsADirectoryError:
            raise RuntimeError("Write Failed: Invalid Directory.")