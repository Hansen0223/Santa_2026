"""Rebuild two targets together when their incumbent shares operations private to the pair."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
from itertools import combinations, islice
import json
from pathlib import Path

from interior_bands import compile_on_parent, solve
from two_sided_chains import arithmetic_edges, search, split_three
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes


def pair_cuts(puzzle, graph, maximum):
    targets = sorted(set(puzzle.targets) & graph.keys())
    owner = dict.fromkeys(graph, 0)
    for i, target in enumerate(targets):
        owner[target] |= 1 << i
    for output, (_, a, b) in reversed(graph.items()):
        for source in {a, b} & graph.keys():
            owner[source] |= owner[output]
    counts = Counter(owner.values())
    pairs = []
    for i, j in combinations(range(len(targets)), 2):
        first, second = 1 << i, 1 << j
        shared = counts[first | second]
        total = shared + counts[first] + counts[second]
        if shared and 5 <= total <= maximum:
            mask = first | second
            cone = {value for value, users in owner.items() if not users & ~mask}
            anchors = tuple(value for value in reversed(graph) if owner[value] == mask)
            pairs.append((-shared, total, targets[i], targets[j], cone, anchors))
    return sorted(pairs)


def construct_frontier(puzzle, pool, extra=(), base=None):
    front = {} if base is None else dict(base)
    for value in extra:
        front.pop(value, None)
    known = set(pool)
    for i, a in enumerate(pool if base is None else extra):
        partners = pool[:i+1] if base is None else pool
        for b in partners:
            for value, operation in arithmetic_edges(a, b, puzzle.limit):
                if value not in known:
                    front.setdefault(value, operation)
    return front


def arms(puzzle, output, ready, front, budget, width, splits):
    candidates = search(puzzle, output, ready, front, budget, width)
    if splits and budget >= 3:
        candidates.extend(islice(split_three(puzzle, output, front), 6))
    return sorted({frozenset(patch.items()): patch for patch in candidates}.values(),
                  key=lambda patch: (len(patch), tuple(sorted(patch))))


def joint_options(puzzle, a, b, ready, front, budget, width):
    options = {root: arms(puzzle, root, ready, front, min(7, budget-1), width, True)
               for root in (a, b)}
    patches = {}
    for left in options[a]:
        for right in options[b]:
            if len(left.keys() | right.keys()) <= budget:
                for patch in (left | right, right | left):
                    patches.setdefault(frozenset(patch.items()), (patch, "combine"))
    for first, second in ((a, b), (b, a)):
        for path in options[first][:4]:
            left = min(7, budget - len(path))
            new = tuple(sorted(path))
            enlarged = sorted(set(ready) | path.keys())
            extra = construct_frontier(puzzle, enlarged, new, front)
            for successor in arms(puzzle, second, enlarged, extra, left, width, False):
                patch = path | successor
                patches.setdefault(frozenset(patch.items()), (patch, "reuse"))
    return [len(options[a]), len(options[b])], patches.values()


def work(job):
    puzzle, parent, limit, maximum, width, keep_anchors, engine, rounds = job
    graph = active_graph(puzzle, first_recipes(puzzle, parent))
    cuts = pair_cuts(puzzle, graph, maximum)
    best = parent
    rows = []
    alternatives = {}
    for neg_shared, total, a, b, cut, anchors in cuts[:limit]:
        fixed = {value: recipe for value, recipe in graph.items() if value not in cut}
        ready = sorted(set(puzzle.seeds) | fixed.keys())
        front = construct_frontier(puzzle, ready)
        attempts = []
        for anchor in (None, *anchors[:keep_anchors]):
            prep = {} if anchor is None else {
                v:e for v,e in active_graph(puzzle, graph, targets=(anchor,)).items() if v in cut
            }
            budget = total - len(prep) + (1 if engine else -1)
            if budget < 2:
                continue
            enlarged = sorted(set(ready) | prep.keys()) if prep else ready
            new_front = construct_frontier(puzzle, enlarged, tuple(prep), front) if prep else front
            counts, patches = joint_options(puzzle, a, b, enlarged, new_front, budget, width)
            tried = Counter()
            physical = []
            ranked = sorted(patches, key=lambda item: (len(item[0]), tuple(sorted(item[0]))))
            for patch, strategy in ranked[:18]:
                tried[strategy] += 1
                candidate = compile_on_parent(puzzle, parent, patch | prep | fixed)
                if candidate is not None:
                    physical.append(len(candidate))
                    best = min((best, candidate), key=len)
                    if engine and candidate != parent and len(candidate) <= len(parent) + 1:
                        new_graph = first_recipes(puzzle, candidate)
                        distance = len(graph.keys() ^ new_graph.keys())
                        if distance >= 2:
                            alternatives[candidate] = (-distance, len(candidate), a, b, anchor)
            attempts.append(dict(anchor=anchor, prep=len(prep), arms=counts, proposed=len(ranked),
                                 tried=dict(tried), shortest=min(physical, default=None)))
        rows.append(dict(targets=[a, b], removed=total, shared=-neg_shared, attempts=attempts))
    result = dict(before=len(parent), eligible=len(cuts), pairs=rows)
    if alternatives:
        seed = 965951 + int(puzzle.id[-4:])
        control = solve(engine, puzzle, [parent], seed, rounds)
        best = min((best, control), key=len)
        result["control"] = len(control)
        result["starts"] = []
        for tape in sorted(alternatives, key=lambda t: alternatives[t][:4])[:2]:
            trial = solve(engine, puzzle, [tape, parent], seed, rounds)
            distance, length, a, b, anchor = alternatives[tape]
            result["starts"].append(dict(before=length, after=len(trial), distance=-distance,
                                         targets=[a, b], anchor=anchor))
            best = min((best, trial), key=len)
    result["after"] = check(puzzle, best)
    return puzzle.id, best, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("puzzles", "parent", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--engine", type=Path)
    for name, default in (("count", 60), ("offset", 0), ("pairs", 4), ("maximum", 16), ("width", 10),
                          ("anchors", 2), ("jobs", 10), ("rounds", 600)):
        parser.add_argument("--" + name, type=int, default=default)
    args = parser.parse_args()
    puzzles = read_puzzles(args.puzzles)
    parent = read_submission(args.parent)
    eligible = sorted((p for p in puzzles if len(parent[p.id]) >= 36),
                      key=lambda p: hashlib.sha256(("shared-pair-cut-"+p.id).encode()).digest())
    selected = eligible[args.offset:args.offset+args.count]
    tasks = [(p, parent[p.id], args.pairs, args.maximum, args.width, args.anchors, args.engine, args.rounds)
             for p in selected]
    rows, wins = {}, {}
    with ProcessPoolExecutor(args.jobs) as pool:
        for i, tape, row in pool.map(work, tasks, chunksize=1):
            rows[i] = row
            if len(tape) < len(parent[i]):
                wins[i] = tape
                print(i, len(parent[i]), len(tape), flush=True)
    args.out.mkdir(exist_ok=True, parents=True)
    write_submission(args.out / "wins.csv", [p for p in puzzles if p.id in wins], wins)
    data = dict(parent_sha256=sha256(args.parent), settings={k:v for k,v in vars(args).items() if isinstance(v,int)}, rows=rows)
    if args.engine:
        data["engine_sha256"] = sha256(args.engine)
    (args.out / "results.json.gz").write_bytes(gzip.compress(json.dumps(data,separators=(",",":")).encode(),mtime=0))
    print(len(rows), len(wins), sum(rows[i]["before"]-len(tape) for i,tape in wins.items()))


if __name__ == "__main__":
    main()
