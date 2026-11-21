"""Give a temporary puzzle one goal as input and solve part of its ancestry backwards."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'collaboration/retained-pool'))
sys.path.insert(0,str(ROOT/'collaboration/structure-controls/ruler'))
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, compile_graph, first_recipes
from neutral_lead import solve
from selector import compile_selection
from solvers.gpu.pooled_joins import inverse


def inversions(out, recipe):
    op,a,b = recipe
    if a==b:
        return
    if op=='+':
        yield a,('-',out,b)
        yield b,('-',out,a)
    elif op=='-':
        yield a,('+',out,b)
        yield b,('-',a,out)
    elif op=='*':
        yield a,('/',out,b)
        yield b,('/',out,a)
    else:
        yield a,('*',out,b)
        yield b,('/',a,out)


def paths(puzzle, graph):
    ancestors = {v:set() for v in puzzle.seeds}
    uses = Counter(x for _,a,b in graph.values() for x in {a,b})
    for v,(_,a,b) in graph.items():
        ancestors[v] = ancestors[a] | ancestors[b] | {v}
    options = []
    for t in set(puzzle.targets) & graph.keys():
        walk = [(t,{},())]
        while walk:
            current, patch, trace = walk.pop()
            if len(trace)>=4:
                continue
            for u, back in inversions(current,graph[current]):
                if u not in graph or u in back[1:]:
                    continue
                other = back[1] if back[2]==current else back[2]
                # This sibling must still be computable once the edge is reversed.
                if u in ancestors[other]:
                    continue
                updated = patch | {u:back}
                chain = (*trace,u)
                gain = min(len(ancestors[u] - ancestors[other]),40) * (1+min(uses[u],4))**.5
                if len(chain)>=2:
                    options.append((gain,t,chain,updated))
                walk.append((u,updated,chain))
    options.sort(key=lambda x:(-x[0],-len(x[2]),x[1],x[2]))
    return options


def generate(p,base,engine,seed,rounds):
    chosen = []
    seen = set()
    for _,t,chain,patch in paths(p,base):
        if t in seen:
            continue
        inner = replace(p,seeds=(*p.seeds,t),targets=tuple(sorted((set(p.targets)-{t}) | {chain[-1]})))
        try:
            rewired = active_graph(inner,base | patch)
        except (ValueError,KeyError):
            continue
        if not all(v in rewired and rewired[v]==patch[v] for v in chain):
            continue
        tape = compile_graph(inner,rewired,attempts=4)
        if not tape:
            continue
        altered = solve(engine,inner,[tape],seed,rounds)
        guide = active_graph(inner,first_recipes(inner,altered))
        chosen.append((dict(target=t,reverse_path=chain,before=len(tape),after=len(altered)),guide))
        seen.add(t)
        if len(chosen)==2:
            break
    return chosen


def work(job):
    p,tape,engine,rounds = job
    base = active_graph(p,first_recipes(p,tape))
    seed = 176811 + int(p.id[-4:])
    proposals = generate(p,base,engine,seed,rounds)
    row = dict(before=len(tape),temporary=[v for v,_ in proposals])
    best = tape
    if proposals:
        control = solve(engine,p,[tape],seed,rounds)
        best = min((best,control),key=len)
        row['control']=len(control)
        guides = [g for _,g in proposals]
        options = list(guides)
        extra = set()
        # On the official puzzle every borrowed goal must be generated.
        # Reverse new equalities and offer direct reconnections into the new values.
        values = set(base) | set(p.seeds)
        for g in guides:
            values.update(g)
        fresh = values - base.keys() - set(p.seeds)
        for g in guides:
            for v,recipe in g.items():
                if base.get(v)==recipe:
                    continue
                for u,way in inversions(v,recipe):
                    if u not in p.seeds and u not in way[1:]:
                        extra.add((u,way))
        for out in set(p.targets) | {v for note,_ in proposals for v in note['reverse_path']}:
            for operand in fresh:
                for other,recipe in inverse(out,operand,p.limit):
                    if other in values and out not in recipe[1:]:
                        extra.add((out,recipe))
        options.extend({v:e} for v,e in sorted(extra))
        detail,joined = compile_selection(p,tape,base,options,False)
        rebuilt = solve(engine,p,[joined],seed,rounds) if joined!=tape else control
        row.update(new_values=len(fresh),alternative_edges=len(extra),selection=detail,joined=len(joined),searched=len(rebuilt))
        best = min((best,joined,rebuilt),key=len)
    check(p,best)
    return p.id,best,row


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for field in ('puzzles','parent','engine','out'):
        ap.add_argument('--'+field,type=Path,required=True)
    for name,n in [('count',60),('offset',0),('jobs',6),('rounds',440)]:
        ap.add_argument('--'+name,type=int,default=n)
    args=ap.parse_args()
    puzzles=read_puzzles(args.puzzles)
    parents=read_submission(args.parent)
    selected=sorted((p for p in puzzles if len(p.seeds)<p.registers and 25<=len(parents[p.id])<=300),
                    key=lambda p:hashlib.sha256(('reverse-goals1-'+p.id).encode()).digest())
    rows,wins={},{}
    tasks=[(p,parents[p.id],args.engine,args.rounds) for p in selected[args.offset:args.offset+args.count]]
    with ProcessPoolExecutor(args.jobs) as pool:
        for i,t,row in pool.map(work,tasks):
            rows[i]=row
            if len(t)<len(parents[i]):
                wins[i]=t
    args.out.mkdir(exist_ok=True,parents=True)
    write_submission(args.out/'wins.csv',[p for p in puzzles if p.id in wins],wins)
    report=dict(parent_sha256=sha256(args.parent),engine_sha256=sha256(args.engine),
                rounds=args.rounds,offset=args.offset,rows=rows)
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(report,separators=(',',':')).encode(),mtime=0))
    print(len(rows),len(wins),sum(len(parents[i])-len(t) for i,t in wins.items()),flush=True)


if __name__=='__main__':
    main()
