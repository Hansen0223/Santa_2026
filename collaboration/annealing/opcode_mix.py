"""Benchmark opposing opcode preferences against the same search with a length-only objective."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'collaboration/circuit-cuts'))
from reflection_search import execute, read_puzzles, read_submission, write_submission


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('puzzles','parent','reference','binary','out'):
        parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--count',type=int,default=80)
    parser.add_argument('--offset',type=int,default=0)
    parser.add_argument('--rounds',type=int,default=600)
    parser.add_argument('--jobs',type=int,default=8)
    args=parser.parse_args()
    ps=read_puzzles(args.puzzles)
    bank,ref=read_submission(args.parent),read_submission(args.reference)
    group=sorted((p for p in ps if len(bank[p.id])>=40),key=lambda p:
                 (len(bank[p.id])>=len(ref[p.id]),hashlib.sha256(('mix-'+p.id).encode()).digest()))
    group=group[args.offset:args.offset+args.count]
    results,wins={},{}
    with ThreadPoolExecutor(args.jobs) as pool:
        tasks=[pool.submit(execute,args.binary.resolve(),p,bank[p.id],args.rounds) for p in group]
        for job in tasks:
            i,(control,mixed)=job.result()
            results[i]=[len(bank[i]),len(ref[i]),len(control),len(mixed)]
            t=min((bank[i],control,mixed),key=len)
            if len(t)<len(bank[i]):wins[i]=t
    args.out.mkdir(exist_ok=True,parents=True)
    write_submission(args.out/'wins.csv',[p for p in ps if p.id in wins],wins)
    report=dict(parent_sha256=hashlib.sha256(args.parent.read_bytes()).hexdigest(),
                reference_sha256=hashlib.sha256(args.reference.read_bytes()).hexdigest(),rounds=args.rounds,
                columns=['parent','reference','control','weighted'],rows=results)
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(report,separators=(',',':')).encode(),mtime=0))
    print(len(results),len(wins),sum(len(bank[i])-len(t) for i,t in wins.items()))


if __name__=='__main__':
    main()
