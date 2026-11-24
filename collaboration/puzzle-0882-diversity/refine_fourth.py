"""Run fourth-level exact partitions for selected capped cells without repeating completed children."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import subprocess

from refine_open import read_puzzles, sha256, store


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ("puzzles","binary","out"):
        parser.add_argument("--"+key,type=Path,required=True)
    parser.add_argument("--parent",type=Path,nargs="+",required=True)
    parser.add_argument("--parts",type=int,default=16)
    parser.add_argument("--budget",type=int,default=25000000)
    parser.add_argument("--jobs",type=int,default=8)
    args=parser.parse_args()
    if args.parts<2 or min(args.jobs,args.budget)<1:
        parser.error("parts must be at least two and jobs/budget positive")
    puzzle=next(p for p in read_puzzles(args.puzzles) if p.id=="scored_0882")
    official=sha256(args.puzzles)
    binary=args.binary.resolve(strict=True)
    engine=sha256(binary)
    args.out.mkdir(parents=True,exist_ok=True)
    moduli=[24,32,24,args.parts]
    tasks=[]
    seen=set()
    for path in args.parent:
        parent=json.loads(path.read_bytes())
        coords=parent["coordinates"]
        if (parent["status"]!="UNKNOWN" or parent["context"]["official_sha256"]!=official
                or parent["context"]["thirds"]!=24 or tuple(coords) in seen):
            raise ValueError(f"Expected distinct capped 24-part cell at {path}")
        if len(coords)!=3 or any(not 0<=i<n for i,n in zip(coords,moduli)):
            raise ValueError(f"Invalid parent coordinate at {path}")
        seen.add(tuple(coords))
        for fourth in range(args.parts):
            key=[*coords,fourth]
            tag="-".join(f"{v:02}" for v in key)
            dest=args.out/f"{tag}-mod{args.parts}.json"
            if dest.exists():
                previous=json.loads(dest.read_bytes())
                if previous["coordinates"]!=key or previous["engine"]!=engine or previous["moduli"]!=moduli:
                    raise ValueError(f"Changed refinement at {dest}")
                if previous["stdout"].split()[0] in ("UNSAT","FOUND") or previous["budget"]>=args.budget:
                    continue
            tasks.append((key,dest))

    def search(task):
        key,dest=task
        values=[puzzle.limit,len(puzzle.seeds),len(puzzle.targets),10,args.budget,*puzzle.seeds,*puzzle.targets]
        coords=[str(value) for pair in zip(key,moduli) for value in pair]
        run=subprocess.run([str(binary),"star",*coords],input=" ".join(map(str,values))+"\n",
                           text=True,capture_output=True,check=True,env={**os.environ,"SANTA_GROUP_WIDTH":"16"},
                           creationflags=getattr(subprocess,"BELOW_NORMAL_PRIORITY_CLASS",0))
        stdout=run.stdout.strip()
        status,*metrics=stdout.splitlines()[0].split()
        if status not in ("FOUND","UNSAT","UNKNOWN") or len(metrics)!=7:
            raise ValueError(f"Malformed output for {key}")
        store(dest,dict(coordinates=key,moduli=moduli,budget=args.budget,engine=engine,stdout=stdout))
        return key,status,int(metrics[0])

    with ThreadPoolExecutor(args.jobs) as pool:
        pending=[pool.submit(search,t) for t in tasks]
        for future in as_completed(pending):
            key,status,nodes=future.result()
            print(*key,status,nodes,flush=True)
            if status=="FOUND":
                for other in pending:
                    other.cancel()
                break


if __name__=="__main__":
    main()
