'''
    Load and curate data to feed to rating engine.
    Filter out contests with Id < 600 (Old contests uses different rating logic)
    
    Takes input as list[tuple[int,int,int]] in format of loader.py output
    
    Output a tuple of [int,list] of following format:
    
    (time, [
        seed, perf, delta_raw, delta_adj, delta_final, new_rating
    ])
'''

import json
import subprocess

from pathlib import Path
from utils import get_logger, _load, PROJECT_ROOT

DATA_PATH = PROJECT_ROOT/"data/final"

logger = get_logger(__name__)

def run_naive_engine(delta_list: list[tuple[int,int,int]])-> tuple[float,int,list]:
    # Parse string to pass into subprocess
    lines = [str(len(delta_list))]
    for rating,  rank, _ in delta_list:
        lines.append(f"{rating} {rank}")
    formatted_input = "\n".join(lines)

    result = None
    try:
        result = subprocess.run([str(Path(PROJECT_ROOT/"cpp/build/naive"))],
                                capture_output=True,
                                text=True,
                                check=True,
                                input=formatted_input)
    except subprocess.CalledProcessError as e:
        logger.error(f"naive failed (exit {e.returncode}): {e.stderr}")
        raise e

    logger.info(result.stderr.strip())
    # Parse output created by subprocess.
    lines = result.stdout.strip().split("\n")
    engine_result = []
    for line in lines:
        seed, perf, delta_raw, delta_adj, delta_final, new_rating = line.split()
        seed = float(seed)
        perf = int(perf)
        delta_raw = float(delta_raw)
        delta_adj = float(delta_adj)
        delta_final = int(delta_final)
        new_rating = int(new_rating)
        engine_result.append((seed,perf,delta_raw,delta_adj,delta_final,new_rating));

    exec_time, offset = result.stderr.strip().split(" ")
    exec_time = float(exec_time)
    offset = int(offset)

    return exec_time,offset,engine_result





    

    
    
