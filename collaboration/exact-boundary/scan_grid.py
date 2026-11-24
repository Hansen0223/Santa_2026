"""Run a resumable two-level exact search grid for a bounded arithmetic puzzle."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT), str(ROOT/"collaboration/puzzle-0882-diversity")]
from elf import check, read_puzzles, sha256, write_submission
from tiny import encode
from refine_open import store


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for k in ("puzzles","binary","out"):
        parser.add_argument("--"+k,type=Path,required=True)
    parser.add_argument("--id",required=True)
    parser.add_argument("--helpers",required=True,type=int)
    parser.add_argument("--prior",type=Path)
    for k,n in (("shards",24),("subshards",32),("jobs",8),("budget",2000000)):
        parser.add_argument("--"+k,type=int,default=n)
    args=parser.parse_args()
    if min(args.shards,args.subshards,args.jobs,args.budget)<1 or args.helpers<5:
        parser.error("Shard counts and budgets must be positive; select at least five helpers")
    p=next(x for x in read_puzzles(args.puzzles) if x.id==args.id)
    if p.limit>2000000:
        parser.error("The dense engine requires a value limit at most 2,000,000")
    binary=args.binary.resolve(strict=True)
    context=dict(puzzle=p.id,helpers=args.helpers,official=sha256(args.puzzles),
                 engine=sha256(binary),group_width=16,moduli=[args.shards,args.subshards,1])
    args.out.mkdir(parents=True,exist_ok=True)
    rows={}
    permitted={(i,j,0) for i in range(args.shards) for j in range(args.subshards)}

    def take(row):
        coord=tuple(row["coords"])
        if coord not in permitted or any(row.get(k)!=v for k,v in context.items()):
            raise ValueError(f"Mismatched record for {coord}")
        prior=rows.get(coord)
        if prior is None or (prior["status"]=="UNKNOWN" and
           (row["status"]!="UNKNOWN" or row["budget"]>prior["budget"])):
            rows[coord]=row

    if args.prior:
        raw=json.loads(gzip.decompress(args.prior.read_bytes()))
        for row in raw["rows"]:
            take(row)
    for f in args.out.glob("*.json"):
        take(json.loads(f.read_bytes()))
    upper=len(set(p.targets)-set(p.seeds))+args.helpers
    for row in rows.values():
        if row["status"]=="FOUND":
            if check(p,row["program"])>upper:
                raise ValueError("Invalid saved witness")
            write_submission(args.out/"witness.csv",[p],{p.id:row["program"]})
            return
    tasks=sorted((x for x in permitted if x not in rows or
                  (rows[x]["status"]=="UNKNOWN" and rows[x]["budget"]<args.budget)),
                 key=lambda x:hashlib.sha256(f"{p.id}-{x}".encode()).digest())
    nums=[p.limit,len(p.seeds),len(p.targets),args.helpers,args.budget,*p.seeds,*p.targets]
    wire=" ".join(map(str,nums))+"\n"
    env={**os.environ,"SANTA_GROUP_WIDTH":"16"}

    def run(coord):
        fields=[str(v) for part in zip(coord,context["moduli"]) for v in part]
        proc=subprocess.run([str(binary),"star",*fields],input=wire,text=True,capture_output=True,
                            check=True,env=env,creationflags=getattr(subprocess,"BELOW_NORMAL_PRIORITY_CLASS",0))
        lines=proc.stdout.splitlines()
        status,*tokens=lines[0].split()
        metrics=list(map(int,tokens))
        if (status not in ("UNSAT","UNKNOWN","FOUND") or len(metrics)!=7 or
                not 0<=metrics[0]<=args.budget or len(lines)!=1+(status=="FOUND")):
            raise ValueError(f"Unexpected decision for {coord}")
        row=dict(context,coords=coord,budget=args.budget,status=status,metrics=metrics)
        if status=="FOUND":
            sequence=tuple(map(int,lines[1].split()))
            if sequence[:len(p.seeds)]!=p.seeds:
                raise ValueError("Changed starting values")
            tape=encode(p,sequence[len(p.seeds):])
            if check(p,tape)>upper:
                raise ValueError("Invalid exact witness")
            row["program"]=tape
        filename="-".join(f"{i:02}" for i in coord)+".json"
        store(args.out/filename,row)
        return coord,row

    print(f"{len(tasks)} queued cells, {len(rows)} prior records, budget {args.budget}",flush=True)
    with ThreadPoolExecutor(args.jobs) as pool:
        pending=[pool.submit(run,task) for task in tasks]
        for f in as_completed(pending):
            coord,row=f.result()
            rows[coord]=row
            print(*coord,row["status"],row["metrics"][0],flush=True)
            if row["status"]=="FOUND":
                write_submission(args.out/"witness.csv",[p],{p.id:row["program"]})
                for outstanding in pending:
                    outstanding.cancel()
                break


if __name__=="__main__":
    main()
