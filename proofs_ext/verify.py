"""Independently recheck the extended proof layer.

Replays the improved submission, recomputes every analytic lower bound, reruns
all shards of both the original proofs/decisions.json and proofs_ext/decisions.json,
and compares the combined per-puzzle table proofs_ext/bounds.csv.
"""

import argparse
import csv
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from proofs_ext.audit_cache import ensure_audit, native_input
from elf import read_puzzles, read_submission, score
from prefix_bounds import lower
from tiny import encode


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
    if status == "FOUND":
        values = tuple(map(int, output[1].split()))
        starts = tuple(dict.fromkeys(puzzle.seeds))
        if values[: len(starts)] != starts:
            raise ValueError("Starting values differ")
        program = encode(puzzle, values[len(starts) :])
        missing = len(set(puzzle.targets) - set(puzzle.seeds))
        if len(program) > missing + helpers:
            raise ValueError("Replayed witness exceeds its declared budget")
    return status, int(nodes), int(last_candidates)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--binary", type=Path, default=ROOT / "work/proofs/exact_helpers.exe")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--puzzles", type=Path, default=ROOT / "data/puzzles.csv")
    ap.add_argument("--submission", type=Path, default=ROOT / "improve/submission.csv")
    ap.add_argument("--only", type=str, default="",
                    help="comma-separated receipt stems (id_hN) to recheck; "
                         "skips the full-table comparison when set")
    ap.add_argument("--refresh-audit", action="store_true", help="rerun the local pair audit")
    args = ap.parse_args()
    if args.jobs < 1:
        ap.error("Expected a positive worker count")
    only = {s.strip() for s in args.only.split(",") if s.strip()}

    normalized = args.puzzles.read_bytes().replace(b"\r\n", b"\n")
    digest = sha256(normalized).hexdigest()
    decisions = []
    original = ROOT / "proofs/decisions.json"
    if original.exists():
        receipt = json.loads(original.read_text())
        if receipt["puzzles_lf_sha256"] != digest:
            raise ValueError("Unexpected puzzle file in proofs/decisions.json")
        decisions.extend(receipt["decisions"])
    # Extended layer: union of the merged receipt and per-decision files.
    merged = {}
    ext_receipt = ROOT / "proofs_ext/decisions.json"
    if ext_receipt.exists():
        receipt = json.loads(ext_receipt.read_text())
        if receipt["puzzles_lf_sha256"] != digest:
            raise ValueError("Unexpected puzzle file in proofs_ext/decisions.json")
        for d in receipt["decisions"]:
            merged[(d["id"], d["helpers"])] = d
    decision_dir = ROOT / "proofs_ext/decisions.d"
    if decision_dir.exists():
        for path in sorted(decision_dir.glob("*.json")):
            d = json.loads(path.read_text())
            merged[(d["id"], d["helpers"])] = d
    decisions.extend(merged[key] for key in sorted(merged))
    if only:
        decisions = [d for d in decisions if f"{d['id']}_h{d['helpers']}" in only]
        missing_stems = only - {f"{d['id']}_h{d['helpers']}" for d in decisions}
        if missing_stems:
            raise ValueError(f"--only stems not found: {sorted(missing_stems)}")

    puzzles = read_puzzles(args.puzzles)
    programs = read_submission(args.submission)
    score(puzzles, programs)
    analytic = {p.id: lower(p) for p in puzzles}
    bounds = dict(analytic)
    by_id = {p.id: p for p in puzzles}
    binary = args.binary.resolve()
    with ThreadPoolExecutor(args.jobs) as pool:
        for row in decisions:
            p = by_id[row["id"]]
            ensure_audit(binary, p, refresh=args.refresh_audit)
            shards = len(row["shard_nodes"])
            jobs = [
                pool.submit(query, binary, p, row["helpers"], row["max_nodes_per_shard"], i, shards)
                for i in range(shards)
            ]
            result = [job.result() for job in jobs]
            if any(status != "UNSAT" for status, _, _ in result):
                raise ValueError(f"{p.id}: not all branches proved impossible")
            if [nodes for _, nodes, _ in result] != row["shard_nodes"] or sum(
                last for _, _, last in result
            ) != row["terminal_candidates"]:
                raise ValueError(f"{p.id}: search trace differs from the receipt")
            missing = len(set(p.targets) - set(p.seeds))
            bounds[p.id] = max(bounds[p.id], missing + row["helpers"] + 1)
            if bounds[p.id] > len(programs[p.id]):
                raise ValueError(f"{p.id}: lower exceeds verified upper")
            print(p.id, "helpers", row["helpers"], "lower", bounds[p.id],
                  "upper", len(programs[p.id]), flush=True)

    if only:
        print(f"Rechecked {len(decisions)} selected decisions; all traces match.")
        return

    with (ROOT / "proofs_ext/bounds.csv").open(newline="") as f:
        published = list(csv.DictReader(f))
    expected = [
        (p.id, str(analytic[p.id]), str(bounds[p.id]), str(len(programs[p.id])))
        for p in puzzles
    ]
    if expected != [
        (r["id"], r["prefix_lower"], r["certified_lower"], r["verified_upper"])
        for r in published
    ]:
        raise ValueError("Per-puzzle table differs")
    if any(bounds[p.id] > len(programs[p.id]) for p in puzzles):
        raise ValueError("Inconsistent bounds")
    print(
        "Total",
        sum(bounds.values()),
        sum(map(len, programs.values())),
        "proved optimal",
        sum(bounds[p.id] == len(programs[p.id]) for p in puzzles),
    )


if __name__ == "__main__":
    main()