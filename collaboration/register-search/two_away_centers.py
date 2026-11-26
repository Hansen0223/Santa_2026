"""Find centers with short constructions and two-operation routes to multiple outputs."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
from itertools import combinations_with_replacement
import json
from pathlib import Path

from composed_hubs import compile_selection, removable_together
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes
from solvers.graphs.corpus_prefix import arithmetic_edges
from two_sided_chains import reverse_steps


def additions(puzzle, graph, root_limit, menu):
    known = set(puzzle.seeds) | graph.keys()
    order = {value: rank for rank, value in enumerate(graph)}
    uses = Counter(puzzle.targets)
    for _, a, b in graph.values():
        uses.update({a, b})
    old = set(puzzle.targets)
    roots = sorted(
        graph, key=lambda value: (value not in old, -uses[value], -order[value])
    )[:root_limit]
    popularity = sorted(known, key=lambda v: (v not in puzzle.seeds, -uses[v], v))
    anchors = popularity[:28]
    births = {}
    for a, b in combinations_with_replacement(sorted(known), 2):
        for value, edge in arithmetic_edges(a, b, puzzle.limit):
            if value not in known:
                births.setdefault(value, edge)
    routes = defaultdict(dict)
    for root in roots:
        for a in anchors:
            if a == root:
                continue
            for mid, last in reverse_steps(root, a, puzzle.limit):
                if mid in (root, a) or mid in puzzle.seeds:
                    continue
                if mid in births:
                    routes[mid][root] = (0, ((root, last),))
                for b in anchors:
                    if b in (root, mid):
                        continue
                    for hub, first in reverse_steps(mid, b, puzzle.limit):
                        if hub in (root, mid, b) or hub not in births:
                            continue
                        cost = int(mid not in known)
                        edges = ((root, last), (mid, first))
                        existing = routes[hub].get(root)
                        if existing is None or (cost, edges) < existing:
                            routes[hub][root] = cost, edges

    ranks = []
    for hub, support in routes.items():
        if len(support) < 2:
            continue
        reclaim = removable_together(graph, uses, set(support))
        potential = len(reclaim) - 1 - sum(cost for cost, _ in support.values())
        if potential >= -1:
            ranks.append((-potential, -len(support), hub))

    edges = {}
    for _, _, hub in sorted(ranks)[:menu]:
        edges[hub, births[hub]] = {hub: births[hub]}
        for _, path in routes[hub].values():
            for target, edge in path:
                if target not in puzzle.seeds:
                    edges[target, edge] = {target: edge}
    return list(edges.values()), len(ranks)


def trial(job):
    puzzle, tape, roots, menu = job
    graph = active_graph(puzzle, first_recipes(puzzle, tape))
    recipe_bank, eligible = additions(puzzle, graph, roots, menu)
    record = {"before": len(tape), "eligible_centers": eligible, "alternatives": len(recipe_bank)}
    if recipe_bank:
        result, candidate = compile_selection(puzzle, tape, graph, recipe_bank, False)
        record["search"] = result
    else:
        candidate = tape
    record["after"] = check(puzzle, candidate)
    return puzzle.id, candidate, record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("puzzles", "parent", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    for option, default in (("count", 56), ("roots", 24), ("menu", 18), ("jobs", 6)):
        parser.add_argument("--" + option, type=int, default=default)
    args = parser.parse_args()
    puzzles = read_puzzles(args.puzzles)
    parent = read_submission(args.parent)
    sample = [p for p in puzzles if 24 <= len(parent[p.id]) <= 190 and len(p.targets) >= 6]
    sample.sort(key=lambda p: hashlib.sha256(("two-away-1/" + p.id).encode()).digest())
    selected = sample[:args.count]
    rows, wins = {}, {}
    queue = [(p, parent[p.id], args.roots, args.menu) for p in selected]
    with ProcessPoolExecutor(args.jobs) as pool:
        for puzzle_id, result, row in pool.map(trial, queue, chunksize=1):
            rows[puzzle_id] = row
            if len(result) < len(parent[puzzle_id]):
                wins[puzzle_id] = result
                print(puzzle_id, row["before"], row["after"], flush=True)
    args.out.mkdir(exist_ok=True, parents=True)
    write_submission(args.out / "wins.csv", [p for p in puzzles if p.id in wins], wins)
    record = dict(parent_sha256=sha256(args.parent), puzzles_sha256=sha256(args.puzzles),
                  count=args.count, roots=args.roots, menu=args.menu, eligible=len(sample), rows=rows)
    (args.out / "results.json.gz").write_bytes(
        gzip.compress(json.dumps(record, separators=(",", ":")).encode(), mtime=0)
    )
    print(len(rows), len(wins), sum(rows[i]["before"] - rows[i]["after"] for i in wins))


if __name__ == "__main__":
    main()
