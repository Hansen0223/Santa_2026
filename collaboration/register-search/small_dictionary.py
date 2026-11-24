"""Rebuild the small-value dictionary with exact recipe selection and rejoin the original consumers."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
import gzip
import json
from pathlib import Path
import sys

from interior_bands import compile_on_parent
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "collaboration/structure-controls/ruler"))
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, compile_graph, first_recipes
from selector import compile_selection
from solvers.graphs.corpus_prefix import arithmetic_edges


def candidates(p, graph, cap):
    # Follow the old order and include only definitions entirely inside the small-value prefix.
    available = set(p.seeds)
    region = {}
    for value, edge in graph.items():
        if value <= cap and set(edge[1:]) <= available:
            available.add(value)
            region[value] = edge
    fixed = {v: edge for v, edge in graph.items() if v not in region}
    outputs = set(region) & (set(p.targets) | {x for _, a, b in fixed.values() for x in (a, b)})
    return region, fixed, outputs


def alternatives(p, region, cap):
    old = sorted(set(p.seeds) | set(region))
    new = Counter()
    for j, a in enumerate(old):
        for b in old[:j+1]:
            for value, _ in arithmetic_edges(a, b, cap):
                if value not in region and value not in p.seeds:
                    new[value] += 1
    scores = Counter()
    for value in new:
        for operand in old:
            for result, _ in arithmetic_edges(value, operand, cap):
                if result in region:
                    scores[value] += 1
    top = sorted(scores, key=lambda v: (-scores[v], -new[v], v))[:20]
    vals = sorted(set(old) | set(top))
    usable = set(region) | set(top)
    paths = []
    for j, a in enumerate(vals):
        for b in vals[:j+1]:
            for value, recipe in arithmetic_edges(a, b, cap):
                if value in usable and value not in (a, b):
                    paths.append({value: recipe})
    return paths


def work(task):
    p, parent = task
    graph = active_graph(p, first_recipes(p, parent))
    best = parent
    details = []
    for cap in (4096, 65536, 262144):
        region, fixed, outputs = candidates(p, graph, cap)
        if not 7 <= len(region) <= 78 or len(region) <= len(outputs):
            continue
        sub = replace(p, targets=tuple(sorted(outputs)))
        start = compile_graph(sub, region)
        if start is None:
            continue
        paths = alternatives(p, region, cap)
        info, result = compile_selection(sub, start, region, paths, False)
        if len(result) < len(start):
            merged = compile_on_parent(p, parent, first_recipes(sub, result) | fixed)
            if merged is not None:
                best = min((best, merged), key=len)
        details.append(dict(limit=cap, region=len(region), outputs=len(outputs), before=len(start), **info))
    check(p, best)
    return p.id, best, dict(before=len(parent), after=len(best), passes=details)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("parent", "puzzles", "out"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--count", type=int, default=120)
    args = parser.parse_args()
    puzzles = read_puzzles(args.puzzles)
    parent = read_submission(args.parent)
    ranking = []
    for p in puzzles:
        graph = active_graph(p, first_recipes(p, parent[p.id]))
        region, _, outputs = candidates(p, graph, 65536)
        if len(region) >= 9 and len(region) > len(outputs):
            ranking.append((-(len(region)-len(outputs)), p.id, p))
    rows = {}
    wins = {}
    with ProcessPoolExecutor(args.jobs) as pool:
        for i, t, info in pool.map(work, [(p, parent[p.id]) for _, _, p in sorted(ranking)[:args.count]], chunksize=2):
            rows[i] = info
            if len(t) < len(parent[i]):
                wins[i] = t
    args.out.mkdir(parents=True, exist_ok=True)
    write_submission(args.out / "wins.csv", [p for p in puzzles if p.id in wins], wins)
    receipt = dict(parent_sha256=sha256(args.parent), eligible=len(ranking), rows=rows)
    (args.out / "results.json.gz").write_bytes(gzip.compress(json.dumps(receipt,separators=(",", ":")).encode(),mtime=0))
    print(len(rows), len(wins), sum(rows[i]["before"] - len(t) for i, t in wins.items()))


if __name__ == "__main__":
    main()