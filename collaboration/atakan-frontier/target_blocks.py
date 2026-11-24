"""Benchmark the pinned Atakan multi-output search on current programs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from elf import check, read_puzzles, read_submission, sha256, write_submission


PROFILES = ((2, 10, 8, 4, 64, 0), (3, 14, 10, 4, 64, 1))


def compare(task):
    puzzle, old, engine, timeout = task
    values = (puzzle.id, puzzle.limit, len(puzzle.seeds), len(puzzle.targets), len(old),
              *puzzle.seeds, *puzzle.targets)
    header = " ".join(map(str, values))
    tape = "\n".join(" ".join(map(str, op)) for op in old)
    wire = f"{header}\n{tape}\n"
    best = old
    arms = []
    for profile in PROFILES:
        try:
            proc = subprocess.run([str(engine), *map(str, profile)], input=wire, check=True,
                                  text=True, capture_output=True, timeout=timeout,
                                  creationflags=getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0))
        except subprocess.TimeoutExpired:
            arms.append({"status": "timeout"})
            continue
        summary, *instructions = proc.stdout.splitlines()
        identifier, width, accepted = summary.split()
        assembled = []
        for line in instructions:
            op, left, right, destination = line.split()
            assembled.append((op, int(left), int(right), int(destination)))
        candidate = tuple(assembled)
        if identifier != puzzle.id or check(puzzle, candidate) != int(width):
            raise ValueError(f"Engine produced an invalid result for {puzzle.id}")
        arms.append({"length": len(candidate), "accepted": int(accepted)})
        best = min((best, candidate), key=len)
    return puzzle.id, best, {"before": len(old), "after": len(best), "arms": arms}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for field in ("puzzles", "parent", "engine", "source", "out"):
        cli.add_argument("--" + field, type=Path, required=True)
    for field, default in (("count", 48), ("offset", 0), ("jobs", 6), ("timeout", 20)):
        cli.add_argument("--" + field, type=int, default=default)
    args = cli.parse_args()
    puzzles = read_puzzles(args.puzzles)
    parent = read_submission(args.parent)
    eligible = sorted((p for p in puzzles if 90 <= len(parent[p.id]) <= 220 and 12 <= len(p.targets) <= 63
                       and p.registers == 48 and p.limit < 2**62),
                      key=lambda p: hashlib.sha256(("target-block-239-" + p.id).encode()).digest())
    selected = eligible[args.offset:args.offset+args.count]
    rows, wins = {}, {}
    jobs = [(p, parent[p.id], args.engine.resolve(strict=True), args.timeout) for p in selected]
    with ThreadPoolExecutor(args.jobs) as pool:
        for i, tape, result in pool.map(compare, jobs):
            rows[i] = result
            if len(tape) < len(parent[i]):
                wins[i] = tape
                print(i, len(parent[i]), len(tape), flush=True)
    args.out.mkdir(exist_ok=True, parents=True)
    write_submission(args.out/"wins.csv", [p for p in puzzles if p.id in wins], wins)
    record = dict(parent_sha256=sha256(args.parent), engine_sha256=sha256(args.engine),
                  source=json.loads(args.source.read_bytes()), profiles=PROFILES, timeout=args.timeout, rows=rows)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(record, separators=(",", ":")).encode(), mtime=0))
    print(len(rows), len(wins), sum(rows[i]["before"]-len(tape) for i,tape in wins.items()), flush=True)


if __name__ == "__main__":
    main()
