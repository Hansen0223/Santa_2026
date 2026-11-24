"""Search a frontier and its nearest structurally distinct independent or public parent."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import json
from pathlib import Path
import sys

from donor_masks import read_puzzles,read_submission,sha256,write_submission
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"collaboration/retained-pool"))
from neutral_lead import fingerprint, solve


def work(item):
    p,tape,other,origin,distance,binary,rounds=item
    seed=580273+int(p.id[-4:])
    control=solve(binary,p,[tape],seed,rounds)
    crossed=solve(binary,p,[tape,other],seed,rounds)
    alternate=solve(binary,p,[other,tape],seed,rounds)
    result=min((tape,control,crossed,alternate),key=len)
    return p.id,result,dict(before=len(tape),donor=origin,donor_steps=len(other),
                            distance=round(distance,5),control=len(control),crossed=len(crossed),
                            alternate=len(alternate),after=len(result))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for k in ("puzzles","parent","binary","out"):
        parser.add_argument("--"+k,type=Path,required=True)
    parser.add_argument("--donors",nargs="+",type=Path,required=True)
    for k,n in (("jobs",10),("count",64),("gap",5),("offset",0),("rounds",1450)):
        parser.add_argument("--"+k,type=int,default=n)
    args=parser.parse_args()
    ps=read_puzzles(args.puzzles)
    bank=read_submission(args.parent)
    sources=[(path.name,read_submission(path)) for path in args.donors]
    ranked=[]
    for p in ps:
        tape=bank[p.id]
        if len(tape)<26:
            continue
        base=fingerprint(p,tape)
        candidates=[]
        for origin,donors in sources:
            t=donors.get(p.id)
            if t is None or not 0<=len(t)-len(tape)<=args.gap:
                continue
            other=fingerprint(p,t)
            distance=len(base^other)/max(1,len(base|other))
            if distance>=.13:
                merit=distance/(1+.44*(len(t)-len(tape)))
                candidates.append((-merit,origin,t,distance))
        if candidates:
            merit,origin,t,distance=min(candidates)
            ranked.append((merit,p.id,(p,tape,t,origin,distance,args.binary,args.rounds)))
    tasks=[task for _,_,task in sorted(ranked)[args.offset:args.offset+args.count]]
    rows,wins={},{}
    with ThreadPoolExecutor(args.jobs) as pool:
        for i,t,record in pool.map(work,tasks):
            rows[i]=record
            if len(t)<len(bank[i]):
                wins[i]=t
    args.out.mkdir(exist_ok=True,parents=True)
    write_submission(args.out/"wins.csv",[p for p in ps if p.id in wins],wins)
    data=dict(parent_sha256=sha256(args.parent),engine_sha256=sha256(args.binary),
              donors={f.name:sha256(f) for f in args.donors},eligible=len(ranked),
              settings={k:v for k,v in vars(args).items() if isinstance(v,int)},rows=rows)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(data,separators=(",",":")).encode(),mtime=0))
    print(len(ranked),len(rows),len(wins),sum(rows[i]["before"]-len(t) for i,t in wins.items()))


if __name__=="__main__":
    main()
