"""Optimize internal bands of a circuit using independently reachable arithmetic values as inputs."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'collaboration/retained-pool'))
from neutral_lead import solve
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, compile_graph, first_recipes
from solvers.gpu.gpu_schedule import schedule_like
from solvers.graphs.corpus_prefix import arithmetic_edges


def bands(p,graph,count):
    order = list(graph)
    positions = {v:i for i,v in enumerate(order)}
    uses = defaultdict(set)
    depth = dict.fromkeys(p.seeds,0)
    height = {}
    for v,(_,a,b) in graph.items():
        uses[a].add(v)
        uses[b].add(v)
        depth[v] = 1+max(depth[a],depth[b])
    for v in reversed(order):
        height[v] = 1+max((height[w] for w in uses[v]),default=0)
    orders = {
        'trace':order,
        'depth':sorted(order,key=lambda v:(depth[v],positions[v])),
        'height':sorted(order,key=lambda v:(-height[v],positions[v])),
    }
    goals = set(p.targets)
    candidates = []
    n = len(order)
    for axis,seq in orders.items():
        for width in sorted({max(10,min(90,round(n*f))) for f in (.21,.38,.57)}):
            for k in range(1,8):
                start = max(1,(n-width)*k//8)
                if start+width>=n:
                    continue
                block = frozenset(seq[start:start+width])
                inputs = {x for v in block for x in graph[v][1:]} - block
                outputs = {v for v in block if v in goals or uses[v]-block}
                if not 1<=len(inputs)<=p.registers-3 or not 2<=len(outputs)<=38:
                    continue
                score = (len(block)-len(outputs))/(1+len(inputs)**.5+len(outputs)**.5)
                candidates.append((-score,axis,start,width,block,inputs,outputs))
    chosen = []
    for item in sorted(candidates,key=lambda x:x[:4]):
        if any(len(item[4]&old[4])*2>len(item[4]|old[4]) for old in chosen):
            continue
        chosen.append(item)
        if len(chosen)==count:
            break
    return chosen


def arithmetic_menu(p,graph):
    values = [*dict.fromkeys(p.seeds),*graph]
    ways = defaultdict(list)
    for j,x in enumerate(values):
        for y in values[:j+1]:
            for out,recipe in arithmetic_edges(x,y,p.limit):
                if out in graph and out not in (x,y):
                    ways[out].append(recipe[1:])
    return ways


def available(p,graph,block,inputs,outputs,ways):
    safe = set(p.seeds)
    for v,(_,a,b) in graph.items():
        if v not in block and a in safe and b in safe:
            safe.add(v)
    if not inputs<=safe:
        raise ValueError('Nonconvex band')
    votes = Counter()
    for v in block:
        for a,b in ways[v]:
            if a in safe and b in safe:
                votes[a] += 1+2*(v in outputs)+(b in inputs)
                votes[b] += 1+2*(v in outputs)+(a in inputs)
    ranked = sorted(safe-inputs,key=lambda v:(-votes[v],v not in p.seeds,v))
    return tuple(sorted(inputs))+tuple(ranked[:p.registers-len(inputs)])


def compile_on_parent(p,parent,whole):
    try:
        g = active_graph(p,whole)
    except (KeyError,ValueError):
        return None
    if len(g)>len(parent)+1:
        return None
    t = schedule_like(p,parent,g)
    if t is None or len(t)>len(g):
        alt = compile_graph(p,g,attempts=4)
        if alt is not None and (t is None or len(alt)<len(t)):
            t = alt
    return t


def work(task):
    p,parent,engine,count,rounds = task
    used = active_graph(p,first_recipes(p,parent))
    # Preserve the incumbent first-occurrence order as one of the three axes.
    graph = {v:r for v,r in first_recipes(p,parent).items() if v in used}
    cuts = bands(p,graph,count)
    return run_cuts(p,parent,engine,rounds,graph,cuts,440251+int(p.id[-4:]))


def run_cuts(p,parent,engine,rounds,graph,cuts,seed):
    row = dict(before=len(parent),bands=[])
    best = parent
    if cuts:
        pairs = arithmetic_menu(p,graph)
        ordinary = solve(engine,p,[parent],seed,rounds)
        best = min((best,ordinary),key=len)
        row['control'] = len(ordinary)
        patches = []
        for _,axis,start,width,block,inputs,outputs in cuts:
            seeds = available(p,graph,block,inputs,outputs,pairs)
            inner = replace(p,seeds=seeds,targets=tuple(sorted(outputs)))
            prior = {v:r for v,r in graph.items() if v in block}
            tape = compile_graph(inner,prior,attempts=4)
            if tape is None:
                continue
            new = solve(engine,inner,[tape],seed,rounds)
            update = first_recipes(inner,new)
            fixed = {v:r for v,r in graph.items() if v not in block}
            candidate = compile_on_parent(p,parent,update|fixed)
            if candidate is None:
                candidate = compile_on_parent(p,parent,fixed|update)
            row['bands'].append(dict(axis=axis,start=start,width=width, inputs=len(inputs),
                                     extras=len(seeds)-len(inputs),outputs=len(outputs), before=len(tape),
                                     rebuilt=len(new),whole=None if candidate is None else len(candidate)))
            if candidate is not None:
                best = min((best,candidate),key=len)
                patches.append((block,update))
        # Nonoverlapping edits can still share new inputs or remove old computations.
        for j,(b,f) in enumerate(patches):
            for c,g in patches[:j]:
                if b&c:
                    continue
                fixed = {v:r for v,r in graph.items() if v not in b and v not in c}
                joined = compile_on_parent(p,parent,f|g|fixed)
                if joined is not None:
                    best = min((best,joined),key=len)
                    row['joined'] = min(row.get('joined',len(parent)),len(joined))
    check(p,best)
    return p.id,best,row


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for key in ('puzzles','parent','engine','out'):
        ap.add_argument('--'+key,type=Path,required=True)
    for key,n in [('count',100),('offset',0),('jobs',8),('bands',3),('rounds',450)]:
        ap.add_argument('--'+key,type=int,default=n)
    a = ap.parse_args()
    ps = read_puzzles(a.puzzles)
    parents = read_submission(a.parent)
    selected = sorted((p for p in ps if len(parents[p.id])>=35),key=lambda p:hashlib.sha256(('inside1-'+p.id).encode()).digest())
    tasks = [(p,parents[p.id],a.engine,a.bands,a.rounds) for p in selected[a.offset:a.offset+a.count]]
    wins,rows = {},{}
    with ProcessPoolExecutor(a.jobs) as ex:
        for i,t,row in ex.map(work,tasks):
            rows[i]=row
            if len(t)<len(parents[i]):
                wins[i]=t
    a.out.mkdir(exist_ok=True,parents=True)
    write_submission(a.out/'wins.csv',[p for p in ps if p.id in wins],wins)
    record = dict(parent_sha256=sha256(a.parent),engine_sha256=sha256(a.engine),
                  settings={k:v for k,v in vars(a).items() if isinstance(v,int)},rows=rows)
    (a.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(record,separators=(',',':')).encode(),mtime=0))
    print(len(rows),len(wins),sum(len(parents[i])-len(t) for i,t in wins.items()),flush=True)


if __name__=='__main__':
    main()
