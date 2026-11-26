"""Generate diverse near-incumbent programs by excluding shared intermediate values."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/"collaboration/register-search"),
                str(ROOT/"collaboration/structure-controls/ruler"), str(ROOT/"collaboration/retained-pool")]
from elf import check, read_puzzles, read_submission, sha256, write_submission
from fanout_repair import build_frontier, demand
from graph import active_graph, first_recipes
from neutral_lead import solve
from selector import compile_selection


def supplies(puzzle, graph, omit, direct_users, width):
    ready = set(puzzle.seeds) | (graph.keys() - {omit} - direct_users)
    frontier = build_frontier(sorted(ready), ready, puzzle.limit)
    required, direct = demand(direct_users, ready, puzzle.limit)
    useful = sorted(required.keys() & frontier.keys(),
                    key=lambda v:(-len(required[v]), v.bit_length(), v))
    picked = []
    uncovered = direct_users - direct.keys()
    while useful and len(picked) < width:
        v = min(useful,key=lambda v:(-len(required[v].keys() & uncovered),-len(required[v]),v.bit_length(),v))
        useful.remove(v)
        picked.append(v)
        uncovered -= required[v].keys()
    return [{v:frontier[v], **required[v]} for v in picked]


def work(task):
    puzzle,parent,binary,helpers,rounds,width,slack,least_shared = task
    graph = active_graph(puzzle,first_recipes(puzzle,parent))
    users=defaultdict(set)
    seeds=set(puzzle.seeds)
    for v,(_,a,b) in graph.items():
        for u in {a,b}:
            users[u].add(v)
    candidates=sorted((v for v in graph.keys()-set(puzzle.targets)
                       if 2<=len(users[v])<=6),key=lambda v:(len(users[v]) if least_shared else -len(users[v]),v.bit_length(),v))
    best=parent
    report=dict(before=len(parent),tested=[],eligible=len(candidates))
    seed=200671+int(puzzle.id[-4:])
    for omit in candidates[:helpers]:
        paths=supplies(puzzle,graph,omit,users[omit],width)
        if not paths:
            continue
        model,tape=compile_selection(puzzle,parent,graph,paths,True,slack=slack,forbidden_values=(omit,))
        record=dict(omitted=omit,consumers=len(users[omit]),supplied=len(paths),model=model)
        report["tested"].append(record)
        if tape is None:
            continue
        values=first_recipes(puzzle,tape).keys()
        fresh=values-graph.keys()-seeds
        if omit in values:
            raise ValueError("Forbidden helper survived register scheduling")
        best=min((best,tape),key=len)
        if not fresh:
            continue
        if "control" not in report:
            control=solve(binary,puzzle,[parent],seed,rounds)
            report["control"]=len(control)
            best=min((best,control),key=len)
        test=solve(binary,puzzle,[tape,parent],seed,rounds)
        best=min((best,tape,test),key=len)
        record.update(fresh=len(fresh),start=len(tape),after=len(test))
    report["after"]=check(puzzle,best)
    return puzzle.id,best,report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ("puzzles","parent","engine","out"):
        parser.add_argument("--"+key,type=Path,required=True)
    for key,n in (("count",60),("offset",0),("helpers",3),("width",12),("slack",2),("rounds",460),("jobs",5)):
        parser.add_argument("--"+key,type=int,default=n)
    parser.add_argument("--least-shared",action="store_true")
    a=parser.parse_args()
    puzzles=read_puzzles(a.puzzles)
    bank=read_submission(a.parent)
    qualified=sorted((p for p in puzzles if 28<=len(bank[p.id])<=190),
                     key=lambda p:hashlib.sha256(("exclude-shared-"+p.id).encode()).digest())
    tasks=[(p,bank[p.id],a.engine,a.helpers,a.rounds,a.width,a.slack,a.least_shared) for p in qualified[a.offset:a.offset+a.count]]
    results,wins={},{}
    with ProcessPoolExecutor(a.jobs) as pool:
        for pid,tape,r in pool.map(work,tasks):
            results[pid]=r
            if r["after"]<r["before"]:
                wins[pid]=tape
                print(pid,r["before"],r["after"],flush=True)
    a.out.mkdir(parents=True,exist_ok=True)
    write_submission(a.out/"wins.csv",[p for p in puzzles if p.id in wins],wins)
    data=dict(parent_sha256=sha256(a.parent),puzzles_sha256=sha256(a.puzzles),engine_sha256=sha256(a.engine),
              settings={k:v for k,v in vars(a).items() if isinstance(v,int)},rows=results)
    (a.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(data,separators=(",",":")).encode(),mtime=0))
    print(len(results),len(wins),sum(results[i]["before"]-results[i]["after"] for i in wins))


if __name__=="__main__":
    main()
