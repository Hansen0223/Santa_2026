"""Rewrite an intermediate and the full fanout that keeps it in an incumbent program."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
from itertools import combinations_with_replacement
import json
from pathlib import Path

from helper_triangles import removable_together
from interior_bands import compile_on_parent, solve
from quotient_chains import private_cone
from two_sided_chains import reverse_steps
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes
from solvers.graphs.corpus_prefix import arithmetic_edges


def direct(value, ready, cap):
    for anchor in sorted(ready):
        for other, edge in reverse_steps(value, anchor, cap):
            if other in ready and value not in edge[1:]:
                return edge
    if value % 2 == 0 and value // 2 in ready:
        return "+", value // 2, value // 2
    return None


def build_frontier(ordered, ready, cap):
    frontier = {}
    for a, b in combinations_with_replacement(ordered, 2):
        for value, edge in arithmetic_edges(a, b, cap):
            if value not in ready:
                frontier.setdefault(value, edge)
    return frontier


def demand(roots, ready, limit):
    required = defaultdict(dict)
    free = {}
    for root in sorted(roots):
        edge = direct(root, ready, limit)
        if edge is not None:
            free[root] = edge
        for anchor in sorted(ready):
            for next_value, recipe in reverse_steps(root, anchor, limit):
                if next_value not in ready and next_value not in roots:
                    required[next_value].setdefault(root, recipe)
    return required, free


def paired_choices(required, free, needed, ordered, ready, frontier, limit, width):
    """Offer two paid branches, including a second value computed using the first."""
    one_step = defaultdict(list)
    for v in sorted(required.keys() & frontier.keys()):
        mask = frozenset(required[v].keys() & needed)
        if mask and mask != needed:
            one_step[mask].append(v)
    kept = {
        mask: sorted(values, key=lambda v: (v.bit_length(), v))[:min(width, 6)]
        for mask, values in one_step.items()
    }
    seen = set()
    for mask, starters in sorted(kept.items(), key=lambda pair: (-len(pair[0]), sorted(pair[0]))):
        missing = needed - mask
        for first in starters:
            next_hubs = {}
            for other_mask, other_values in kept.items():
                if missing <= other_mask:
                    for second in other_values:
                        next_hubs.setdefault(second, frontier[second])
            for anchor in (*ordered, first):
                for second, edge in arithmetic_edges(first, anchor, limit):
                    if second != first and second not in ready and missing <= required.get(second, {}).keys():
                        next_hubs.setdefault(second, edge)
            for second, edge in next_hubs.items():
                key = (first, second)
                if key in seen:
                    continue
                seen.add(key)
                yield free | required[first] | required[second] | {first:frontier[first], second:edge}
                if len(seen) >= width:
                    return


def choices(roots, ready, limit, gap, width, depth, paired, stats):
    required, free = demand(roots, ready, limit)
    needed = set(roots) - free.keys()
    if not needed:
        yield free
        return
    contenders = sorted((h for h, edges in required.items() if needed <= edges.keys()),
                       key=lambda h: (-len(required[h]), h.bit_length(), h))
    stats["shared_candidates"] += len(contenders)
    ordered = sorted(ready)
    frontier = None
    for hub in contenders[:width]:
        options = {**free, **required[hub]}
        route = direct(hub, ready, limit)
        if route:
            yield options | {hub:route}
            continue
        if depth < 2 or gap < 2:
            continue
        if frontier is None:
            frontier = build_frontier(ordered, ready, limit)
        for anchor in ordered:
            matching = [(helper, edge) for helper, edge in reverse_steps(hub, anchor, limit)
                        if helper in frontier and helper != hub and helper not in roots]
            if matching:
                helper, edge = matching[0]
                yield options | {helper:frontier[helper], hub:edge}
                break
    if paired and gap >= 3 and len(needed) >= 2 and required:
        if frontier is None:
            frontier = build_frontier(ordered, ready, limit)
        for patch in paired_choices(required, free, needed, ordered, ready, frontier, limit, width):
            stats["paired_patches"] += 1
            yield patch


def work(task):
    puzzle, parent, size, width, depth, engine, rounds, paired = task
    graph = active_graph(puzzle, first_recipes(puzzle, parent))
    targets = set(puzzle.targets)
    users = defaultdict(set)
    ancestors = {v:set() for v in puzzle.seeds}
    for output, (_, a, b) in graph.items():
        ancestors[output] = {a, b} | ancestors[a] | ancestors[b]
        for value in {a, b}:
            users[value].add(output)
    uses = Counter({v:len(outputs) for v,outputs in users.items()}) + Counter(targets)
    cuts = []
    for v in graph.keys() - targets:
        outputs = users[v]
        if not 2 <= len(outputs) <= 8:
            continue
        removed = removable_together(graph, uses, outputs)
        if len(removed) < 2 or v not in removed:
            continue
        own = len(private_cone(graph, uses, v))
        cuts.append((-len(removed), -own, -len(outputs), v, removed))
    best = parent
    counts = Counter()
    alternatives = {}
    for _, _, _, v, removed in sorted(cuts)[:size]:
        roots = users[v]
        fixed = {x:edge for x,edge in graph.items() if x not in removed}
        ready = {x for x in (set(puzzle.seeds) | fixed.keys()) - roots if not ancestors[x] & roots}
        for patch in choices(roots, ready, puzzle.limit, len(removed), width, depth, paired, counts):
            counts["patches"] += 1
            tape = compile_on_parent(puzzle, parent, fixed | patch)
            if tape is None:
                continue
            counts["valid"] += 1
            best = min((best, tape), key=len)
            if engine and len(tape) <= len(parent)+1:
                distance = len(first_recipes(puzzle, tape).keys() ^ graph.keys())
                if distance >= 2:
                    alternatives[tape] = (-distance, len(tape), v)
    record = dict(before=len(parent), eligible=len(cuts), queried=min(size,len(cuts)), counts=dict(counts))
    if alternatives:
        salt = 484777 + int(puzzle.id[-4:])
        control = solve(engine, puzzle, [parent], salt, rounds)
        best = min((best, control), key=len)
        record["control"] = len(control)
        record["starts"] = []
        for start in sorted(alternatives, key=alternatives.get)[:2]:
            polished = solve(engine, puzzle, [start,parent], salt, rounds)
            best = min((best, polished), key=len)
            record["starts"].append([len(start), len(polished), *alternatives[start]])
    record["after"] = check(puzzle, best)
    return puzzle.id, best, record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("puzzles", "parent", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--engine", type=Path)
    parser.add_argument("--paired", action="store_true")
    for name, default in (("count",160),("offset",0),("cuts",7),("width",32),
                          ("depth",2),("jobs",7),("rounds",330)):
        parser.add_argument("--" + name, type=int, default=default)
    args = parser.parse_args()
    puzzles = read_puzzles(args.puzzles)
    bank = read_submission(args.parent)
    eligible = sorted((p for p in puzzles if len(bank[p.id]) >= 30),
                      key=lambda p: hashlib.sha256(("paid-fanout-" + p.id).encode()).digest())
    selected = eligible[args.offset:args.offset+args.count]
    tasks = [(p,bank[p.id],args.cuts,args.width,args.depth,args.engine,args.rounds,args.paired) for p in selected]
    wins, rows = {}, {}
    with ProcessPoolExecutor(args.jobs) as executor:
        for i, tape, row in executor.map(work,tasks,chunksize=1):
            rows[i] = row
            if len(tape) < len(bank[i]):
                wins[i] = tape
                print(i,len(bank[i]),len(tape),flush=True)
    args.out.mkdir(exist_ok=True,parents=True)
    write_submission(args.out/"wins.csv",[p for p in puzzles if p.id in wins],wins)
    receipt = dict(parent_sha256=sha256(args.parent),
                   settings={k:v for k,v in vars(args).items() if isinstance(v,int)}, rows=rows)
    if args.engine:
        receipt["engine_sha256"] = sha256(args.engine)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(receipt,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-len(t) for i,t in wins.items()),flush=True)


if __name__ == "__main__":
    main()
