"""Build three-operation replacements for existing values from a two-step arithmetic frontier."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import csv
import gzip
import json
from pathlib import Path

from boundary_ensembles import variants, reverse_steps, compile_selection
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes


def propose(p, graph, base, one):
    # Each replacement has one new predecessor and up to two preceding operations.
    uses = Counter(x for _,a,b in graph.values() for x in {a,b})
    known = sorted(base)
    wanted = sorted(graph,key=lambda v:(v not in p.targets,-uses[v],-v.bit_length(),v))[:32]
    candidates = defaultdict(set)
    for target in wanted:
        for a in known:
            if a==target:
                continue
            for v,outer in reverse_steps(target,a,p.limit):
                if v==a or v==target or v in base:
                    continue
                if v in one:
                    candidates[target].add((v,outer,None,None))
                    continue
                for b in known:
                    if b==target:
                        continue
                    for q,inner in reverse_steps(v,b,p.limit):
                        if q in one and q!=v:
                            candidates[target].add((v,outer,q,inner))
    support = defaultdict(set)
    for target,options in candidates.items():
        for v,_,q,_ in options:
            support[v].add(target)
            if q is not None:
                support[q].add(target)
    return candidates,support


def work(job):
    p,parent,donors=job
    graph=active_graph(p,first_recipes(p,parent))
    base,one,common=variants(p,graph,donors)
    options,support=propose(p,graph,base,one)
    control,tape=compile_selection(p,parent,graph,common,False)
    best=min((parent,tape),key=len)
    arms=[]
    for fan,reverse_order in ((9,False),(22,False),(22,True)):
        paths={}
        tie=-1 if reverse_order else 1
        def rank(candidate):
            v,outer,q,inner=candidate
            users=len(support[v])+(len(support[q]) if q is not None else 0)
            return -users,q is not None,tie*v,(q or 0),outer,inner or ()
        for target,choices in sorted(options.items()):
            for v,outer,q,inner in sorted(choices,key=rank)[:fan]:
                paths[target,outer]={target:outer}
                if q is None:
                    for e in one[v]:
                        paths[v,e]={v:e}
                else:
                    paths[v,inner]={v:inner}
                    for e in one[q]:
                        paths[q,e]={q:e}
        if paths:
            status,candidate=compile_selection(p,parent,graph,common+list(paths.values()),False)
            best=min((best,candidate),key=len)
            arms.append(dict(fan=fan,reverse_order=reverse_order,paths=len(paths),**status))
    check(p,best)
    return p.id,best,dict(before=len(parent),after=len(best),control=control,
                          options=sum(map(len,options.values())),arms=arms)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ("puzzles","parent","bounds","out"):
        parser.add_argument("--"+key,type=Path,required=True)
    parser.add_argument("--donors",nargs="+",type=Path,required=True)
    parser.add_argument("--count",type=int,default=25)
    parser.add_argument("--jobs",type=int,default=8)
    args=parser.parse_args()
    ps=read_puzzles(args.puzzles)
    bank=read_submission(args.parent)
    parents=[read_submission(f) for f in args.donors]
    with args.bounds.open(newline="",encoding="utf8") as f:
        bounds={r["id"]:int(r["certified_lower"]) for r in csv.DictReader(f)}
    eligible=sorted((len(bank[p.id])-bounds[p.id],len(bank[p.id]),p.id,p)
                    for p in ps if bounds[p.id]<len(bank[p.id])<=29 and p.limit<=2000000)
    tasks=[(p,bank[i],list(dict.fromkeys(b[i] for b in parents if i in b and len(b[i])<=len(bank[i])+6 and b[i]!=bank[i]))) for _,_,i,p in eligible[:args.count]]
    rows,wins={},{}
    with ProcessPoolExecutor(args.jobs) as pool:
        for i,tape,row in pool.map(work,tasks,chunksize=1):
            rows[i]=row
            if len(tape)<len(bank[i]):
                wins[i]=tape
    args.out.mkdir(exist_ok=True,parents=True)
    write_submission(args.out/"wins.csv",[p for p in ps if p.id in wins],wins)
    data=dict(parent_sha256=sha256(args.parent),bounds_sha256=sha256(args.bounds),
              donors={f.name:sha256(f) for f in args.donors},rows=rows)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(data,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-len(tape) for i,tape in wins.items()))


if __name__=="__main__":
    main()
