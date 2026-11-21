"""Resynthesize local arithmetic cones using scaled or translated intermediate values."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from elf import read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, compile_graph, first_recipes
from solvers.gpu.gpu_schedule import schedule_like


def proposals(puzzle, graph, count):
    users = defaultdict(set)
    for v, (_, a, b) in graph.items():
        users[a].add(v)
        users[b].add(v)
    goals = set(puzzle.targets)
    options = {}
    for v in graph:
        members = {v}
        wave = {v}
        for _ in range(4):
            wave = {x for q in wave for x in graph[q][1:] if x in graph and x not in members}
            if not wave or len(members) + len(wave) > 21:
                break
            members.update(wave)
            if len(members) < 5:
                continue
            ports = {x for x in members if users[x] - members or x in goals}
            hidden = members - ports
            if len(hidden) < 3:
                continue
            # Prefer cuts whose original computation can actually disappear.
            rank = (len(hidden) / (1 + len(ports)**.5), len(hidden))
            options[frozenset(members)] = (rank, ports)
    chosen = []
    for region, (_, ports) in sorted(options.items(), key=lambda item: item[1][0], reverse=True):
        if any(len(region & other) * 3 > 2 * len(region | other) for other, _ in chosen):
            continue
        chosen.append((region, ports))
        if len(chosen) == count:
            break
    return chosen


def variants(region, inputs, free, cap, mode):
    members = region | inputs
    if mode == 'scale':
        counts = Counter(k for k in (2, 3, 5, 7, 10) for x in members if x * k in free or x * k in members)
        factors = sorted((2, 3, 5, 7, 10), key=lambda k: (-counts[k], k))[:2]
        return {y for x in members for k in factors for y in (x*k, x//k if x%k==0 else 0) if 0<y<=cap}
    if mode == 'offset':
        offsets = Counter()
        small = sorted((free | members) & set(range(1, 65)))
        for x in members:
            for k in small:
                if x+k in members or x+k in free:
                    offsets[k] += 1
        steps = sorted(small, key=lambda k: (-offsets[k], k))[:3]
        return {x+s for x in members for k in steps for s in (k, -k) if 0<x+s<=cap}
    return set()


def recipes_for(v, values, free):
    # For a fixed output, equivalent choices with the same paid operands cost the same.
    candidates = {}
    for a in values:
        if v == a:
            continue
        for op, left, right, other in (
            ('+', a, v-a, v-a), ('-', v+a, a, v+a), ('-', a, a-v, a-v),
            ('*', a, v//a, v//a if v%a==0 else 0),
            ('/', v*a, a, v*a), ('/', a, a//v, a//v if a%v==0 else 0)
        ):
            if other == v or other not in values:
                continue
            paid = frozenset(x for x in (left, right) if x not in free)
            if not paid:
                return {paid: (op, left, right)}
            candidates.setdefault(paid, (op, left, right))
    singles = {next(iter(key)) for key in candidates if len(key) == 1}
    return {key: r for key, r in candidates.items() if len(key) == 1 or key.isdisjoint(singles)}


def select(graph, puzzle, region, ports, mode, budget):
    from ortools.sat.python import cp_model
    # Values depending on an exit can only be reused after it has been rebuilt.
    blocked = set(region)
    for v, (_, a, b) in graph.items():
        if a in blocked or b in blocked:
            blocked.add(v)
    free = set(puzzle.seeds) | (graph.keys() - blocked)
    inputs = {x for v in region for x in graph[v][1:]} - region
    new = variants(region, inputs, free, puzzle.limit, mode)
    paid = (region | new) - free
    values = paid | free
    ways = {}
    queue = list(ports)
    while queue:
        v = queue.pop()
        if v in ways:
            continue
        ways[v] = recipes_for(v, values, free)
        for deps in ways[v]:
            queue.extend(deps - ways.keys())
    model = cp_model.CpModel()
    present = {v: model.new_bool_var('') for v in ways}
    rank = {v: model.new_int_var(0, len(ways), '') for v in ways}
    choices = {}
    for v, options in ways.items():
        if v in ports:
            model.add(present[v] == 1)
        terms = []
        for deps, recipe in options.items():
            take = model.new_bool_var('')
            terms.append(take)
            choices[v, recipe] = take
            for w in deps:
                model.add_implication(take, present[w])
                model.add(rank[w] < rank[v]).only_enforce_if(take)
        model.add(sum(terms) == present[v])
    size = sum(present.values())
    model.add(size < len(region))
    model.minimize(size)
    solver = cp_model.CpSolver()
    solver.parameters.max_deterministic_time = budget
    solver.parameters.num_search_workers = 1
    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None, solver.status_name(status)
    return {v: r for (v, r), take in choices.items() if solver.value(take)}, solver.status_name(status)


def work(task):
    puzzle, parent, count, budget, modes = task
    graph = active_graph(puzzle, first_recipes(puzzle, parent))
    regions = proposals(puzzle, graph, count)
    best = parent
    stats = {}
    for mode in modes:
        scores = Counter()
        best_mode = len(parent)
        for region, ports in regions:
            patch, status = select(graph, puzzle, region, ports, mode, budget)
            scores[status] += 1
            if patch is None:
                continue
            try:
                candidate = active_graph(puzzle, graph | patch)
            except ValueError:
                continue
            if len(candidate) >= best_mode:
                continue
            tape = compile_graph(puzzle, candidate)
            if tape is None:
                tape = schedule_like(puzzle, parent, candidate)
            if tape is not None and len(tape) < best_mode:
                best_mode = len(tape)
                if len(tape) < len(best):
                    best = tape
        stats[mode] = dict(scores, length=best_mode)
    return puzzle.id, best, dict(before=len(parent), cuts=len(regions), modes=stats)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for key in ('puzzles', 'parent', 'out'):
        ap.add_argument('--'+key, type=Path, required=True)
    ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--count', type=int, default=48)
    ap.add_argument('--offset', type=int, default=0)
    ap.add_argument('--cuts', type=int, default=8)
    ap.add_argument('--budget', type=float, default=.035)
    ap.add_argument('--modes', nargs='+', choices=['scale','offset','original'], default=['original','scale','offset'])
    args = ap.parse_args()
    ps = read_puzzles(args.puzzles)
    parent = read_submission(args.parent)
    group = sorted((p for p in ps if len(parent[p.id])>=35),
                   key=lambda p:hashlib.sha256(('lifted-'+p.id).encode()).digest())[args.offset:args.offset+args.count]
    args.out.mkdir(parents=True, exist_ok=True)
    rows, wins = {}, {}
    with ProcessPoolExecutor(args.jobs) as pool:
        for i, tape, row in pool.map(work, [(p,parent[p.id],args.cuts,args.budget,args.modes) for p in group]):
            rows[i] = row
            if len(tape)<len(parent[i]):
                wins[i] = tape
    write_submission(args.out/'wins.csv', [p for p in ps if p.id in wins], wins)
    record = dict(parent_sha256=sha256(args.parent), budget=args.budget, offset=args.offset, cuts=args.cuts, rows=rows)
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(record,separators=(',',':')).encode(),mtime=0))
    print(len(rows), len(wins), sum(len(parent[i])-len(tape) for i,tape in wins.items()), flush=True)


if __name__ == '__main__':
    main()
