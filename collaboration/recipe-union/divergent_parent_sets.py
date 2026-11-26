"""Compare structurally distinct two- and three-parent recombination."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from itertools import combinations
import gzip
import json
from pathlib import Path

from full_union import additions, compile_selection
from graph import first_recipes
from elf import check, read_puzzles, read_submission, sha256, write_submission
from cone_assignment import solve


def distance(first, second):
    return len(first ^ second) / len(first | second)


def compare(job):
    puzzle, parent, first, second = job
    candidates = {"parent": parent}
    records = {}
    for label, donors in (("two", [first]), ("three", [first, second])):
        parents = [parent, *donors]
        cone, cone_result = solve(puzzle, parents, extra=16, deterministic_budget=0.22)
        selection_result, selected = compile_selection(
            puzzle, parent, first_recipes(puzzle, parent), additions(puzzle, parents), True
        )
        records[label] = {
            "cone": cone_result, "cone_steps": len(cone),
            "arithmetic": selection_result, "arithmetic_steps": len(selected),
        }
        candidates[label] = min(cone, selected, key=len)
    method = min(candidates, key=lambda name: len(candidates[name]))
    winner = candidates[method]
    check(puzzle, winner)
    return puzzle.id, winner, {
        "before": len(parent), "after": len(winner), "best": method, "runs": records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("puzzles", "parent", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--donors", nargs="+", type=Path, required=True)
    parser.add_argument("--count", type=int, default=64)
    parser.add_argument("--gap", type=int, default=12)
    parser.add_argument("--jobs", type=int, default=6)
    args = parser.parse_args()
    puzzles = read_puzzles(args.puzzles)
    bank = read_submission(args.parent)
    donors = [read_submission(path) for path in args.donors]
    queue = []
    for puzzle in puzzles:
        tape = bank[puzzle.id]
        if not 35 <= len(tape) <= 230:
            continue
        values = set(first_recipes(puzzle, tape))
        novel = {}
        for donor in donors:
            other = donor.get(puzzle.id)
            if other is None or len(other) > len(tape) + args.gap:
                continue
            signature = frozenset(first_recipes(puzzle, other))
            if signature != values:
                novel[signature] = min(novel.get(signature, other), other, key=len)
        choices = []
        for first, second in combinations(novel, 2):
            novelty = min(distance(values, first), distance(values, second), distance(first, second))
            if novelty:
                choices.append((novelty, len(first | second), novel[first], novel[second]))
        if choices:
            priority, _, first, second = max(choices)
            first, second = sorted((first, second), key=len)
            queue.append((-priority, puzzle.id, (puzzle, tape, first, second)))
    rows = {}
    wins = {}
    args.out.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(args.jobs) as pool:
        for i, tape, row in pool.map(compare, (job for _, _, job in sorted(queue)[:args.count]), chunksize=1):
            rows[i] = row
            if row["after"] < row["before"]:
                wins[i] = tape
                print(i, row["before"], row["after"], row["best"], flush=True)
    write_submission(args.out / "wins.csv", [p for p in puzzles if p.id in wins], wins)
    data = {
        "parent_sha256": sha256(args.parent), "puzzles_sha256": sha256(args.puzzles),
        "donors": {path.name: sha256(path) for path in args.donors},
        "count": args.count, "gap": args.gap, "eligible": len(queue), "rows": rows,
    }
    raw = json.dumps(data, separators=(",", ":")).encode()
    (args.out / "results.json.gz").write_bytes(gzip.compress(raw, mtime=0))
    print(len(queue), len(rows), len(wins), sum(row["before"] - row["after"] for row in rows.values()))


if __name__ == "__main__":
    main()
