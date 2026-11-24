"""Find a new arithmetic value that can generate two separate target helpers."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
from itertools import combinations_with_replacement
import json
from pathlib import Path
import sys

from quotient_chains import private_cone
from two_sided_chains import reverse_steps
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes
from solvers.graphs.corpus_prefix import arithmetic_edges

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"collaboration/structure-controls/ruler"))
from selector import compile_selection


def work(job):
    p,parent,limit,internal=job
    graph=active_graph(p,first_recipes(p,parent))
    targets=set(p.targets)
    consumers=Counter(x for _,a,b in graph.values() for x in {a,b})
    uses=consumers+Counter(targets)
    cuts={t:private_cone(graph,uses,t) for t in sorted(targets&graph.keys()) if not consumers[t]}
    if internal:
        interior = [(v,private_cone(graph,uses,v)) for v in graph
                    if v not in targets and 2<=consumers[v]<=5]
        preferred = sorted(interior,key=lambda item:(-len(item[1]),-consumers[item[0]],item[0]))
        cuts.update((v,c) for v,c in preferred[:internal] if len(c)>=3)
    weights={t:len(c)-1 for t,c in cuts.items() if len(c)>=2}
    record=dict(before=len(parent),eligible_targets=len(weights),after=len(parent))
    if len(weights)<2:
        return p.id,parent,record
    base=set(p.seeds)|graph.keys()
    pool=sorted(base-cuts.keys())
    demands=defaultdict(dict)
    for target in weights:
        for x in pool:
            if x in cuts[target]:
                continue
            for helper,edge in reverse_steps(target,x,p.limit):
                if helper not in base:
                    demands[helper].setdefault(target,edge)
    one=defaultdict(list)
    for a,b in combinations_with_replacement(pool,2):
        for v,e in arithmetic_edges(a,b,p.limit):
            if v not in base and len(one[v])<2:
                one[v].append(e)

    # Spread attention across terminal targets rather than taking every demand from the longest cone.
    ranked=defaultdict(list)
    for v,roots in demands.items():
        if v not in one:
            for t in roots:
                ranked[t].append(v)
    helpers=sorted({v for values in ranked.values() for v in sorted(
        values,key=lambda v:(-len(demands[v]), v.bit_length(), v))[:limit]})
    branches=defaultdict(dict)
    for h in helpers:
        for x in pool:
            for shared,recipe in reverse_steps(h,x,p.limit):
                if shared in one and shared!=h:
                    branches[shared].setdefault(h,recipe)
    scores=[]
    for shared,options in branches.items():
        if len(options)<2:
            continue
        affected=set().union(*(demands[h].keys() for h in options))
        if len(affected)<2:
            continue
        total=sum(weights[t] for t in affected)
        if total>3:
            scores.append((-total,shared))
    mixed=[]
    for _,shared in sorted(scores)[:24]:
        mixed.extend({shared:e} for e in one[shared])
        useful=sorted(branches[shared],key=lambda v:(-len(demands[v]),v))[:8]
        for h in useful:
            mixed.append({h:branches[shared][h]})
            mixed.extend({t:e} for t,e in demands[h].items())
    record.update(demands=len(demands),searched_helpers=len(helpers),shared_forks=len(scores),
                  offered=len(mixed))
    if not mixed:
        check(p,parent)
        return p.id,parent,record
    result,tape=compile_selection(p,parent,graph,mixed,False)
    best=min((parent,tape),key=len)
    check(p,best)
    record.update(selection=result,after=len(best))
    return p.id,best,record


def main():
    args=argparse.ArgumentParser(description=__doc__)
    for key in ("puzzles","parent","out"):
        args.add_argument("--"+key,type=Path,required=True)
    for key,value in (("count",125),("offset",0),("limit",24),("internal",0),("jobs",8)):
        args.add_argument("--"+key,type=int,default=value)
    a=args.parse_args()
    puzzles=read_puzzles(a.puzzles)
    bank=read_submission(a.parent)
    pool=sorted((p for p in puzzles if len(bank[p.id])>=45),
                key=lambda p:hashlib.sha256(("shared-fork1-"+p.id).encode()).digest())
    tasks=[(p,bank[p.id],a.limit,a.internal) for p in pool[a.offset:a.offset+a.count]]
    rows,wins={},{}
    with ProcessPoolExecutor(a.jobs) as executor:
        for i,tape,record in executor.map(work,tasks,chunksize=1):
            rows[i]=record
            if len(tape)<len(bank[i]):
                wins[i]=tape
    a.out.mkdir(exist_ok=True,parents=True)
    write_submission(a.out/"wins.csv",[p for p in puzzles if p.id in wins],wins)
    data=dict(parent_sha256=sha256(a.parent),eligible=len(pool),settings={k:v for k,v in vars(a).items() if isinstance(v,int)},rows=rows)
    (a.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(data,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-len(tape) for i,tape in wins.items()))


if __name__=="__main__":
    main()
