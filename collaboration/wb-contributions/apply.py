"""Regenerate the recorded strict improvements against the current candidates."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from elf import check, read_puzzles, read_submission, write_submission
from solvers.graphs.algebra_rewrite import repair_algebra


def main():
    puzzles = read_puzzles(ROOT / "data/puzzles.csv")
    own = read_submission(ROOT / "submission.csv")
    public = read_submission(ROOT / "public-assisted/submission.csv")
    own_out = dict(own)
    public_out = dict(public)
    report = {"algebra": {}, "cross_line": {}}

    for puzzle in puzzles:
        new = repair_algebra(puzzle, own[puzzle.id])
        if len(new) < len(own[puzzle.id]):
            check(puzzle, new)
            own_out[puzzle.id] = new
            report["algebra"][puzzle.id] = [len(own[puzzle.id]), len(new)]

    for puzzle in puzzles:
        pid = puzzle.id
        if len(own_out[pid]) < len(public_out[pid]):
            check(puzzle, own_out[pid])
            public_out[pid] = own_out[pid]
            report["cross_line"][pid] = [len(public[pid]), len(public_out[pid])]

    target = ROOT / "work/wb-applied"
    target.mkdir(parents=True, exist_ok=True)
    write_submission(target / "independent.csv", puzzles, own_out)
    write_submission(target / "public-assisted.csv", puzzles, public_out)
    report["scores"] = {
        "independent_before": sum(len(v) for v in own.values()),
        "independent_after": sum(len(v) for v in own_out.values()),
        "public_before": sum(len(v) for v in public.values()),
        "public_after": sum(len(v) for v in public_out.values()),
    }
    (target / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
