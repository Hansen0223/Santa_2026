"""Compare literal portfolio recombination with new arithmetic on the same values."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "collaboration/structure-controls/ruler")]
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import first_recipes, recipes_from
from selector import compile_selection


def additions(puzzle, parents):
    seen = recipes_from(puzzle, parents[0])
    added = []
    for tape in parents[1:]:
        for value, choices in recipes_from(puzzle, tape).items():
            seen.setdefault(value, set())
            for recipe in sorted(choices - seen[value]):
                added.append({value: recipe})
            seen[value].update(choices)
    return added


def work(job):
    puzzle, parents = job
    parent = parents[0]
    original = first_recipes(puzzle, parent)
    paths = additions(puzzle, parents)
    literal, first = compile_selection(puzzle, parent, original, paths, False)
    arithmetic, second = compile_selection(puzzle, parent, original, paths, True)
    best = min((parent, first, second), key=len)
    check(puzzle, best)
    return puzzle.id, best, {
        "before": len(parent), "parents": list(map(len, parents)),
        "literal": literal, "expanded": arithmetic, "after": len(best),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("puzzles", "parent", "out"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--donors", nargs="+", type=Path, required=True)
    for key, n in (("count", 1000), ("offset", 0), ("gap", 7), ("jobs", 8)):
        parser.add_argument("--" + key, type=int, default=n)
    args = parser.parse_args()
    puzzles = read_puzzles(args.puzzles)
    parent = read_submission(args.parent)
    donors = [read_submission(path) for path in args.donors]
    eligible = []
    for puzzle in puzzles:
        tape = parent[puzzle.id]
        size = len(tape)
        if size < 24:
            continue
        baseline = recipes_from(puzzle, tape)
        unique = {tape}
        options = []
        for bank in donors:
            candidate = bank.get(puzzle.id)
            if candidate is None or candidate in unique or len(candidate) > size + args.gap:
                continue
            unique.add(candidate)
            alternate = recipes_from(puzzle, candidate)
            innovation = sum(len(edges - baseline.get(v, set())) for v, edges in alternate.items())
            if innovation:
                options.append((innovation, candidate))
        if options:
            priority = -sum(n / max(1, len(t) - size + 1) for n, t in options) / size
            eligible.append((priority, puzzle.id, puzzle, [t for _, t in options]))
    jobs = [(p, [parent[i], *t]) for _, i, p, t in sorted(eligible)[args.offset:args.offset+args.count]]
    rows, wins = {}, {}
    with ProcessPoolExecutor(args.jobs) as pool:
        for i, tape, record in pool.map(work, jobs, chunksize=2):
            rows[i] = record
            if len(tape) < len(parent[i]):
                wins[i] = tape
    args.out.mkdir(parents=True, exist_ok=True)
    write_submission(args.out / "wins.csv", [p for p in puzzles if p.id in wins], wins)
    data = dict(parent_sha256=sha256(args.parent), donors={f.name:sha256(f) for f in args.donors},
                eligible=len(eligible), settings={k:v for k,v in vars(args).items() if isinstance(v,int)}, rows=rows)
    (args.out / "results.json.gz").write_bytes(gzip.compress(json.dumps(data,separators=(",", ":")).encode(),mtime=0))
    print(len(eligible), len(rows), len(wins), sum(rows[i]["before"] - len(t) for i,t in wins.items()))


if __name__ == "__main__":
    main()
