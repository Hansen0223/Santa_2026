"""Search physical instruction windows and rebind the unchanged suffix."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from itertools import combinations_with_replacement
import gzip
import hashlib
import json
from pathlib import Path
import sys

from interior_bands import compile_on_parent, solve
from recover_prefix import input_slots
from suffix_search import remap
from two_sided_chains import reverse_steps
from elf import check, read_puzzles, read_submission, replay, sha256, write_submission
from graph import first_recipes
from solvers.graphs.corpus_prefix import arithmetic_edges

RULER = Path(__file__).resolve().parents[1] / "structure-controls/ruler"
sys.path.insert(0, str(RULER))
from selector import compile_selection


def select_arithmetic(inner, warm):
    reference = first_recipes(inner, warm)
    seeds = sorted(set(inner.seeds))
    known = set(seeds) | reference.keys()
    births = {}
    for a, b in combinations_with_replacement(seeds, 2):
        for value, recipe in arithmetic_edges(a, b, inner.limit):
            if value not in known:
                births.setdefault(value, recipe)
    votes = Counter()
    goals = set(inner.targets)
    for target in reference:
        helpful = {value for anchor in known - {target}
                   for value, _ in reverse_steps(target, anchor, inner.limit) if value in births}
        votes.update({value: 1 + (target in goals) for value in helpful})
    selected = sorted(votes, key=lambda value: (-votes[value], value))[:32]
    supplied = [{value: births[value]} for value in selected]
    _, optimized = compile_selection(inner, warm, reference, supplied, True)
    return optimized, len(selected)


def rank_windows(puzzle, tape, trace, count):
    values = [step.output for step in trace]
    targets = set(puzzle.targets)
    registers = [*puzzle.seeds, *[0] * (puzzle.registers - len(puzzle.seeds))]
    states = [tuple(registers)]
    for inst, value in zip(tape, values):
        registers[inst[-1]] = value
        states.append(tuple(registers))
    suffix_live = [frozenset()] * (len(tape) + 1)
    for j in range(len(tape) - 1, -1, -1):
        _, a, b, dest = tape[j]
        suffix_live[j] = (suffix_live[j + 1] - {dest}) | {a, b}
    proposals = []
    solved = set(puzzle.seeds)
    for start, value in enumerate(values):
        if start >= 3 and start % 3 == 0:
            for length in (12, 19, 28, 42):
                stop = start + length
                if stop > len(tape) - 4:
                    continue
                slice_values = set(values[start:stop])
                carry = {states[stop][i] for i in suffix_live[stop]}
                goals = (targets - solved) & slice_values
                outputs = goals | (carry & slice_values)
                if not 2 <= len(outputs) < length - 3:
                    continue
                inputs = len(input_slots(tape[start:stop]))
                score = (length - len(outputs)) / (1 + inputs**0.7 + len(outputs)**0.7)
                proposals.append((-score, start, stop, tuple(sorted(outputs)), suffix_live[stop]))
        solved.add(value)
    chosen = []
    for candidate in sorted(proposals):
        _, start, stop, *_ = candidate
        if any(2 * (min(stop, b) - max(start, a)) > min(stop - start, b - a) for _, a, b, *_ in chosen):
            continue
        chosen.append(candidate)
        if len(chosen) == count:
            break
    return states, chosen


def replay_window(puzzle, inner, replacement, states, start, stop, live, tape, slots):
    end_state = list(states[start])
    for inst, step in zip(replacement, replay(inner, replacement)):
        end_state[slots[inst[-1]]] = step.output
    mapping = {}
    for j in sorted(live):
        matches = [k for k, value in enumerate(end_state) if value == states[stop][j] and k not in mapping.values()]
        if not matches:
            return None
        mapping[j] = matches[0]
    rest = range(puzzle.registers)
    free_original = [k for k in rest if k not in mapping]
    used = set(mapping.values())
    mapping.update(zip(free_original, (k for k in rest if k not in used)))
    result = tape[:start] + remap(replacement, slots) + remap(tape[stop:], mapping)
    check(puzzle, result)
    return result


def work(puzzle, tape, binary, rounds, count, strategy):
    trace = replay(puzzle, tape)
    states, windows = rank_windows(puzzle, tape, trace, count)
    best = tape
    rows = []
    seed = 25083 + int(puzzle.id[-4:])
    original = first_recipes(puzzle, tape)
    for _, start, stop, outputs, live in windows:
        slots = sorted(range(puzzle.registers), key=lambda j: states[start][j] == 0)
        starts = tuple(states[start][j] for j in slots if states[start][j])
        index = {slot: rank for rank, slot in enumerate(slots)}
        inner = replace(puzzle, seeds=starts, targets=outputs)
        warm = remap(tape[start:stop], index)
        if strategy == "arithmetic":
            result, extra = select_arithmetic(inner, warm)
        else:
            result, extra = solve(binary, inner, [warm], seed + start, rounds), None
        method = None
        if len(result) < len(warm):
            rebuilt = replay_window(puzzle, inner, result, states, start, stop, live, tape, slots)
            method = "splice"
            if rebuilt is None:
                removed = {step.output for step in trace[start:stop]}
                fixed = {v: edge for v, edge in original.items() if v not in removed}
                rebuilt = compile_on_parent(puzzle, tape, fixed | first_recipes(inner, result))
                method = "recompile" if rebuilt is not None else "rejected"
            if rebuilt is not None:
                best = min(best, rebuilt, key=len)
        rows.append(dict(start=start, stop=stop, outputs=len(outputs), live_out=len(live),
                         rebuilt=len(result), extra=extra, method=method))
    return puzzle.id, best, dict(before=len(tape), after=check(puzzle, best), windows=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("puzzles", "parent", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    for key, default in (("count", 64), ("rounds", 256), ("windows", 3), ("jobs", 7)):
        parser.add_argument("--" + key, type=int, default=default)
    parser.add_argument("--strategy", choices=("anneal", "arithmetic"), default="anneal")
    parser.add_argument("--binary", type=Path)
    args = parser.parse_args()
    if args.strategy == "anneal" and args.binary is None:
        parser.error("--binary is required for annealing")
    puzzles = read_puzzles(args.puzzles)
    parent = read_submission(args.parent)
    eligible = [p for p in puzzles if 42 <= len(parent[p.id]) <= 280]
    selected = sorted(eligible, key=lambda p: hashlib.sha256(("window-1/" + p.id).encode()).digest())[:args.count]
    args.out.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(args.jobs) as pool:
        jobs = [pool.submit(work, p, parent[p.id], args.binary, args.rounds, args.windows, args.strategy) for p in selected]
        wins, rows = {}, {}
        for job in jobs:
            key, tape, receipt = job.result()
            rows[key] = receipt
            if len(tape) < len(parent[key]):
                wins[key] = tape
                print(key, len(parent[key]), len(tape), flush=True)
    write_submission(args.out / "wins.csv", [p for p in puzzles if p.id in wins], wins)
    receipt = dict(parent_sha256=sha256(args.parent), puzzles_sha256=sha256(args.puzzles), binary_sha256=sha256(args.binary) if args.binary else None,
                   strategy=args.strategy,
                   settings={k: v for k, v in vars(args).items() if isinstance(v, int)}, eligible=len(eligible), rows=rows)
    (args.out / "results.json.gz").write_bytes(gzip.compress(json.dumps(receipt, separators=(",", ":")).encode(), mtime=0))
    print(len(rows), len(wins), sum(len(parent[i]) - len(t) for i, t in wins.items()))


if __name__ == "__main__":
    main()
