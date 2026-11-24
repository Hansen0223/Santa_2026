"""Interleave new arithmetic with an incumbent order under a register limit."""
from collections import deque
from functools import cache
from heapq import nsmallest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from elf import check
from graph import _allocate, active_graph


def interleave(puzzle, previous, recipes, movable=()):
    """Search all interleavings of fixed incumbent steps and freely ordered steps."""
    graph = active_graph(puzzle, recipes)
    free = set(movable) | {
        value for value, recipe in graph.items() if recipe != previous.get(value)
    }
    fixed = [value for value in previous if value in graph and value not in free]
    change = [value for value in graph if value in free]
    bit = {value: 1 << i for i, value in enumerate((*graph, *dict.fromkeys(puzzle.seeds)))}
    seeds = sum(bit[value] for value in set(puzzle.seeds))
    needs = {
        value: bit[left] | bit[right] for value, (_, left, right) in graph.items()
    }
    fixed_before = [seeds]
    for value in fixed:
        fixed_before.append(fixed_before[-1] | bit[value])
    fixed_after = [0] * (len(fixed) + 1)
    for i in range(len(fixed) - 1, -1, -1):
        fixed_after[i] = fixed_after[i + 1] | needs[fixed[i]]

    all_change = (1 << len(change)) - 1

    @cache
    def change_frontier(mask):
        if not mask:
            return 0, 0
        lowest = mask & -mask
        value = change[lowest.bit_length() - 1]
        computed, required = change_frontier(mask ^ lowest)
        return computed | bit[value], required | needs[value]

    start = (0, 0)
    finish = (len(fixed), all_change)
    previous_state = {start: None}
    queue = deque([start])
    highest = 0
    while queue:
        i, mask = state = queue.popleft()
        highest = max(highest, i + mask.bit_count())
        if state == finish:
            order = []
            while state != start:
                state, value = previous_state[state]
                order.append(value)
            ordered = {value: graph[value] for value in reversed(order)}
            tape = _allocate(puzzle, ordered, False, 0, fixed_order=True)
            if tape is None:
                raise RuntimeError("modeled register use disagrees with allocation")
            check(puzzle, tape)
            return tape, dict(states=len(previous_state), deepest=highest, movable=len(change))
        done = fixed_before[i] | change_frontier(mask)[0]
        remaining = all_change ^ mask
        options = [(fixed[i], i + 1, mask)] if i < len(fixed) else []
        while remaining:
            lowest = remaining & -remaining
            remaining ^= lowest
            options.append((change[lowest.bit_length() - 1], i, mask | lowest))
        for value, next_i, next_mask in options:
            next_state = (next_i, next_mask)
            if next_state in previous_state or needs[value] & ~done:
                continue
            later = fixed_after[next_i] | change_frontier(all_change ^ next_mask)[1]
            # Even a result with no consumers needs a destination for its instruction.
            required = bit[value] | ((done | bit[value]) & later)
            if required.bit_count() > puzzle.registers:
                continue
            previous_state[next_state] = state, value
            queue.append(next_state)
    return None, dict(states=len(previous_state), deepest=highest, movable=len(change))

def backward_beam(puzzle, recipes, width):
    """Build the program from its tail while enforcing exact destination pressure."""
    if width < 1:
        raise ValueError("beam width must be positive")
    graph = active_graph(puzzle, recipes)
    values = list(graph)
    count = len(values)
    index = {value: i for i, value in enumerate((*values, *dict.fromkeys(puzzle.seeds)))}
    operands = [
        (1 << index[left]) | (1 << index[right])
        for _, left, right in graph.values()
    ]
    parents = [tuple(index[source] for source in {left, right} if source in graph)
               for _, left, right in graph.values()]
    consumers = [0] * count
    for node, inputs in enumerate(parents):
        for source in inputs:
            consumers[source] |= 1 << node
    ready = sum(1 << node for node, used in enumerate(consumers) if not used)
    states = [(0, ready, 0, None)]
    for reached in range(count):
        updated = {}
        for done, ready, live, order in states:
            options = ready
            while options:
                bit = options & -options
                options ^= bit
                visited = done | bit
                if visited in updated or (live | bit).bit_count() > puzzle.registers:
                    continue
                node = bit.bit_length() - 1
                boundary = (live & ~bit) | operands[node]
                if boundary.bit_count() > puzzle.registers:
                    continue
                available = ready ^ bit
                for parent in parents[node]:
                    if consumers[parent] & ~visited == 0:
                        available |= 1 << parent
                updated[visited] = (visited, available, boundary, (node, order))
        if not updated:
            return None, reached
        states = nsmallest(width, updated.values(), key=lambda s:
                           (s[2].bit_count(), -s[1].bit_count(), s[0]))
    tail = states[0][3]
    ordered = {}
    while tail is not None:
        node, tail = tail
        value = values[node]
        ordered[value] = graph[value]
    tape = _allocate(puzzle, ordered, False, 0, fixed_order=True)
    if tape is None:
        raise RuntimeError("modeled register use disagrees with allocation")
    check(puzzle, tape)
    return tape, count

def main():
    import argparse
    from collections import Counter
    import json
    from elf import read_puzzles, read_submission, sha256, write_submission
    from graph import first_recipes
    from quotient_chains import inverse_chain, private_cone

    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("puzzles", "parent", "out"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--puzzle-id", required=True)
    parser.add_argument("--root", type=int, required=True)
    parser.add_argument("--beam", type=int, nargs="*", default=[128, 1024, 8192])
    args = parser.parse_args()
    puzzles = {p.id: p for p in read_puzzles(args.puzzles)}
    puzzle = puzzles[args.puzzle_id]
    incumbent = read_submission(args.parent)[puzzle.id]
    previous = first_recipes(puzzle, incumbent)
    graph = active_graph(puzzle, previous)
    uses = Counter(set(puzzle.targets))
    for _, left, right in graph.values():
        uses.update({left, right})
    cut = private_cone(graph, uses, args.root)
    fixed = {value: recipe for value, recipe in graph.items() if value not in cut}
    ready = set(puzzle.seeds)
    for value, (_, left, right) in fixed.items():
        if left in ready and right in ready:
            ready.add(value)
    replacement = inverse_chain(puzzle, args.root, ready, len(cut) - 1, 12)
    if not replacement:
        raise ValueError("No shorter quotient chain was found")
    candidate = active_graph(puzzle, replacement | fixed)
    tape, details = interleave(puzzle, previous, candidate)
    if tape is None:
        for width in args.beam:
            tape, depth = backward_beam(puzzle, candidate, width)
            details[f"reverse_{width}"] = depth
            if tape is not None:
                break
    details.update(puzzle=puzzle.id, root=args.root, before=len(incumbent),
                   graph=len(candidate), scheduled=None if tape is None else len(tape),
                   parent_sha256=sha256(args.parent))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "results.json").write_text(json.dumps(details, indent=2)+"\n", encoding="utf-8")
    if tape is not None and len(tape) < len(incumbent):
        write_submission(args.out / "wins.csv", [puzzle], {puzzle.id: tape})
    print(json.dumps(details, ensure_ascii=False))


if __name__ == "__main__":
    main()
