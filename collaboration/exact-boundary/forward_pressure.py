"""Search whole short programs by pricing helpers that unlock several missing targets."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from itertools import combinations
import gzip
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from elf import check, read_puzzles, read_submission, replay, sha256, write_submission
from tiny import encode
from graph import active_graph, first_recipes


def plans(puzzle, parent, ceiling, restarts, serial_offset, salt_stride):
    seeds = tuple(dict.fromkeys(puzzle.seeds))
    targets = tuple(sorted(set(puzzle.targets) - set(seeds)))
    tape = tuple(dict.fromkeys(step.output for step in replay(puzzle, parent) if step.output not in seeds))
    helper_limit = ceiling - len(targets) - 1
    hints = tuple(v for v in tape if v not in targets)
    prefixes = {(): 0}
    for tail in (5, 8, 12):
        cut = max(0, min(len(hints), helper_limit) - tail)
        if not cut:
            continue
        used = 0
        for i, v in enumerate(tape):
            used += v not in targets
            if used == cut:
                prefixes[tape[:i+1]] = cut
                break

    graph = first_recipes(puzzle, parent)
    target_set = set(targets)
    retained_options = []
    groups = [(t,) for t in targets]
    groups.extend(combinations(targets, 2))
    for missing in groups:
        retain = active_graph(puzzle, graph, targets=target_set - set(missing))
        paid = len(retain.keys() - target_set)
        if 2 <= helper_limit - paid <= 9 and missing[0] not in retain:
            sequence = tuple(v for v in tape if v in retain)
            retained_options.append((helper_limit - paid, missing, sequence, paid))
    for _, _, sequence, paid in sorted(retained_options)[:12]:
        prefixes[sequence] = paid

    for serial, (prefix, paid) in enumerate(prefixes.items()):
        for n in range(restarts):
            seed = 724899 + int(puzzle.id[-4:]) * 61 + serial * salt_stride + n + serial_offset * 8191
            profile = (0, 1, 2, 3)[(serial+n) % 4]
            yield seeds, targets, prefix, paid, hints, helper_limit, seed, profile


def run(task):
    puzzle, old, engine, width, branch, timeout, plan = task
    seeds, targets, prefix, paid, hints, helper_limit, salt, profile = plan
    fixed = seeds + prefix
    header = (puzzle.limit, len(seeds), len(fixed), len(targets), len(hints), helper_limit-paid,
              width, branch, profile, salt)
    detail = dict(prefix=prefix, paid=paid, profile=profile, salt=salt)
    wire = " ".join(map(str, (*header, *fixed, *targets, *hints))) + "\n"
    try:
        p = subprocess.run([str(engine)], input=wire, capture_output=True, check=True, text=True,
                           timeout=timeout, creationflags=getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0))
    except subprocess.TimeoutExpired:
        return puzzle.id, None, dict(detail, status="timeout")
    status, expanded, transitions, *values = map(int, p.stdout.split())
    tape = None
    if status:
        if tuple(values[:len(fixed)]) != fixed:
            raise ValueError("Witness changed its fixed prefix")
        tape = encode(puzzle, tuple(values[len(seeds):]))
        if check(puzzle, tape) >= len(old):
            raise ValueError("Witness failed the score limit")
    return puzzle.id, tape, dict(detail, status="found" if tape is not None else "no-candidate",
                                 expanded=expanded, transitions=transitions, length=len(tape) if tape else None)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for key in ("puzzles", "parent", "bounds", "engine", "out"):
        ap.add_argument("--" + key, type=Path, required=True)
    for key, n in (("count", 50), ("width", 32), ("branch", 8), ("jobs", 8),
                   ("restarts", 3), ("timeout", 12), ("cap", 350000)):
        ap.add_argument("--" + key, type=int, default=n)
    ap.add_argument("--min-cap", type=int, default=1)
    ap.add_argument("--max-steps", type=int, default=39)
    ap.add_argument("--salt-stride", type=int, default=19)
    ap.add_argument("--ids", nargs="+")
    ap.add_argument("--donors", nargs="+", type=Path, default=[])
    args = ap.parse_args()
    puzzles = read_puzzles(args.puzzles)
    parent = read_submission(args.parent)
    donors = [read_submission(path) for path in args.donors]
    with args.bounds.open(encoding="utf-8", newline="") as f:
        bound = {r["id"]: int(r["certified_lower"]) for r in csv.DictReader(f)}
    cohort = []
    for p in puzzles:
        n = len(parent[p.id])
        if ((not args.ids or p.id in args.ids) and 0 < len(set(p.targets) - set(p.seeds)) < n <= args.max_steps and bound[p.id] < n
                and len(p.seeds) == len(set(p.seeds)) and len(p.seeds) + n <= p.registers
                and args.min_cap <= p.limit <= args.cap):
            cohort.append(p)
    chosen = sorted(cohort, key=lambda p: (p.limit, p.id))[:args.count]
    tasks = []
    for p in chosen:
        start = parent[p.id]
        sources = tuple(dict.fromkeys([start, *(d[p.id] for d in donors if p.id in d)]))
        for source_index, source in enumerate(sources):
            for plan in plans(p, source, len(start), args.restarts, source_index, args.salt_stride):
                tasks.append((p, start, args.engine, args.width, args.branch, args.timeout, plan))
    rows, wins = {p.id: [] for p in chosen}, {}
    with ThreadPoolExecutor(args.jobs) as executor:
        for i, tape, detail in executor.map(run, tasks):
            rows[i].append(detail)
            if tape is not None and len(tape) < len(wins.get(i, parent[i])):
                wins[i] = tape
                print(i, len(parent[i]), len(tape), flush=True)
    args.out.mkdir(parents=True, exist_ok=True)
    write_submission(args.out/"wins.csv", [p for p in puzzles if p.id in wins], wins)
    settings = {k: v for k,v in vars(args).items() if isinstance(v, int)}
    archive = dict(parent_sha256=sha256(args.parent), engine_sha256=sha256(args.engine),
                   bounds_sha256=sha256(args.bounds), settings=settings, rows=rows, eligible=len(cohort),
                   donors={path.name: sha256(path) for path in args.donors}, ids=args.ids)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(archive, separators=(",", ":")).encode(), mtime=0))
    print(len(rows), len(tasks), len(wins), sum(len(parent[i])-len(t) for i,t in wins.items()), flush=True)


if __name__ == "__main__":
    main()
