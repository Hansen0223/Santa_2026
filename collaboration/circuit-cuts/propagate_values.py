"""Substitute an available number for an internal value and rerun its downstream arithmetic."""
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
sys.path.insert(0, str(ROOT / 'collaboration/retained-pool'))
from neutral_lead import solve
from elf import arithmetic, check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, compile_graph, first_recipes
from solvers.gpu.gpu_schedule import schedule_like
from solvers.gpu.pooled_joins import inverse


def regions(puzzle, graph, count):
    users = defaultdict(set)
    for v, (_, a, b) in graph.items():
        users[a].add(v)
        users[b].add(v)
    goals = set(puzzle.targets)
    descendants = {}
    for v in reversed(graph):
        descendants[v] = {v}.union(*(descendants[w] for w in users[v]))
    seen = set()
    choices = []
    for root in graph.keys() - goals:
        region = {root}
        wave = {root}
        for depth in range(1, 6):
            wave = {u for v in wave for u in users[v]} - region
            if not wave:
                break
            region.update(wave)
            if len(region) > 15:
                break
            if len(region) < 3:
                continue
            ports = frozenset(v for v in region if v in goals or users[v] - region)
            if not 1 <= len(ports) <= 3 or root in ports:
                continue
            key = root, ports
            if key in seen:
                continue
            seen.add(key)
            # Prefer deep edits and branches with few old values to restore.
            rank = (len(region) - len(ports)) / (1 + len(ports))
            choices.append((-rank, -depth, root, ports, frozenset(region)))
    taken = Counter()
    used = []
    for _, _, root, ports, region in sorted(choices, key=lambda c:(c[:3],sorted(c[3]))):
        if taken[root] == 2 or any(len(region & q) * 5 > 4 * len(region | q) for q in used):
            continue
        used.append(region)
        taken[root] += 1
        yield root, ports, [v for v in graph if v in region], descendants[root]
        if len(used) == count:
            break


def restore(goal, preferred, known, cap):
    for x in preferred:
        for y, recipe in inverse(goal, x, cap):
            if goal not in recipe[1:] and y in known:
                return recipe
    return None


def trials(puzzle, graph, region, width, metrics):
    root, ports, order, descendants = region
    seeds = set(puzzle.seeds)
    fixed = (graph.keys() | seeds) - descendants
    inputs = [x for v in order for x in graph[v][1:] if x in fixed]
    # Mix inputs of this region, numerically close values and a spread of sizes.
    values = sorted(fixed)
    near = sorted(fixed, key=lambda x:(abs(x - root), x))
    spread = [values[j * len(values) // width] for j in range(width)] if values else []
    substitutions = list(dict.fromkeys([*puzzle.seeds, *inputs, *near[:width//2], *spread, *near]))[:width]
    existing = {v:recipe for v, recipe in graph.items() if v not in order}
    fallback = {g:restore(g, values, fixed, puzzle.limit) for g in ports}
    for sub in substitutions:
        metrics['substitutions'] += 1
        mapping = {root:sub}
        patch = {}
        try:
            for v in order[1:]:
                op, a, b = graph[v]
                a, b = mapping.get(a,a), mapping.get(b,b)
                new = arithmetic(op,a,b)
                if not 1 <= new <= puzzle.limit:
                    break
                mapping[v] = new
                if new not in fixed and new not in patch:
                    patch[new] = (op,a,b)
            else:
                if not patch:
                    continue
                metrics['within_limit'] += 1
                known = fixed | patch.keys()
                for goal in sorted(ports):
                    if goal in known:
                        continue
                    preferred = dict.fromkeys([mapping[goal], *reversed(patch)])
                    recipe = restore(goal, preferred, known, puzzle.limit) or fallback[goal]
                    if recipe is None:
                        break
                    patch[goal] = recipe
                    known.add(goal)
                else:
                    metrics['restored'] += 1
                    new_values = patch.keys() - graph.keys()
                    if not new_values:
                        continue
                    try:
                        candidate = active_graph(puzzle, existing | patch)
                    except (KeyError, ValueError):
                        continue
                    if candidate.keys() & new_values:
                        yield candidate, (root, sub, len(order), len(ports))
        except ValueError:
            # Exact division can stop being valid after an operand changes.
            continue


def work(task):
    puzzle, parent, engine, cases, width, rounds = task
    base = active_graph(puzzle, first_recipes(puzzle, parent))
    metrics = Counter()
    best = parent
    starts = []
    seen = set()
    for region in regions(puzzle, base, cases):
        metrics['regions'] += 1
        for graph, record in trials(puzzle, base, region, width, metrics):
            if len(graph) > len(parent) + 2:
                continue
            delta = frozenset((v,r) for v,r in graph.items() if base.get(v) != r)
            if delta in seen:
                continue
            seen.add(delta)
            starts.append((len(graph),record,delta,graph))
    rows = []
    chosen = []
    for _,record,delta,graph in sorted(starts,key=lambda x:(x[0],-len(x[2]),x[1])):
        if any(len(delta ^ prev) < 3 for prev in chosen):
            continue
        tape = compile_graph(puzzle,graph,attempts=4)
        if tape is None:
            tape = schedule_like(puzzle,parent,graph)
        if tape and len(tape) <= len(parent)+2:
            chosen.append(delta)
            rows.append((tape,record))
            if len(rows)==2:
                break
    metrics['distinct_candidates'] = len(seen)
    result = dict(before=len(parent), metrics=dict(metrics), starts=[])
    if rows:
        seed = 259127 + int(puzzle.id[-4:])
        control = solve(engine,puzzle,[parent],seed,rounds)
        result['control'] = len(control)
        best = min((best,control),key=len)
        for tape,record in rows:
            polished = solve(engine,puzzle,[tape],seed,rounds)
            result['starts'].append(dict(region=record,raw=len(tape),searched=len(polished)))
            best = min((best,tape,polished),key=len)
    check(puzzle,best)
    return puzzle.id,best,result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for arg in ('puzzles','parent','engine','out'):
        ap.add_argument('--'+arg,type=Path,required=True)
    for name,n in [('count',100),('offset',0),('cases',24),('width',64),('rounds',420),('jobs',6)]:
        ap.add_argument('--'+name,type=int,default=n)
    a = ap.parse_args()
    puzzles = read_puzzles(a.puzzles)
    parents = read_submission(a.parent)
    selected = sorted((p for p in puzzles if len(parents[p.id])>=25),
                      key=lambda p:hashlib.sha256(('propagate-1-'+p.id).encode()).digest())
    tasks = [(p,parents[p.id],a.engine,a.cases,a.width,a.rounds) for p in selected[a.offset:a.offset+a.count]]
    rows,wins = {},{}
    with ProcessPoolExecutor(a.jobs) as pool:
        for i,t,record in pool.map(work,tasks):
            rows[i] = record
            if len(t)<len(parents[i]):
                wins[i]=t
    a.out.mkdir(exist_ok=True,parents=True)
    write_submission(a.out/'wins.csv',[p for p in puzzles if p.id in wins],wins)
    report = dict(parent_sha256=sha256(a.parent),engine_sha256=sha256(a.engine),
                  settings={k:v for k,v in vars(a).items() if isinstance(v,int)},rows=rows)
    (a.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(report,separators=(',',':')).encode(),mtime=0))
    print(len(rows),len(wins),sum(len(parents[i])-len(t) for i,t in wins.items()),flush=True)


if __name__=='__main__':
    main()
