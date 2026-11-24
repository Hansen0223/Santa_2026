"""Select three paid helper values when the third combines the first two."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
from itertools import combinations, combinations_with_replacement
import json
from pathlib import Path
import sys

from interior_bands import ROOT
from quotient_chains import private_cone
from two_sided_chains import reverse_steps
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes
from solvers.graphs.corpus_prefix import arithmetic_edges

sys.path.insert(0, str(ROOT / "collaboration/structure-controls/ruler"))
from selector import compile_selection


def removable_together(graph, uses, roots):
    """Count old computations that could disappear together before paying for replacements."""
    removed = set(roots)
    removed_uses = Counter()
    pending = list(roots)
    while pending:
        source = pending.pop()
        for operand in set(graph[source][1:]) & graph.keys():
            if operand in removed:
                continue
            removed_uses[operand] += 1
            if removed_uses[operand] == uses[operand]:
                removed.add(operand)
                pending.append(operand)
    return removed - roots


def search_menu(puzzle, graph, width, groups, allow_direct, joint=False):
    targets = set(puzzle.targets)
    consumers = Counter(source for _, a, b in graph.values() for source in {a, b})
    uses = consumers + Counter(targets)
    cuts = {value: private_cone(graph, uses, value) for value in graph}
    if not joint:
        cuts = {root: cone for root, cone in cuts.items() if len(cone) >= 2}
    if len(cuts) < 3:
        return [], [], dict(roots=len(cuts))
    original = set(puzzle.seeds) | graph.keys()
    valued = sorted(original)
    ancestors = {value: set() for value in puzzle.seeds}
    for value, (_, a, b) in graph.items():
        ancestors[value] = ancestors[a] | ancestors[b] | {a, b}
    needs = defaultdict(dict)
    for root, cone in cuts.items():
        for operand in valued:
            if operand in cone or root in ancestors[operand]:
                continue
            for helper, edge in reverse_steps(root, operand, puzzle.limit):
                if helper not in original:
                    needs[helper].setdefault(root, edge)

    birth = defaultdict(list)
    for a, b in combinations_with_replacement(valued, 2):
        for value, edge in arithmetic_edges(a, b, puzzle.limit):
            if value in needs and len(birth[value]) < 3:
                birth[value].append(edge)
    impact = {
        v: sum(4*(len(cuts[root]) - 1) + int(joint) for root in needs[v] if any(
            all(operand not in cuts[root] and root not in ancestors[operand] for operand in e[1:]) for e in es
        ))
        for v, es in birth.items()
    }
    lead = sorted((v for v in birth if impact[v]), key=lambda v: (-impact[v], -len(needs[v]), v))[:width]
    joined = {}
    for a, b in combinations(lead, 2):
        for c, edge in arithmetic_edges(a, b, puzzle.limit):
            if (c in birth and not allow_direct) or c not in needs or c in (a, b):
                continue
            roots = needs[a].keys() | needs[b].keys() | needs[c].keys()
            if len(roots) < 3 or not needs[c].keys() - (needs[a].keys() | needs[b].keys()):
                continue
            if joint:
                removable = removable_together(graph, uses, roots)
            else:
                removable = set().union(*(cuts[root] - roots for root in roots))
            if len(removable) <= 3:
                continue
            key = (min(a, b), max(a, b), c)
            joined.setdefault(key, (-len(removable), c, edge, roots))

    control, treatment = {}, {}
    for (a, b, c), (_, _, edge, _) in sorted(joined.items(), key=lambda x:(x[1][:3],x[0]))[:groups]:
        for helper in (a, b, c):
            for path in birth.get(helper, ()):
                control[helper, path] = {helper: path}
            for root, path in needs[helper].items():
                edges = control if helper in birth else treatment
                edges[root, path] = {root: path}
        treatment[c, edge] = {c: edge}
    return list(control.values()), list(treatment.values()), dict(
        roots=len(cuts), birth=len(birth), lead=len(lead), joined=len(joined))


def work(job):
    puzzle, parent, width, groups, allow_direct, joint = job
    graph = active_graph(puzzle, first_recipes(puzzle, parent))
    direct, nested, detail = search_menu(puzzle, graph, width, groups, allow_direct, joint)
    best = parent
    info = dict(before=len(parent), menu=detail)
    if nested:
        info["control"], plain = compile_selection(puzzle, parent, graph, direct, False)
        info["join"], compound = compile_selection(puzzle, parent, graph, direct + nested, False)
        best = min((parent, plain, compound), key=len)
    info["after"] = check(puzzle, best)
    return puzzle.id, best, info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("puzzles", "parent", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--allow-direct", action="store_true")
    parser.add_argument("--joint", action="store_true", help="Also price dependencies shared by several replaced roots.")
    for name, default in (("count", 120), ("width", 80), ("groups", 24), ("offset", 0), ("jobs", 10)):
        parser.add_argument("--" + name, type=int, default=default)
    args = parser.parse_args()
    puzzles = read_puzzles(args.puzzles)
    original = read_submission(args.parent)
    selected = sorted((p for p in puzzles if len(original[p.id]) >= 40),
                      key=lambda p: hashlib.sha256(("three-helper-join-" + p.id).encode()).digest())
    rows, wins = {}, {}
    cohort = selected[args.offset:args.offset + args.count]
    with ProcessPoolExecutor(args.jobs) as pool:
        tasks = [(p, original[p.id], args.width, args.groups, args.allow_direct, args.joint) for p in cohort]
        for i, tape, row in pool.map(work, tasks, chunksize=1):
            rows[i] = row
            if len(tape) < len(original[i]):
                wins[i] = tape
                print(i, len(original[i]), len(tape), flush=True)
    args.out.mkdir(exist_ok=True, parents=True)
    write_submission(args.out / "wins.csv", [p for p in puzzles if p.id in wins], wins)
    settings = {k:v for k,v in vars(args).items() if isinstance(v,int)}
    data = dict(parent_sha256=sha256(args.parent), settings=settings, rows=rows, eligible=len(selected))
    (args.out / "results.json.gz").write_bytes(gzip.compress(json.dumps(data,separators=(",",":")).encode(),mtime=0))
    print(len(rows), len(wins), sum(rows[i]["before"]-len(tape) for i,tape in wins.items()))


if __name__ == "__main__":
    main()
