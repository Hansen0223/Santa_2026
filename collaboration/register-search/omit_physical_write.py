"""Shorten a physical tape by deleting a write and repairing its consumers."""
import argparse
from bisect import bisect_left
from collections import Counter, defaultdict
from dataclasses import replace
import gzip
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from elf import arithmetic, check, read_puzzles, read_submission, replay, sha256, write_submission
from graph import _allocate


def alternatives(registers, output):
    """Generate valid one-step recipes in the supplied value-to-operand map."""
    for value, left in registers.items():
        right = registers.get(output - value)
        if right is not None:
            yield "+", left, right
        right = registers.get(value - output)
        if right is not None:
            yield "-", left, right
        if output % value == 0:
            right = registers.get(output // value)
            if right is not None:
                yield "*", left, right
        right = registers.get(value * output)
        if right is not None:
            yield "/", right, left


def omission(puzzle, tape):
    trace = replay(puzzle, tape)
    required = set(puzzle.targets) - set(puzzle.seeds)
    outputs = Counter(step.output for step in trace)
    registers = [*puzzle.seeds, *([0] * (puzzle.registers - len(puzzle.seeds)))]
    previous = [None] * puzzle.registers
    consumers = [[] for _ in tape]
    states = []
    for i, (_, left, right, destination) in enumerate(tape):
        for index in {previous[left], previous[right]} - {None}:
            consumers[index].append(i)
        states.append(tuple(registers))
        registers[destination] = trace[i].output
        previous[destination] = i

    for i, ((_, _, _, destination), step) in enumerate(zip(tape, trace)):
        if step.output in required and outputs[step.output] == 1:
            continue
        repairs = {}
        for j in consumers[i]:
            state = list(states[j])
            state[destination] = states[i][destination]
            op, left, right, out = tape[j]
            first, second = state[left], state[right]
            if first and second:
                try:
                    if arithmetic(op, first, second) == trace[j].output:
                        continue
                except ValueError:
                    pass
            available = {value: index for index, value in enumerate(state) if value}
            recipe = next(alternatives(available, trace[j].output), None)
            if recipe is None:
                break
            repairs[j] = (*recipe, out)
        else:
            candidate = tuple(repairs.get(j, instruction) for j, instruction in enumerate(tape) if j != i)
            check(puzzle, candidate)
            return candidate, len(repairs)
    return tape, None


def extend_lifetimes(puzzle, tape):
    """Repair with earlier occurrences and allocate the fixed order again."""
    count = len(tape)
    seeds = tuple(range(count, count + len(puzzle.seeds)))
    if not count:
        return tape, None
    allocation = replace(puzzle, seeds=seeds, targets=(),
                         limit=max(puzzle.limit, seeds[-1]))
    trace = replay(puzzle, tape)
    occurrences = defaultdict(list)
    for value, node in zip(puzzle.seeds, seeds):
        occurrences[value].append((-1, node))
    binding = dict(enumerate(seeds))
    original = {}
    consumers = defaultdict(list)
    last_use = {}
    birth = dict.fromkeys(seeds, -1)
    for i, ((op, left, right, destination), step) in enumerate(zip(tape, trace)):
        recipe = (op, binding[left], binding[right])
        original[i] = recipe
        for source in set(recipe[1:]):
            consumers[source].append(i)
            last_use[source] = i
        occurrences[step.output].append((i, i))
        birth[i] = i
        binding[destination] = i

    required = set(puzzle.targets) - set(puzzle.seeds)
    for i, step in enumerate(trace):
        if step.output in required and len(occurrences[step.output]) == 1:
            continue
        options = {}
        for j in consumers.get(i, ()):
            available = {}
            for value, copies in occurrences.items():
                index = bisect_left(copies, (j, -1)) - 1
                if index >= 0 and copies[index][1] == i:
                    index -= 1
                if index >= 0:
                    available[value] = copies[index][1]
            recipes = list(alternatives(available, trace[j].output))
            if not recipes:
                break
            options[j] = recipes
        else:
            for retention_first in (True, False):
                candidate = original.copy()
                del candidate[i]
                live_until = last_use.copy()
                for j, recipes in options.items():
                    def priority(recipe):
                        operands = set(recipe[1:])
                        extension = sum(max(0, j - live_until.get(v, birth[v])) for v in operands)
                        age = sum(j - birth[v] for v in operands)
                        return (extension, age) if retention_first else (age, extension)
                    recipe = min(recipes, key=priority)
                    candidate[j] = recipe
                    for operand in set(recipe[1:]):
                        live_until[operand] = max(j, live_until.get(operand, -1))
                repaired = _allocate(allocation, candidate, False, 0, fixed_order=True)
                if repaired is not None:
                    check(puzzle, repaired)
                    return repaired, len(options)
    return tape, None


def improve(puzzle, tape, extended):
    edits = []
    while True:
        candidate, repaired = omission(puzzle, tape)
        if repaired is not None:
            tape = candidate
            edits.append({"mode": "live", "repaired": repaired})
            continue
        if extended:
            candidate, repaired = extend_lifetimes(puzzle, tape)
            if repaired is not None:
                tape = candidate
                edits.append({"mode": "extended", "repaired": repaired})
                continue
        return tape, edits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("puzzles", "parent", "out"):
        parser.add_argument("--" + field, type=Path, required=True)
    parser.add_argument("--extend-lifetimes", action="store_true")
    args = parser.parse_args()
    puzzles = read_puzzles(args.puzzles)
    original = read_submission(args.parent)
    winners, rows = {}, {}
    for puzzle in puzzles:
        parent = original[puzzle.id]
        tape, edits = improve(puzzle, parent, args.extend_lifetimes)
        if edits:
            winners[puzzle.id] = tape
            print(puzzle.id, len(parent), len(tape), flush=True)
        rows[puzzle.id] = {"before": len(parent), "after": len(tape), "repaired": edits}
    args.out.mkdir(exist_ok=True, parents=True)
    write_submission(args.out / "wins.csv", [p for p in puzzles if p.id in winners], winners)
    record = dict(parent_sha256=sha256(args.parent), extend_lifetimes=args.extend_lifetimes, rows=rows)
    (args.out / "results.json.gz").write_bytes(
        gzip.compress(json.dumps(record, separators=(",", ":")).encode(), mtime=0)
    )
    print(len(rows), len(winners), sum(r["before"] - r["after"] for r in rows.values()), flush=True)


if __name__ == "__main__":
    main()
