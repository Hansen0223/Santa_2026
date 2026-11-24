"""Build a near-shortest graph that omits old helpers, then search from it."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import json
from pathlib import Path
import sys

from full_union import additions, compile_selection, first_recipes, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph
from elf import check

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"collaboration/retained-pool"))
from neutral_lead import solve


def work(job):
    p,base,donors,binary,rounds,donor_hint=job
    original=first_recipes(p,base)
    graph=active_graph(p,original)
    alternatives=additions(p,[base,*donors])
    alternatives.extend({v:e} for v,e in original.items() if v not in graph)
    seed=584423+int(p.id[-4:])
    control=solve(binary,p,[base],seed,rounds)
    best=min((base,control),key=len)
    donors_within_slack=[active_graph(p,first_recipes(p,t)) for t in donors if len(t)<=len(base)+2] if donor_hint else []
    old_helpers=set(graph)-set(p.targets)
    tried=[]
    for change in (2,6):
        allowed=[g for g in donors_within_slack if len(old_helpers-g.keys())>=change]
        warm=min(allowed,key=len,default=None)
        details,tape=compile_selection(p,base,graph,alternatives,True,omit_old=change,slack=2,hint_graph=warm)
        if warm is not None:
            details["hint_steps"]=len(warm)
        if tape is not None:
            missing=len((graph.keys()-set(p.targets))-first_recipes(p,tape).keys())
            details["omitted_after_replay"]=missing
            if missing>=change:
                test=solve(binary,p,[tape,base],seed,rounds)
                details["refined"]=len(test)
                best=min((best,tape,test),key=len)
        tried.append(details)
    check(p,best)
    return p.id,best,dict(before=len(base),after=len(best),control=len(control),trials=tried)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ("puzzles","parent","binary","out"):
        ap.add_argument("--"+name,type=Path,required=True)
    ap.add_argument("--donors",nargs="+",type=Path,required=True)
    for field,n in (("count",90),("offset",0),("jobs",8),("rounds",600),("gap",6)):
        ap.add_argument("--"+field,type=int,default=n)
    ap.add_argument("--donor-hint",action="store_true")
    args=ap.parse_args()
    ps=read_puzzles(args.puzzles)
    bank=read_submission(args.parent)
    donor_banks=[read_submission(f) for f in args.donors]
    eligible=[]
    for p in ps:
        tape=bank[p.id]
        if len(tape)<29:
            continue
        old=first_recipes(p,tape)
        candidates={}
        for donor in donor_banks:
            t=donor.get(p.id)
            if t is None or not 0<=len(t)-len(tape)<=args.gap:
                continue
            values=first_recipes(p,t)
            distance=len(set(old)^set(values))
            if distance>=5:
                candidates[t]=distance
        if candidates:
            merit=max(d/(1+len(t)-len(tape)) for t,d in candidates.items())/len(tape)
            eligible.append((-merit,p.id,p,list(candidates)))
    jobs=[(p,bank[i],ts,args.binary,args.rounds,args.donor_hint) for _,i,p,ts in sorted(eligible)[args.offset:args.offset+args.count]]
    rows,wins={},{}
    with ProcessPoolExecutor(args.jobs) as pool:
        for i,tape,row in pool.map(work,jobs,chunksize=1):
            rows[i]=row
            if len(tape)<len(bank[i]):
                wins[i]=tape
    args.out.mkdir(parents=True,exist_ok=True)
    write_submission(args.out/"wins.csv",[p for p in ps if p.id in wins],wins)
    result=dict(parent_sha256=sha256(args.parent),engine_sha256=sha256(args.binary),eligible=len(eligible),
                donors={f.name:sha256(f) for f in args.donors},
                settings={k:v for k,v in vars(args).items() if isinstance(v,int)},rows=rows)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(result,separators=(",",":")).encode(),mtime=0))
    print(len(eligible),len(rows),len(wins),sum(rows[i]["before"]-len(t) for i,t in wins.items()))


if __name__=="__main__":
    main()
