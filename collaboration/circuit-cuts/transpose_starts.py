"""Search from complete programs built by transposing bounded signed-sum regions."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path

from transposed_sums import active_graph, check, compile_graph, first_recipes, read_puzzles, read_submission, regions, synthesize, write_submission, ROOT
import sys
sys.path.insert(0,str(ROOT/'collaboration/retained-pool'))
from neutral_lead import solve


def parents(p,old):
    base=active_graph(p,first_recipes(p,old))
    trials=[]
    for region,ports in regions(p,base)[:32]:
        try:
            extra=synthesize(p,base,region,ports,True)
            if not extra:
                continue
            graph=active_graph(p,base|extra)
        except (KeyError,ValueError,OverflowError):
            continue
        exported=frozenset(graph.keys()-base.keys())
        if exported and len(graph)<=len(old)+4:
            trials.append((len(graph),exported,graph))
    guides=[]
    seen=set()
    for size,novel,g in sorted(trials,key=lambda x:(x[0],-len(x[1]),sorted(x[1]))):
        if novel in seen:
            continue
        seen.add(novel)
        candidate=compile_graph(p,g,attempts=3)
        if candidate is not None and len(candidate)<=len(old)+4:
            guides.append(candidate)
            if len(guides)==4:
                break
    return guides


def work(job):
    p,old,binary,rounds=job
    alternatives=parents(p,old)
    if not alternatives:
        return p.id,old,dict(before=len(old),alternatives=[])
    seed=832077+int(p.id[-4:])
    baseline=solve(binary,p,[old],seed,rounds)
    treated=solve(binary,p,[old,*alternatives],seed,rounds)
    best=min((old,baseline,treated),key=len)
    return p.id,best,dict(before=len(old),alternatives=list(map(len,alternatives)),control=len(baseline),treated=len(treated))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for flag in ('puzzles','parent','binary','out'):
        parser.add_argument('--'+flag,required=True,type=Path)
    parser.add_argument('--offset',type=int,default=0)
    parser.add_argument('--count',type=int,default=96)
    parser.add_argument('--jobs',type=int,default=8)
    parser.add_argument('--rounds',type=int,default=350)
    args=parser.parse_args()
    ps=read_puzzles(args.puzzles)
    source=read_submission(args.parent)
    digest=hashlib.sha256(args.parent.read_bytes()).hexdigest()
    group=sorted((p for p in ps if len(source[p.id])>=35),
                 key=lambda p:hashlib.sha256(('dual-'+p.id).encode()).digest())[args.offset:args.offset+args.count]
    rows,wins={},{}
    with ProcessPoolExecutor(args.jobs) as pool:
        for i,t,rec in pool.map(work,[(p,source[p.id],args.binary,args.rounds) for p in group]):
            rows[i]=rec
            if len(t)<len(source[i]):wins[i]=t
    args.out.mkdir(parents=True,exist_ok=True)
    write_submission(args.out/'wins.csv',[p for p in ps if p.id in wins],wins)
    receipt=dict(parent_sha256=digest,offset=args.offset,rounds=args.rounds,rows=rows)
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(receipt,separators=(',',':')).encode(),mtime=0))
    print(len(rows),sum(bool(r['alternatives']) for r in rows.values()),len(wins),
          sum(len(source[i])-len(t) for i,t in wins.items()))


if __name__=='__main__':
    main()
