"""Optimize novelty under a length ceiling, then refine with matched controls."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import gzip
import json
from pathlib import Path
import sys

from full_union import additions, compile_selection
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"collaboration/retained-pool"))
from neutral_lead import solve


def canonical(graph):
    return {v:(op,min(a,b),max(a,b)) if op in "+*" else (op,a,b) for v,(op,a,b) in graph.items()}


def work(job):
    puzzle, parent, donors, engine, rounds, slack, expand = job
    old = active_graph(puzzle,first_recipes(puzzle,parent))
    routes = [(t,active_graph(puzzle,first_recipes(puzzle,t))) for t in donors]
    frequencies = Counter(v for _,graph in routes for v in graph if v not in old)
    weights = {v: 2 if n==1 else 1 for v,n in frequencies.items()}
    alternatives = additions(puzzle,[parent,*donors])
    warm = min(((t,g) for t,g in routes if len(t)<=len(parent)+slack),
               key=lambda item:(-sum(weights.get(v,0) for v in item[1]),len(item[0])),default=None)
    model,candidate = compile_selection(
        puzzle,parent,old,alternatives,expand,slack=slack,
        hint_graph=None if warm is None else warm[1],novelty_weights=weights
    )
    seed = 476081 + int(puzzle.id[-4:])
    direct = solve(engine,puzzle,[parent],seed,rounds)
    cross = solve(engine,puzzle,[parent,*donors[:3]],seed,rounds)
    best = min((parent,direct,cross),key=len)
    report = dict(before=len(parent),donors=list(map(len,donors)),
                  control=len(direct),ordinary_cross=len(cross),model=model)
    if candidate is not None:
        best = min((best,candidate),key=len)
        active = active_graph(puzzle,first_recipes(puzzle,candidate))
        novel = set(active)-old.keys()
        report["start"] = len(candidate)
        report["new_values"] = len(novel)
        key = canonical(active)
        if novel and all(key!=canonical(g) for _,g in routes):
            result = solve(engine,puzzle,[candidate,parent,*donors[:2]],seed,rounds)
            best = min((best,result),key=len)
            report["refined"] = len(result)
    report["after"] = check(puzzle,best)
    return puzzle.id,best,report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("puzzles","parent","engine","out"):
        parser.add_argument("--"+key,type=Path,required=True)
    parser.add_argument("--donors",nargs="+",type=Path,required=True)
    parser.add_argument("--expand",action="store_true",help="Enumerate extra recipes among the retained values.")
    for key,default in (("count",130),("offset",0),("jobs",10),("rounds",550),("slack",2),("minimum-distance",5)):
        parser.add_argument("--"+key,type=int,default=default)
    args = parser.parse_args()
    ps = read_puzzles(args.puzzles)
    source = read_submission(args.parent)
    banks = [read_submission(f) for f in args.donors]
    candidates = []
    for puzzle in ps:
        tape = source[puzzle.id]
        if len(tape)<31:
            continue
        old = active_graph(puzzle,first_recipes(puzzle,tape))
        offers = {}
        for bank in banks:
            draft = bank.get(puzzle.id)
            if draft is None or not 0<=len(draft)-len(tape)<=args.slack+3 or draft in offers:
                continue
            alternate = active_graph(puzzle,first_recipes(puzzle,draft))
            distance = len(old.keys() ^ alternate.keys())
            if distance>=args.minimum_distance:
                offers[draft] = distance/(1+len(draft)-len(tape))
        if offers:
            ranked = sorted(offers,key=lambda t:(-offers[t],len(t)))[:5]
            candidates.append((-offers[ranked[0]]/len(tape),puzzle.id,puzzle,ranked))
    selected = sorted(candidates)[args.offset:args.offset+args.count]
    tasks = [(p,source[p.id],ts,args.engine,args.rounds,args.slack,args.expand) for _,_,p,ts in selected]
    rows,wins = {},{}
    with ProcessPoolExecutor(args.jobs) as pool:
        for i,tape,row in pool.map(work,tasks,chunksize=1):
            rows[i] = row
            if len(tape)<len(source[i]):
                wins[i] = tape
                print(i,len(source[i]),len(tape),flush=True)
    args.out.mkdir(exist_ok=True,parents=True)
    write_submission(args.out/"wins.csv",[p for p in ps if p.id in wins],wins)
    report = dict(parent_sha256=sha256(args.parent),engine_sha256=sha256(args.engine),
                  donors={f.name:sha256(f) for f in args.donors},eligible=len(candidates),
                  settings={k:v for k,v in vars(args).items() if isinstance(v,int)},rows=rows)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(report,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-len(t) for i,t in wins.items()))


if __name__=="__main__":
    main()
