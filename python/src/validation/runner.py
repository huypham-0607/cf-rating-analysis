"""
Run a compiled rating engine (naive or fft) on a list of (rating, rank, delta) tuples.

The engine binary is invoked as a subprocess using the shared stdin/stdout protocol:
  stdin:  n\\nrating_1 rank_1\\n...\\nrating_n rank_n
  stdout: seed perf raw_delta adj_delta final_delta new_rating  (one line per participant)
  stderr: runtime_ms correction_offset
"""

import subprocess
from pathlib import Path
from utils import PROJECT_ROOT

_BINARY_DIR = PROJECT_ROOT / "cpp" / "build"
_VALID_ENGINES = {"naive", "fft"}


def run_engine(engine: str, delta_list: list[tuple[int, int, int]]) -> tuple[float, int, list]:
    """
    Run the specified engine on delta_list.

    Parameters
    ----------
    engine : str
        "naive" or "fft"
    delta_list : list of (true_old_rating, rank, actual_delta)

    Returns
    -------
    (runtime_ms, correction_offset, results)
    results : list of (seed, perf, raw_delta, adj_delta, final_delta, new_rating)
    """
    if engine not in _VALID_ENGINES:
        raise ValueError(f"Unknown engine '{engine}'. Valid options: {_VALID_ENGINES}")

    binary = _BINARY_DIR / engine
    if not binary.exists():
        raise FileNotFoundError(
            f"Engine binary not found: {binary}\n"
            f"Build with: cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release && cmake --build cpp/build -j"
        )

    n = len(delta_list)
    lines = [str(n)]
    for rating, rank, _ in delta_list:
        lines.append(f"{rating} {rank}")
    input_text = "\n".join(lines)

    result = subprocess.run(
        [str(binary)],
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Engine '{engine}' failed (exit {result.returncode}):\n{result.stderr}"
        )

    output_lines = result.stdout.strip().split("\n")
    if len(output_lines) != n:
        raise RuntimeError(
            f"Engine '{engine}' returned {len(output_lines)} rows for {n} participants"
        )

    parsed = []
    for row_idx, line in enumerate(output_lines):
        parts = line.split()
        if len(parts) != 6:
            raise RuntimeError(
                f"Engine '{engine}' row {row_idx}: expected 6 fields, got {len(parts)}: {line!r}"
            )
        try:
            parsed.append((
                float(parts[0]),   # seed
                int(parts[1]),     # perf
                float(parts[2]),   # raw_delta
                float(parts[3]),   # adj_delta
                int(parts[4]),     # final_delta
                int(parts[5]),     # new_rating
            ))
        except ValueError as exc:
            raise RuntimeError(
                f"Engine '{engine}' row {row_idx}: parse error: {exc}: {line!r}"
            ) from exc

    stderr_parts = result.stderr.strip().split()
    if len(stderr_parts) < 2:
        raise RuntimeError(f"Engine '{engine}': unexpected stderr: {result.stderr!r}")
    runtime_ms = float(stderr_parts[0])
    correction  = int(stderr_parts[1])

    return runtime_ms, correction, parsed


def run_naive_engine(delta_list: list[tuple[int, int, int]]) -> tuple[float, int, list]:
    return run_engine("naive", delta_list)


def run_fft_engine(delta_list: list[tuple[int, int, int]]) -> tuple[float, int, list]:
    return run_engine("fft", delta_list)
