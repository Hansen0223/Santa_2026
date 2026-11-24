"""Split one capped 882 cell by refining its third-level residue."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

from refine_open import read_puzzles, search, sha256, store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("puzzles","binary","parent","out"):
        parser.add_argument("--"+key,type=Path,required=True)
    parser.add_argument("--factor",type=int,default=4)
    parser.add_argument("--budget",type=int,default=25000000)
    parser.add_argument("--jobs",type=int,default=4)
    args = parser.parse_args()
    if args.factor<2 or min(args.jobs,args.budget)<1:
        parser.error("factor must be at least two and budget/jobs must be positive")
    capped = json.loads(args.parent.read_bytes())
    old = capped["context"]
    binary = args.binary.resolve(strict=True)
    if (capped["status"]!="UNKNOWN" or old["official_sha256"]!=sha256(args.puzzles)
            or old["binary_sha256"]!=sha256(binary) or old["thirds"]!=24 or old["width"]!=16):
        raise ValueError("Expected a capped cell from the original 24-part search")
    puzzle = next(x for x in read_puzzles(args.puzzles) if x.id=="scored_0882")
    first, second, third = capped["coordinates"]
    modulus = old["thirds"]*args.factor
    context = dict(old,thirds=modulus)
    args.out.mkdir(parents=True,exist_ok=True)
    todo=[]
    for fine in range(third,modulus,old["thirds"]):
        key=[first,second,fine]
        path=args.out/f"{first:02}-{second:02}-{fine:02}-mod{modulus}.json"
        if path.exists():
            current=json.loads(path.read_bytes())
            if current["coordinates"]!=key or current["parent"]!=capped["coordinates"] or current["context"]!=context:
                raise ValueError(f"Different refinement in {path}")
            if current["status"] in ("UNSAT","FOUND") or current["budget"]>=args.budget:
                continue
        todo.append((key,path))

    def work(item):
        key,path=item
        row=search(puzzle,binary,*key,args.budget,thirds=modulus)
        store(path,dict(row,coordinates=key,context=context,parent=capped["coordinates"]))
        print(*key,row["status"],row["metrics"][0],flush=True)

    with ThreadPoolExecutor(args.jobs) as pool:
        list(pool.map(work,todo))


if __name__=="__main__":
    main()
