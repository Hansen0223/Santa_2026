"""Resynthesize two incumbent values as different operations on one operand pair."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
from itertools import combinations, product
import json
from math import isqrt
from pathlib import Path

from helper_triangles import removable_together
from interior_bands import compile_on_parent, solve
from quotient_chains import private_cone
from two_sided_chains import reverse_steps
from elf import arithmetic, check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes


def quotient(a, b):
    return a // b if b and a % b == 0 else 0


def operands(first, second, a, b):
    """Invert an unordered operator pair with x >= y > 0."""
    pair = first + second
    if pair == "+-":
        return quotient(a + b, 2), quotient(a - b, 2)
    if pair == "+*":
        discriminant = a*a - 4*b
        if discriminant < 0:
            return 0, 0
        square = isqrt(discriminant)
        return quotient(a + square, 2), quotient(a - square, 2)
    if pair == "+/":
        y = quotient(a, b + 1)
        return b*y, y
    if pair == "-*":
        square = isqrt(a*a + 4*b)
        y = quotient(square - a, 2)
        return y+a, y
    if pair == "-/":
        y = quotient(a, b - 1)
        return b*y, y
    square = quotient(a, b)
    y = isqrt(square)
    return b*y, y


def operation_pairs(a, b, cap):
    for left, right in ((a, b), (b, a)):
        for first, second in combinations("+-*/", 2):
            x, y = operands(first, second, left, right)
            if not 0 < y <= x <= cap or {x, y} & {a, b}:
                continue
            if second == "/" and x % y:
                continue
            if arithmetic(first, x, y) == left and arithmetic(second, x, y) == right:
                yield x, y, {left: (first, x, y), right: (second, x, y)}


def births(value, ready, cap, width):
    if value in ready:
        return [None]
    recipes = {}
    for endpoint in sorted(ready):
        for operand, edge in reverse_steps(value, endpoint, cap):
            if operand not in ready:
                continue
            op, left, right = edge
            if op in "+*":
                edge = (op, min(left, right), max(left, right))
            recipes[edge] = edge
            if len(recipes) == width:
                return list(recipes)
    return list(recipes)


def shifted_pairs(a, b, neighbors, ready, cap):
    """Allow an additional operation on either output using a retained value."""
    for fixed, shifted in ((a, b), (b, a)):
        for anchor in neighbors[shifted]:
            if anchor not in ready:
                continue
            for middle, recipe in reverse_steps(shifted, anchor, cap):
                if middle in (fixed, shifted, anchor):
                    continue
                for x, y, outputs in operation_pairs(fixed, middle, cap):
                    if shifted not in (x, y):
                        yield x, y, outputs | {shifted: recipe}, middle


def work(job):
    p, parent, width, cap, engine, rounds, shifts = job
    graph = active_graph(p, first_recipes(p, parent))
    wants = set(p.targets)
    uses = Counter(source for _, a, b in graph.values() for source in {a, b}) + Counter(wants)
    private = {v: len(private_cone(graph, uses, v)) for v in graph}
    roots = sorted(graph, key=lambda v: (-private[v], v not in wants, uses[v], v))[:cap]
    ancestors = {v: set() for v in p.seeds}
    for v, (_, a, b) in graph.items():
        ancestors[v] = ancestors[a] | ancestors[b] | {a, b}
    available = set(p.seeds) | graph.keys()
    frequent = sorted(available, key=lambda v: (-uses[v], v))[:shifts]
    neighbors = {v: tuple(dict.fromkeys((*graph[v][1:], *frequent))) for v in roots}
    combos = Counter()
    warm = {}
    best = parent
    for a, b in combinations(roots, 2):
        cut = removable_together(graph, uses, {a, b})
        if len(cut) < 2:
            continue
        combos["eligible"] += 1
        safe = {v for v in available - cut - {a, b} if not {a, b} & ancestors[v]}
        generated = [(x, y, outputs, None) for x,y,outputs in operation_pairs(a, b, p.limit)]
        if shifts and len(cut) >= 3:
            generated.extend(shifted_pairs(a, b, neighbors, safe, p.limit))
        if not generated:
            continue
        kept = {v:e for v,e in graph.items() if v not in cut}
        for x, y, outputs, middle in generated:
            if middle in safe:
                continue
            new = {x, y} - safe
            price = len(new) + (middle is not None)
            if not new or price > len(cut):
                continue
            ingredients = sorted(new)
            construction = [births(v, safe, p.limit, width) for v in ingredients]
            if not all(construction):
                continue
            combos["shifted" if middle is not None else "constructible"] += 1
            for pair in product(*construction):
                patch = dict(zip(ingredients, pair))
                tape = compile_on_parent(p, parent, kept | patch | outputs)
                if tape is None:
                    continue
                combos["compiled"] += 1
                best = min((best, tape), key=len)
                if engine and len(tape) <= len(parent) + 1:
                    new_values = first_recipes(p, tape).keys()
                    distance = len(graph.keys() ^ new_values)
                    if distance >= 2:
                        warm[tape] = (-distance, len(tape), a, b)
    info = dict(before=len(parent), counts=dict(combos))
    if warm:
        seed = 464631 + int(p.id[-4:])
        direct = solve(engine, p, [parent], seed, rounds)
        best = min((best, direct), key=len)
        info["control"] = len(direct)
        info["starts"] = []
        for start in sorted(warm, key=lambda t: warm[t])[:2]:
            polished = solve(engine, p, [start, parent], seed, rounds)
            best = min((best, polished), key=len)
            info["starts"].append([len(start), len(polished), *warm[start]])
    info["after"] = check(p, best)
    return p.id, best, info


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("puzzles", "parent", "out"):
        cli.add_argument("--" + name, type=Path, required=True)
    cli.add_argument("--engine", type=Path)
    for name, default in (("count", 150), ("offset", 0), ("width", 3), ("roots", 54),
                          ("jobs", 7), ("rounds", 420), ("shifts", 0)):
        cli.add_argument("--" + name, type=int, default=default)
    args = cli.parse_args()
    puzzles = read_puzzles(args.puzzles)
    parent = read_submission(args.parent)
    eligible = sorted((p for p in puzzles if len(parent[p.id]) >= 28),
                      key=lambda p: hashlib.sha256(("dual-operation-" + p.id).encode()).digest())
    selected = eligible[args.offset:args.offset + args.count]
    jobs = [(p, parent[p.id], args.width, args.roots, args.engine, args.rounds, args.shifts) for p in selected]
    wins, rows = {}, {}
    with ProcessPoolExecutor(args.jobs) as pool:
        for identifier, tape, detail in pool.map(work, jobs):
            rows[identifier] = detail
            if len(tape) < len(parent[identifier]):
                wins[identifier] = tape
                print(identifier, len(parent[identifier]), len(tape), flush=True)
    args.out.mkdir(parents=True, exist_ok=True)
    write_submission(args.out / "wins.csv", [p for p in puzzles if p.id in wins], wins)
    settings = {k:v for k,v in vars(args).items() if isinstance(v, int)}
    report = dict(parent_sha256=sha256(args.parent), settings=settings, eligible=len(eligible), rows=rows)
    if args.engine:
        report["engine_sha256"] = sha256(args.engine)
    (args.out / "results.json.gz").write_bytes(
        gzip.compress(json.dumps(report, separators=(",", ":")).encode(), mtime=0)
    )
    print(len(rows), len(wins), sum(rows[i]["before"] - len(t) for i,t in wins.items()), flush=True)


if __name__ == "__main__":
    main()
