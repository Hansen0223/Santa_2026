"""Move one common factor through a circuit, allowing different operations to carry it."""
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
sys.path.insert(0, str(ROOT/'collaboration/structure-controls/ruler'))
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes
from selector import compile_selection


def common_factors(p, graph):
    values = graph.keys() | set(p.seeds)
    support = Counter()
    for v, (op, a, b) in graph.items():
        if op == '*':
            support.update({a, b})
        elif op == '/':
            support[b] += 1
    ranked = []
    for k, count in support.items():
        if k <= 1:
            continue
        shared = sum(v*k in values for v in values)
        if shared >= 2:
            ranked.append((count + shared, shared, k))
    return [k for _, _, k in sorted(ranked, key=lambda item: (-item[0], -item[1], item[2]))]


def factor_edges(p, graph, k):
    seeds = set(p.seeds)
    originals = graph.keys() | seeds
    levels = {}
    for x in originals:
        states = {0:x}
        if x*k <= p.limit:
            states[1] = x*k
        if x%k == 0:
            states[-1] = x//k
        levels[x] = states
    menu = defaultdict(set)

    def offer(v, op, a, b):
        if v in seeds or v in (a, b):
            return
        if op in '+*':
            a, b = min(a,b), max(a,b)
        menu[v].add((op,a,b))

    for x, states in levels.items():
        if 1 in states:
            offer(states[1], '*', x, k)
            offer(x, '/', states[1], k)
        if -1 in states:
            offer(x, '*', states[-1], k)
            offer(states[-1], '/', x, k)
    for v, (op, a, b) in graph.items():
        for i, left in levels[a].items():
            for j, right in levels[b].items():
                if op in '+-' and i != j:
                    continue
                exponent = i+j if op == '*' else i-j if op == '/' else i
                if exponent in levels[v]:
                    offer(levels[v][exponent], op, left, right)

    # Remove variants without a route from the original values, including cycles
    # in which each state could only be defined through a complementary state.
    available = set(originals)
    while True:
        extra = {v for v, choices in menu.items() if v not in available and
                 any(a in available and b in available for _,a,b in choices)}
        if not extra:
            break
        available.update(extra)
    paths = []
    for v, choices in menu.items():
        for edge in sorted(choices):
            if v in available and all(x in available for x in edge[1:]) and graph.get(v) != edge:
                paths.append({v:edge})
    return paths, len(available-originals)


def work(task):
    p,tape,count = task
    graph = active_graph(p,first_recipes(p,tape))
    factors = common_factors(p,graph)[:count]
    best = tape
    trials = []
    for k in factors:
        paths,added = factor_edges(p,graph,k)
        result, candidate = compile_selection(p,tape,graph,paths,False)
        trials.append(dict(factor=k,new_values=added,**result))
        if len(candidate) < len(best):
            best = candidate
    check(p,best)
    return p.id,best,dict(before=len(tape),after=len(best),trials=trials)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('puzzles','parent','out'):
        parser.add_argument('--'+name, type=Path, required=True)
    for name, default in [('count',40),('factors',3),('jobs',4),('offset',0)]:
        parser.add_argument('--'+name, type=int, default=default)
    args = parser.parse_args()
    puzzles = read_puzzles(args.puzzles)
    parents = read_submission(args.parent)
    selected = sorted((p for p in puzzles if 25 <= len(parents[p.id]) <= 200),
                      key=lambda p:hashlib.sha256(('factor-motion-'+p.id).encode()).digest())
    tasks = [(p,parents[p.id],args.factors) for p in selected[args.offset:args.offset+args.count]]
    wins,rows = {},{}
    with ProcessPoolExecutor(args.jobs) as pool:
        for i,t,row in pool.map(work,tasks):
            rows[i] = row
            if len(t) < len(parents[i]):
                wins[i] = t
    args.out.mkdir(exist_ok=True, parents=True)
    write_submission(args.out/'wins.csv',[p for p in puzzles if p.id in wins],wins)
    report = dict(parent_sha256=sha256(args.parent),settings={k:v for k,v in vars(args).items() if isinstance(v,int)},rows=rows)
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(report,separators=(',',':')).encode(),mtime=0))
    print(len(rows),len(wins),sum(len(parents[i])-len(t) for i,t in wins.items()))


if __name__ == '__main__':
    main()
