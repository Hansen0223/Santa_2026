"""Compare equal-round searches from structurally different near-tie programs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(root), str(root / "collaboration/retained-pool")]
from elf import read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes
from neutral_lead import solve


def trial(engine, rounds, job):
    _, puzzle_id, puzzle, tape, other, donor, distance = job
    seed = 193891 + int(puzzle_id[-4:])
    control = solve(engine, puzzle, [tape], seed, rounds)
    archive_first = solve(engine, puzzle, [other, tape], seed, rounds)
    incumbent_first = solve(engine, puzzle, [tape, other], seed, rounds)
    best = min((tape, control, archive_first, incumbent_first), key=len)
    return puzzle_id, best, dict(
        before=len(tape), donor=donor, helper_distance=distance, after=len(best),
        control=len(control), archive_first=len(archive_first), incumbent_first=len(incumbent_first),
    )


def ranked(puzzle, tape, archive_sets):
    if len(tape) < 29:
        return None
    values = set(active_graph(puzzle, first_recipes(puzzle, tape)))
    offers = []
    for donor, bank in enumerate(archive_sets):
        other = bank.get(puzzle.id)
        if other is None or not 0 <= len(other) - len(tape) <= 2:
            continue
        alternate = active_graph(puzzle, first_recipes(puzzle, other))
        different = len(values ^ alternate.keys())
        if different >= 4:
            priority = -different / (len(other) - len(tape) + 1)
            offers.append((priority, donor, other, different))
    if offers:
        priority, donor, other, distance = min(offers)
        return priority, puzzle.id, puzzle, tape, other, donor, distance
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("puzzles", "parent", "binary", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--donors", type=Path, nargs="+", required=True)
    parser.add_argument("--count", type=int, default=115)
    parser.add_argument("--rounds", type=int, default=1700)
    parser.add_argument("--jobs", type=int, default=12)
    args = parser.parse_args()
    puzzles = read_puzzles(args.puzzles)
    current = read_submission(args.parent)
    archive_sets = [read_submission(path) for path in args.donors]
    cohort = sorted(row for p in puzzles if (row := ranked(p, current[p.id], archive_sets)) is not None)
    rows, wins = {}, {}
    with ThreadPoolExecutor(args.jobs) as executor:
        for puzzle_id, result, previous in executor.map(
            lambda job: trial(args.binary, args.rounds, job), cohort[:args.count]
        ):
            rows[puzzle_id] = previous
            if len(result) < previous["before"]:
                wins[puzzle_id] = result
    args.out.mkdir(parents=True, exist_ok=True)
    receipt = dict(
        parent=sha256(args.parent), archives={p.name: sha256(p) for p in args.donors},
        engine=sha256(args.binary), eligible=len(cohort), rounds=args.rounds, rows=rows,
    )
    (args.out / "neutral-native-results.json.gz").write_bytes(
        gzip.compress(json.dumps(receipt, separators=(",", ":")).encode(), mtime=0)
    )
    write_submission(args.out / "neutral-native-wins.csv", [p for p in puzzles if p.id in wins], wins)
    print(len(cohort), len(rows), len(wins), sum(r["before"] - r["after"] for r in rows.values()))


if __name__ == "__main__":
    main()
