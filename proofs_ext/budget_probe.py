"""Sample helper-search shards before committing to a full decision grid."""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from elf import read_puzzles
from prefix_bounds import available


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("puzzle_id")
    parser.add_argument("helpers", type=int)
    parser.add_argument("--binary", type=Path, default=ROOT / "work/proofs/exact_helpers.exe")
    parser.add_argument("--puzzles", type=Path, default=ROOT / "data/puzzles.csv")
    parser.add_argument("--submission", type=Path, default=ROOT / "improve/submission.csv")
    parser.add_argument("--cap", type=int, default=5_000_000, help="node limit per sampled shard")
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--cores", type=int, default=2, help="assumed parallel workers")
    parser.add_argument("--jobs", type=int, help="override the worker count for estimates and execution")
    parser.add_argument("--threshold", type=int, default=1_000_000_000,
                        help="skip the full grid above this estimated node count")
    parser.add_argument("--run", action="store_true", help="start the grid if the sample fits")
    args = parser.parse_args()
    workers = args.jobs if args.jobs is not None else args.cores
    if args.helpers < 0 or min(args.samples, args.cap, args.threshold, args.cores, workers) < 1:
        parser.error("helpers must be nonnegative and all budgets and worker counts must be positive")
    puzzle = next((p for p in read_puzzles(args.puzzles) if p.id == args.puzzle_id), None)
    if puzzle is None:
        parser.error(f"unknown puzzle {args.puzzle_id}")
    missing = len(set(puzzle.targets) - set(puzzle.seeds))
    shards = max(1, len(available(puzzle.seeds, set(puzzle.targets), puzzle.limit)))
    n = min(args.samples, shards)
    indices = [round(i * (shards - 1) / max(1, n - 1)) for i in range(n)]
    binary = args.binary.resolve()
    payload = (f"{puzzle.limit} {len(puzzle.seeds)} {len(puzzle.targets)} {args.helpers} {args.cap}\n"
               + " ".join(map(str, puzzle.seeds + puzzle.targets)) + "\n")
    print(f"{puzzle.id}: h{args.helpers}, {n}/{shards} shards sampled; "
          f"an exhaustive UNSAT grid would prove a lower bound of {missing + args.helpers + 1}", flush=True)
    counts = []
    capped = False
    start = time.perf_counter()
    for shard in indices:
        result = subprocess.run([str(binary), str(shard), str(shards)], input=payload,
                                text=True, capture_output=True, check=True)
        status, raw_nodes, _ = result.stdout.splitlines()[0].split()
        nodes = int(raw_nodes)
        print(f"  shard {shard}/{shards}: {status} {nodes:,} nodes", flush=True)
        if status == "FOUND":
            print("A witness was found within this helper budget.")
            return
        if status not in {"UNSAT", "UNKNOWN"}:
            raise ValueError(f"Unexpected shard status {status!r}")
        capped |= status == "UNKNOWN"
        counts.append(nodes)
    if capped:
        print("Indeterminate at this cap. Increase --cap before estimating the full grid.")
        return
    elapsed = time.perf_counter() - start
    mean_total = sum(counts) * shards / n
    high_estimate = max(counts) * shards
    workers = min(workers, shards)
    print(f"Sample estimates: {mean_total:,.0f} nodes by the mean, {high_estimate:,} by the maximum.")
    print(f"Estimated wall time on {workers} worker(s): {elapsed * shards / (n * workers * 60):.1f} min.")
    if high_estimate > args.threshold:
        print(f"Skipping full grid: sample estimate exceeds {args.threshold:,} nodes.")
        return
    print("The sample fits the budget; unsampled shards may take longer.", flush=True)
    if args.run:
        command = [sys.executable, "-B", str(ROOT / "proofs_ext/prove.py"), puzzle.id,
                   str(args.helpers), "--node-limit", str(max(args.cap, 2 * max(counts))),
                   "--jobs", str(workers), "--binary", str(binary),
                   "--puzzles", str(args.puzzles.resolve()), "--submission", str(args.submission.resolve())]
        subprocess.run(command, check=True, cwd=ROOT)


if __name__ == "__main__":
    main()
