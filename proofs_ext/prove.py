"""Run sharded helper-budget decisions and record receipts, additively.

Original proofs/ files are never modified. New decisions are appended to
proofs_ext/decisions.json; the combined table is written to proofs_ext/bounds.csv.
"""

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from proofs_ext.audit_cache import ensure_audit, native_input
from elf import read_puzzles, read_submission, score
from prefix_bounds import available, lower
from tiny import encode

EXT = ROOT / "proofs_ext"
DECISION_DIR = EXT / "decisions.d"


class ReceiptLock:
    """Serialize read-modify-write of the shared receipts across processes."""

    def __init__(self, path, timeout=3600):
        self.path = path
        self.timeout = timeout

    def __enter__(self):
        start = time.time()
        while True:
            try:
                fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                return self
            except FileExistsError:
                if time.time() - start > self.timeout:
                    raise TimeoutError(f"stale lock {self.path}")
                time.sleep(1)

    def __exit__(self, *exc):
        self.path.unlink(missing_ok=True)


def all_decisions():
    """Union of the merged receipt and the per-decision files (source of truth)."""
    merged = {}
    receipt_path = EXT / "decisions.json"
    if receipt_path.exists():
        for d in json.loads(receipt_path.read_text())["decisions"]:
            merged[(d["id"], d["helpers"])] = d
    if DECISION_DIR.exists():
        for path in sorted(DECISION_DIR.glob("*.json")):
            d = json.loads(path.read_text())
            merged[(d["id"], d["helpers"])] = d
    return [merged[key] for key in sorted(merged)]


def merge_receipts(puzzles_path, submission_path):
    """Regenerate decisions.json and bounds.csv from the per-decision files."""
    puzzles = read_puzzles(puzzles_path)
    programs = read_submission(submission_path)
    score(puzzles, programs)
    digest = sha256(puzzles_path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    decisions = all_decisions()
    with ReceiptLock(EXT / ".receipt.lock"):
        dj_tmp = EXT / "decisions.json.tmp"
        dj_tmp.write_text(
            json.dumps({"puzzles_lf_sha256": digest, "decisions": decisions}, indent=2) + "\n",
            encoding="utf8",
        )
        dj_tmp.replace(EXT / "decisions.json")
        original = {
            r["id"]: r
            for r in csv.DictReader((ROOT / "proofs/bounds.csv").open(newline=""))
        }
        analytic = {q.id: lower(q) for q in puzzles}
        certified = {
            pid: max(int(r["certified_lower"]), analytic[pid]) for pid, r in original.items()
        }
        for d in decisions:
            certified[d["id"]] = max(certified[d["id"]], d["lower_bound"])
        rows = []
        for q in puzzles:
            lb = certified[q.id]
            ub = len(programs[q.id])
            if lb > ub:
                raise AssertionError((q.id, lb, ub))
            rows.append((q.id, analytic[q.id], lb, ub))
        with (EXT / "bounds.csv").open("w", encoding="utf8", newline="") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(("id", "prefix_lower", "certified_lower", "verified_upper"))
            writer.writerows(rows)
    print(
        "Total lower", sum(r[2] for r in rows),
        "upper", sum(r[3] for r in rows),
        "proved optimal", sum(r[2] == r[3] for r in rows),
    )


def query(binary, puzzle, helpers, node_limit, shard, total):
    output = subprocess.run(
        [str(binary), str(shard), str(total)],
        input=native_input(puzzle, helpers, node_limit),
        text=True,
        check=True,
        capture_output=True,
    ).stdout.splitlines()
    status, nodes, last_candidates = output[0].split()
    if status not in ("FOUND", "UNKNOWN", "UNSAT"):
        raise ValueError("Unrecognized decision")
    witness = None
    if status == "FOUND":
        values = tuple(map(int, output[1].split()))
        starts = tuple(dict.fromkeys(puzzle.seeds))
        if values[: len(starts)] != starts:
            raise ValueError("Starting values differ")
        program = encode(puzzle, values[len(starts) :])
        missing = len(set(puzzle.targets) - set(puzzle.seeds))
        if len(program) > missing + helpers:
            raise ValueError("Replayed witness exceeds its declared budget")
        witness = list(values)
    return status, int(nodes), int(last_candidates), witness


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("puzzle_id", nargs="?")
    ap.add_argument("helpers", type=int, nargs="?")
    ap.add_argument("--merge-only", action="store_true",
                    help="regenerate receipts from decisions.d without searching")
    ap.add_argument("--binary", type=Path, default=ROOT / "work/proofs/exact_helpers.exe")
    ap.add_argument("--shards", type=int, default=0, help="0 = one per root helper option")
    ap.add_argument("--node-limit", type=int, default=2_000_000_000)
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--refresh-audit", action="store_true",
                    help="rerun the pair-coverage audit even when a matching local audit exists")
    ap.add_argument("--puzzles", type=Path, default=ROOT / "data/puzzles.csv")
    ap.add_argument("--submission", type=Path, default=ROOT / "improve/submission.csv")
    args = ap.parse_args()
    if args.merge_only:
        merge_receipts(args.puzzles, args.submission)
        return
    if args.puzzle_id is None or args.helpers is None:
        ap.error("puzzle_id and helpers are required unless --merge-only")

    puzzles = read_puzzles(args.puzzles)
    programs = read_submission(args.submission)
    score(puzzles, programs)
    p = next(q for q in puzzles if q.id == args.puzzle_id)
    missing = len(set(p.targets) - set(p.seeds))

    ensure_audit(args.binary, p, refresh=args.refresh_audit)

    shards = args.shards or max(1, len(available(p.seeds, set(p.targets), p.limit)))
    start = time.time()
    with ThreadPoolExecutor(args.jobs) as pool:
        jobs = [
            pool.submit(query, args.binary, p, args.helpers, args.node_limit, i, shards)
            for i in range(shards)
        ]
        results = [job.result() for job in jobs]
    elapsed = round(time.time() - start, 1)
    statuses = [r[0] for r in results]
    print(args.puzzle_id, "helpers", args.helpers, "shards", shards, statuses)
    print("nodes", [r[1] for r in results], "seconds", elapsed)

    if "UNKNOWN" in statuses:
        print("INCONCLUSIVE: node cap reached; nothing recorded")
        return
    if "FOUND" in statuses:
        winner = next(r for r in results if r[0] == "FOUND")
        print("FOUND witness values:", winner[3])
        print("program length", missing + args.helpers, "vs upper", len(programs[p.id]))
        return

    decision = {
        "id": p.id,
        "helpers": args.helpers,
        "max_nodes_per_shard": args.node_limit,
        "shard_nodes": [r[1] for r in results],
        "terminal_candidates": sum(r[2] for r in results),
        "seconds_16_threads": elapsed,
        "lower_bound": missing + args.helpers + 1,
    }
    # Per-decision file first: concurrent drivers can never lose a receipt.
    DECISION_DIR.mkdir(exist_ok=True)
    target = DECISION_DIR / f"{p.id}_h{args.helpers}.json"
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(decision, indent=2) + "\n", encoding="utf8")
    tmp.replace(target)
    merge_receipts(args.puzzles, args.submission)


if __name__ == "__main__":
    main()