"""Synthesize short programs using bounded forward and inverse recipe closures."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import csv
import gzip
from itertools import combinations_with_replacement
import json
from pathlib import Path
import sys

from two_sided_chains import reverse_steps
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes, recipes_from
from solvers.graphs.corpus_prefix import arithmetic_edges

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"collaboration/structure-controls/ruler"))
from selector import compile_selection


def variants(p,original,donors):
    base=set(p.seeds)|original.keys()
    inherited=[]
    for tape in donors:
        for v,choices in recipes_from(p,tape).items():
            base.add(v)
            inherited.extend({v:e} for e in sorted(choices))
    pool=sorted(base)
    direct=defaultdict(list)
    for a,b in combinations_with_replacement(pool,2):
        for out,e in arithmetic_edges(a,b,p.limit):
            if out in (a,b) or out in p.seeds:
                continue
            if out in base:
                inherited.append({out:e})
            elif len(direct[out])<4:
                direct[out].append(e)
    return base,direct,inherited


def synthesize(p,base,direct,bonus):
    # Rank definitions by how many required outputs they can help compute.
    shares=Counter()
    incoming=defaultdict(set)
    universe=base|direct.keys()
    ordered=sorted(universe)
    for t in sorted(set(p.targets)-set(p.seeds)):
        for known in ordered:
            for v,e in reverse_steps(t,known,p.limit):
                if v in (known,t) or v not in direct and known not in direct:
                    continue
                op,a,b=e
                if op in "+*" and a>b:
                    e=(op,b,a)
                if v in universe and e not in incoming[t]:
                    incoming[t].add(e)
                    shares.update({x for x in e[1:] if x in direct})
    rank=lambda e:(-sum(shares[a] for a in e[1:]),sum(a not in base for a in e[1:]),e)
    chosen=[]
    live=set()
    for out,choices in incoming.items():
        for e in sorted(choices,key=rank)[:bonus]:
            chosen.append({out:e})
            live.update(x for x in e[1:] if x in direct)
    for value in sorted(live):
        chosen.extend({value:e} for e in direct[value])
    return chosen, len(direct),len(live)


def work(job):
    p,tape,donors=job
    graph=active_graph(p,first_recipes(p,tape))
    base,one,common=variants(p,graph,donors)
    control,t1=compile_selection(p,tape,graph,common,False)
    best=min((tape,t1),key=len)
    trials=[]
    for width in (8,30,100):
        paths,reachable,used=synthesize(p,base,one,width)
        run,t2=compile_selection(p,tape,graph,common+paths,False)
        best=min((t2,best),key=len)
        trials.append(dict(width=width,one_step=reachable,new_values=used,**run))
    check(p,best)
    return p.id,best,dict(before=len(tape),after=len(best),control=control,tests=trials)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("puzzles","parent","bounds","out"):
        parser.add_argument("--"+name,type=Path,required=True)
    parser.add_argument("--donors",nargs="+",type=Path,required=True)
    parser.add_argument("--count",type=int,default=38)
    parser.add_argument("--jobs",type=int,default=6)
    args=parser.parse_args()
    ps=read_puzzles(args.puzzles)
    bank=read_submission(args.parent)
    sources=[read_submission(x) for x in args.donors]
    with args.bounds.open(newline="",encoding="utf8") as f:
        lower={r["id"]:int(r["certified_lower"]) for r in csv.DictReader(f)}
    selected=sorted((len(bank[p.id])-lower[p.id],p.id,p) for p in ps
                    if lower[p.id]<len(bank[p.id])<=33 and p.limit<=15000000)
    jobs=[(p,bank[i],list(dict.fromkeys(x[i] for x in sources if i in x and x[i]!=bank[i] and len(x[i])<=len(bank[i])+8))) for _,i,p in selected[:args.count]]
    rows,wins={},{}
    with ProcessPoolExecutor(args.jobs) as pool:
        for i,tape,record in pool.map(work,jobs,chunksize=2):
            rows[i]=record
            if len(tape)<len(bank[i]):
                wins[i]=tape
    args.out.mkdir(exist_ok=True,parents=True)
    write_submission(args.out/"wins.csv",[p for p in ps if p.id in wins],wins)
    data=dict(parent_sha256=sha256(args.parent),bounds_sha256=sha256(args.bounds),
              donors={f.name:sha256(f) for f in args.donors},eligibility=len(selected),rows=rows)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(data,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-len(tape) for i,tape in wins.items()))


if __name__=="__main__":
    main()
