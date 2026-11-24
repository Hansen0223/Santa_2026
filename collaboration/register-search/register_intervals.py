"""Schedule a fixed arithmetic graph with an exact register-capacity model."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

from quotient_chains import inverse_chain, private_cone
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import _allocate, active_graph, first_recipes
from solvers.graphs.crossover_lns import load_solver


def schedule(puzzle, graph, reference, seconds, workers):
    solver_module = load_solver()
    model = solver_module.CpModel()
    consumers = defaultdict(list)
    first = dict.fromkeys(puzzle.seeds, -1)
    for v, (_, a, b) in graph.items():
        first[v] = 1 + max(first[a], first[b])
        for u in {a, b}:
            consumers[u].append(v)
    last, count = {}, len(graph)
    for v in reversed(graph):
        last[v] = min((last[u] - 1 for u in consumers[v]), default=count - 1)
    position = {v: model.new_int_var(first[v], last[v], f"at_{i}") for i, v in enumerate(graph)}
    model.add_all_different(position.values())
    for v, (_, a, b) in graph.items():
        for u in {a, b} & position.keys():
            model.add(position[u] < position[v])

    intervals = []
    for v in dict.fromkeys((*puzzle.seeds, *graph)):
        downstream = consumers[v]
        start = position[v] + 1 if v in position else 0
        if not downstream:
            if v in position:
                intervals.append(model.new_fixed_size_interval_var(start, 1, "unused_result"))
            continue
        last_read = model.new_int_var(0, count - 1, "last_read")
        model.add_max_equality(last_read, [position[u] for u in downstream])
        end = last_read + 1
        size = model.new_int_var(1, count + 1, "lifetime")
        intervals.append(model.new_interval_var(start, size, end, "live_value"))
    model.add_cumulative(intervals, [1] * len(intervals), puzzle.registers)
    for v, where in reference.items():
        if v in position and first[v] <= where <= last[v]:
            model.add_hint(position[v], where)
    solver = solver_module.CpSolver()
    solver.parameters.max_time_in_seconds = seconds
    solver.parameters.num_search_workers = workers
    status = solver.solve(model)
    tape = None
    if status in (solver_module.OPTIMAL, solver_module.FEASIBLE):
        order = sorted(graph, key=lambda v: solver.value(position[v]))
        tape = _allocate(puzzle, {v: graph[v] for v in order}, False, 0, fixed_order=True)
        if tape is None or check(puzzle, tape) != count:
            raise ValueError("Register assignment disagrees with the interval model")
    return tape, solver.status_name(status)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for field in ("puzzles", "parent", "out"):
        ap.add_argument("--" + field, type=Path, required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--root", type=int, required=True)
    ap.add_argument("--seconds", type=int, default=30)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    puzzle = next(p for p in read_puzzles(args.puzzles) if p.id == args.id)
    parent = read_submission(args.parent)[puzzle.id]
    original = first_recipes(puzzle, parent)
    graph = active_graph(puzzle, original)
    uses = Counter(source for _, a, b in graph.values() for source in {a, b}) + Counter(set(puzzle.targets))
    cut = private_cone(graph, uses, args.root)
    fixed = {v: e for v, e in graph.items() if v not in cut}
    available = set(puzzle.seeds)
    for v, (_, a, b) in fixed.items():
        if {a, b} <= available:
            available.add(v)
    replacement = inverse_chain(puzzle, args.root, available, len(cut) - 1, 12)
    if not replacement:
        raise ValueError("No shorter quotient chain")
    graph = active_graph(puzzle, fixed | replacement)
    hint = {v: i for i, v in enumerate(v for v in original if v in graph)}
    tape, status = schedule(puzzle, graph, hint, args.seconds, args.workers)
    record = dict(id=puzzle.id, root=args.root, parent_sha256=sha256(args.parent), before=len(parent),
                  graph=len(graph), status=status, scheduled=len(tape) if tape else None,
                  seconds=args.seconds, workers=args.workers)
    args.out.mkdir(exist_ok=True, parents=True)
    (args.out/"result.json").write_text(json.dumps(record, indent=2)+"\n", encoding="utf8")
    if tape and len(tape) < len(parent):
        write_submission(args.out/"wins.csv", [puzzle], {puzzle.id:tape})
    print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
