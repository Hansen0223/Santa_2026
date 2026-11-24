"""Split unresolved cells of a dense arithmetic proof along its third axis."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT),str(ROOT/"collaboration/puzzle-0882-diversity")]
from elf import read_puzzles,sha256,write_submission
from merge_grids import ENGINE,child_check,summarize
from refine_open import store
from tiny import encode


def selected_grid(path,puzzle,helpers):
    archive = json.loads(gzip.decompress(path.read_bytes()))
    candidates = [g for g in archive["grids"] if g["puzzle"]==puzzle.id and g["rows"]
                  and g["rows"][0]["helpers"]==helpers]
    if len(candidates) != 1:
        raise ValueError("Expected one grid for the requested puzzle and budget")
    return candidates[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("puzzles","binary","prior","out"):
        parser.add_argument("--"+name,type=Path,required=True)
    parser.add_argument("--id",required=True)
    parser.add_argument("--helpers",type=int,required=True)
    parser.add_argument("--resume",type=Path,help="Previously published child-grid archive")
    for name,default in (("parts",8),("budget",2400000),("jobs",12)):
        parser.add_argument("--"+name,type=int,default=default)
    args = parser.parse_args()
    if args.parts<2 or min(args.jobs,args.budget)<1:
        parser.error("Set two or more parts and positive search budgets")
    official = sha256(args.puzzles)
    puzzle = next(p for p in read_puzzles(args.puzzles) if p.id==args.id)
    binary = args.binary.resolve(strict=True)
    if sha256(binary)!=ENGINE:
        raise ValueError("The engine differs from the archived reference")
    base = selected_grid(args.prior,puzzle,args.helpers)
    base_sha = sha256(args.prior)
    _, open_parents = summarize(puzzle,official,base,[])
    left,right,_ = base["rows"][0]["moduli"]
    moduli = [left,right,args.parts]
    args.out.mkdir(parents=True,exist_ok=True)
    rows = {}
    cells = set(map(tuple,open_parents))
    ctx = dict(puzzle=puzzle.id,helpers=args.helpers,moduli=moduli,official=official,engine=ENGINE,group_width=16)

    def take(row):
        key = child_check(row,puzzle,official,moduli,cells,args.helpers)
        old = rows.get(key)
        if old is None or old["status"]=="UNKNOWN" and (row["status"]!="UNKNOWN" or row["budget"]>old["budget"]):
            rows[key] = row

    if args.resume:
        archive = json.loads(gzip.decompress(args.resume.read_bytes()))
        if archive["parent_sha256"]!=base_sha or archive["parts"]!=args.parts:
            raise ValueError("The archived child grid belongs to a different parent partition")
        for row in archive["children"]:
            take(row)
    for p in args.out.glob("*.json"):
        take(json.loads(p.read_bytes()))

    def search(key):
        coords = [str(v) for pair in zip(key,moduli) for v in pair]
        nums = (puzzle.limit,len(puzzle.seeds),len(puzzle.targets),args.helpers,args.budget,*puzzle.seeds,*puzzle.targets)
        result = subprocess.run([str(binary),"star",*coords],input=" ".join(map(str,nums))+"\n",
                                text=True,capture_output=True,check=True,
                                env={**os.environ,"SANTA_GROUP_WIDTH":"16"},
                                creationflags=getattr(subprocess,"BELOW_NORMAL_PRIORITY_CLASS",0))
        fields = result.stdout.splitlines()
        status,*values=fields[0].split()
        row=dict(ctx,coords=key,budget=args.budget,status=status,metrics=list(map(int,values)))
        if status=="FOUND":
            witness=tuple(map(int,fields[1].split()))
            if witness[:len(puzzle.seeds)]!=puzzle.seeds:
                raise ValueError("Witness changed the initial values")
            row["program"]=encode(puzzle,witness[len(puzzle.seeds):])
        child_check(row,puzzle,official,moduli,cells,args.helpers)
        store(args.out/("-".join(f"{x:02}" for x in key)+".json"),row)
        return key,row

    todo=[(*key,j) for key in open_parents for j in range(args.parts)]
    todo=[key for key in todo if key not in rows or rows[key]["status"]=="UNKNOWN" and rows[key]["budget"]<args.budget]
    todo.sort(key=lambda key:hashlib.sha256(str(key).encode()).digest())
    print(len(todo),"subcells queued",flush=True)
    found=False
    if not any(r["status"]=="FOUND" for r in rows.values()):
        with ThreadPoolExecutor(args.jobs) as pool:
            pending=[pool.submit(search,key) for key in todo]
            for future in as_completed(pending):
                if future.cancelled():
                    continue
                key,row=future.result()
                rows[key]=row
                if row["status"]=="FOUND" and not found:
                    found=True
                    for task in pending:
                        task.cancel()
    witness=next((r["program"] for r in rows.values() if r["status"]=="FOUND"),None)
    if witness is not None:
        write_submission(args.out/"witness.csv",[puzzle],{puzzle.id:witness})
    children=[rows[k] for k in sorted(rows)]
    closed,remaining=summarize(puzzle,official,base,children)
    result=dict(puzzle=puzzle.id,helpers=args.helpers,parent_sha256=base_sha,
                parts=args.parts,closed=closed,remaining=remaining,children=children)
    output=args.out/"refined.json.gz"
    temporary=output.with_suffix(".tmp")
    temporary.write_bytes(gzip.compress(json.dumps(result,separators=(",",":")).encode(),mtime=0))
    temporary.replace(output)
    print(len(children),"subcells;",len(closed),"old cells excluded;",len(remaining),"unresolved",flush=True)


if __name__=="__main__":
    if not __debug__:
        raise SystemExit("Run without -O to keep the proof checks")
    main()
