"""Move complete target ancestor sets before a physical cut, then rebuild the suffix."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path

from suffix_search import assemble, solve, suffix_at
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import _allocate, active_graph, first_recipes


def plans(puzzle, program, fractions):
    old_order = first_recipes(puzzle, program)
    active = active_graph(puzzle, old_order)
    graph = {value: recipe for value, recipe in old_order.items() if value in active}
    values = list(graph)
    targets = sorted(set(puzzle.targets) & graph.keys())
    bit = {value: 1 << i for i, value in enumerate((*values, *dict.fromkeys(puzzle.seeds)))}
    parents = dict.fromkeys(puzzle.seeds, 0)
    users = dict.fromkeys(bit, 0)
    for value, (_, left, right) in graph.items():
        parents[value] = parents[left] | parents[right] | bit[value]
        for source in {left, right}:
            users[source] |= bit[value]
    target_bits = sum(bit[value] for value in targets)
    seed_bits = sum(bit[value] for value in set(puzzle.seeds))

    def crossings(mask):
        available = mask | seed_bits
        return sum(bool(available & mark and users[value] & ~mask) for value, mark in bit.items())

    chosen = set()
    for fraction in fractions:
        size = len(graph) * fraction // 100
        tolerance = max(8, len(graph) // 9)
        candidates = set()
        for goal in targets:
            prefix = parents[goal]
            while prefix.bit_count() <= size + tolerance:
                if abs(prefix.bit_count() - size) <= tolerance:
                    candidates.add(prefix)
                possible = [prefix | parents[t] for t in targets if not prefix & bit[t]]
                if not possible:
                    break
                prefix = min(possible, key=lambda v: (v.bit_count(), -(v & target_bits).bit_count(), v))
        # Equal-size candidates are ranked by how few old values remain tied to later work.
        ranked = sorted(candidates - chosen, key=lambda mask:
                        (crossings(mask) + abs(mask.bit_count() - size) / 3,
                         -((mask & target_bits).bit_count()), mask))
        for mask in ranked[:10]:
            if (target_bits & ~mask).bit_count() < 2:
                continue
            first = [v for v in values if mask & bit[v]]
            last = [v for v in values if not mask & bit[v]]
            order = {v: graph[v] for v in first + last}
            tape = _allocate(puzzle, order, False, 0, fixed_order=True)
            if tape is None:
                continue
            cut = suffix_at(puzzle, tape, len(first))
            baseline = suffix_at(puzzle, program, len(first))
            if cut is None or baseline is None:
                continue
            if cut[0].seeds == baseline[0].seeds and cut[0].targets == baseline[0].targets:
                continue
            check(puzzle, tape)
            chosen.add(mask)
            yield tape, cut, baseline, dict(cut=len(first), crossing=crossings(mask),
                                            kept_goals=(mask & target_bits).bit_count())
            break


def work(job):
    puzzle, parent, binary, rounds, fractions = job
    record = dict(before=len(parent), arms=[])
    best = parent
    options = list(plans(puzzle, parent, fractions))
    if options and binary:
        seed = 701303 + int(puzzle.id[-4:])
        full = solve(binary, puzzle, [parent], seed, rounds)
        record["control"] = len(full)
        best = min((best, full), key=len)
    for tape, cut, baseline, detail in options:
        best = min((best, tape), key=len)
        if not binary:
            record["arms"].append(dict(detail, reordered=len(tape)))
            continue
        totals = []
        for start, subsection in ((tape,cut),(parent,baseline)):
            sub, tail, slots = subsection
            refined = solve(binary, sub, [tail], seed, rounds)
            whole = assemble(puzzle, start, detail["cut"], refined, slots)
            best = min((best, start, whole), key=len)
            totals.append(len(whole))
        record["arms"].append(dict(detail, reordered=len(tape), target_cut=totals[0], time_cut=totals[1]))
    record["after"] = check(puzzle, best)
    return puzzle.id, best, record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("puzzles", "parent", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--binary", type=Path, help="Optional engine. Without it, test reordering alone.")
    for name, default in (("count", 90), ("offset", 0), ("jobs", 10), ("rounds", 440)):
        parser.add_argument("--" + name, type=int, default=default)
    parser.add_argument("--fractions", nargs="+", type=int, default=[34, 61])
    args = parser.parse_args()
    puzzles = read_puzzles(args.puzzles)
    parents = read_submission(args.parent)
    pool = sorted((p for p in puzzles if len(parents[p.id]) >= 48 and len(p.targets) >= 6),
                  key=lambda p: hashlib.sha256(("target-frontier-1-" + p.id).encode()).digest())
    jobs = [(p,parents[p.id],args.binary,args.rounds,args.fractions) for p in pool[args.offset:args.offset + args.count]]
    rows, wins = {}, {}
    with ThreadPoolExecutor(args.jobs) as executor:
        for i,tape,row in executor.map(work,jobs):
            rows[i] = row
            if len(tape) < len(parents[i]):
                wins[i] = tape
                print(i,len(parents[i]),len(tape),flush=True)
    args.out.mkdir(exist_ok=True, parents=True)
    write_submission(args.out / "wins.csv", [p for p in puzzles if p.id in wins], wins)
    report = dict(parent_sha256=sha256(args.parent), eligible=len(pool),
                  fractions=args.fractions, count=args.count, offset=args.offset, rounds=args.rounds, rows=rows)
    if args.binary:
        report["engine_sha256"] = sha256(args.binary)
    (args.out / "results.json.gz").write_bytes(gzip.compress(json.dumps(report,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-len(tape) for i,tape in wins.items()),flush=True)


if __name__ == "__main__":
    main()
