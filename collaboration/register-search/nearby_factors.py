"""Factor nearby integers to propose products of two newly constructed operands."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
from itertools import combinations_with_replacement
import json
from pathlib import Path

from quotient_chains import private_cone
from interior_bands import compile_on_parent
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes
from solvers.graphs.corpus_prefix import arithmetic_edges


def factors(n):
    # An incomplete factorization is sufficient to generate verified divisors.
    from sympy import factorint
    divisors=[1]
    for prime,power in factorint(n,limit=1800).items():
        divisors=[v*int(prime)**j for v in divisors for j in range(power+1)]
    return sorted(d for d in divisors if 1<d<=n//d and n%d==0)


def work(job):
    p,parent,ncuts=job
    graph=active_graph(p,first_recipes(p,parent))
    used=Counter(x for _,a,b in graph.values() for x in {a,b})
    cones=[]
    for v in graph:
        if used[v]>1 or v.bit_length()<20:
            continue
        cone=private_cone(graph,used+Counter(set(p.targets)),v)
        if len(cone)>=5:
            cones.append((-len(cone),-v.bit_length(),v,cone))
    best=parent
    trials=[]
    for _,_,root,cut in sorted(cones)[:ncuts]:
        fixed={v:e for v,e in graph.items() if v not in cut}
        ready=set(p.seeds)
        for v,(_,a,b) in fixed.items():
            if a in ready and b in ready:
                ready.add(v)
        ready_list=sorted(ready)
        forward={}
        for a,b in combinations_with_replacement(ready_list,2):
            for value,e in arithmetic_edges(a,b,p.limit):
                if value not in ready:
                    forward.setdefault(value,e)
        palette=sorted(ready,key=lambda v:(v not in p.seeds,-used[v],v.bit_length(),v))[:14]
        checked=tries=0
        found=None
        for rem in [0,*palette]:
            for sign in ((1,) if rem==0 else (1,-1)):
                product=root-sign*rem
                if not 1<product<=p.limit:
                    continue
                for a in factors(product):
                    b=product//a
                    if a in ready or b in ready:
                        continue
                    if a not in forward or b not in forward or root in (a,b):
                        continue
                    checked+=1
                    new={a:forward[a],b:forward[b],product:("*",a,b)}
                    if rem:
                        new[root]=("+" if sign>0 else "-",product,rem)
                    if len(new)>=len(cut):
                        continue
                    tries+=1
                    t=compile_on_parent(p,parent,new|fixed)
                    if t is not None:
                        found=len(t) if found is None else min(len(t),found)
                        if len(t)<len(best):
                            best=t
        trials.append(dict(root=root,cone=len(cut),checked=checked,tries=tries,scheduled=found))
    check(p,best)
    return p.id,best,dict(before=len(parent),after=len(best),eligible=len(cones),trials=trials)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ("puzzles","parent","out"):
        ap.add_argument("--"+name,type=Path,required=True)
    for name,v in (("count",90),("cuts",3),("jobs",8)):
        ap.add_argument("--"+name,type=int,default=v)
    args=ap.parse_args()
    ps=read_puzzles(args.puzzles)
    parent=read_submission(args.parent)
    order=sorted((p for p in ps if len(parent[p.id])>=45),
                 key=lambda p:hashlib.sha256(("nearby-factor-"+p.id).encode()).digest())
    jobs=[(p,parent[p.id],args.cuts) for p in order[:args.count]]
    rows,wins={},{}
    with ProcessPoolExecutor(args.jobs) as pool:
        for i,t,r in pool.map(work,jobs,chunksize=2):
            rows[i]=r
            if len(t)<len(parent[i]):
                wins[i]=t
    args.out.mkdir(exist_ok=True,parents=True)
    write_submission(args.out/"wins.csv",[p for p in ps if p.id in wins],wins)
    info=dict(parent_sha256=sha256(args.parent),settings={k:v for k,v in vars(args).items() if isinstance(v,int)},rows=rows)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(info,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-len(t) for i,t in wins.items()))


if __name__=="__main__":
    main()
