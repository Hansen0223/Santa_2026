"""Combine several compatible changes to an arithmetic dependency graph."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
from itertools import combinations
import json
from pathlib import Path

from propagate_values import regions, trials, solve, schedule_like
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, compile_graph, first_recipes


def merged_graphs(puzzle, base, edits, limit):
    seen = set()
    for (left, left_context, left_graph), (right, right_context, right_graph) in combinations(edits,2):
        if left_context[0] == right_context[0] or left.keys() <= right.keys() or right.keys() <= left.keys():
            continue
        if any(left[v] != right[v] for v in left.keys() & right.keys()):
            continue
        changes = left | right
        key = frozenset(changes.items())
        if key in seen:
            continue
        seen.add(key)
        try:
            graph = active_graph(puzzle,base | changes)
        except (KeyError,ValueError):
            continue
        if len(graph) > limit or min(len(left_graph),len(right_graph)) + 1 < len(graph):
            continue
        if not ((left.keys() - right.keys()) & graph.keys() and (right.keys() - left.keys()) & graph.keys()):
            continue
        expected = len(left_graph)+len(right_graph)-len(base)
        yield graph,(left_context,right_context),expected-len(graph)


def work(task):
    puzzle,parent,engine,region_count,palette,rounds = task
    base=active_graph(puzzle,first_recipes(puzzle,parent))
    metrics=Counter()
    edits_by_root={}
    seen=set()
    for region in regions(puzzle,base,region_count):
        for graph,context in trials(puzzle,base,region,palette,metrics):
            if len(graph)>len(parent)+2:
                continue
            delta={v:recipe for v,recipe in graph.items() if base.get(v)!=recipe}
            key=frozenset(delta.items())
            if key in seen:
                continue
            seen.add(key)
            edits_by_root.setdefault(context[0],[]).append((delta,context,graph))
    edits=[]
    for choices in edits_by_root.values():
        edits.extend(sorted(choices,key=lambda item:(len(item[2]),-len(item[0]),item[1]))[:3])
    edits.sort(key=lambda item:(len(item[2]),-len(item[0]),item[1]))
    pairs=list(merged_graphs(puzzle,base,edits[:42],len(parent)+2))
    ranked=sorted(pairs,key=lambda p:(len(p[0]),-p[2],-len(p[0].keys()-base.keys()),p[1]))
    record=dict(before=len(parent),singles=len(edits),pairs=len(pairs),metrics=dict(metrics),starts=[])
    best=parent
    if ranked:
        seed=806171+int(puzzle.id[-4:])
        control=solve(engine,puzzle,[parent],seed,rounds)
        best=min((best,control),key=len)
        record["control"]=len(control)
        for kind, candidates in (("single",((g,(ctx,),0) for _,ctx,g in edits[:12])), ("pair",ranked[:18])):
            fingerprints=set()
            for graph,context,surplus in candidates:
                signature=frozenset(graph.items())
                if signature in fingerprints:
                    continue
                tape=compile_graph(puzzle,graph,attempts=4)
                if tape is None:
                    tape=schedule_like(puzzle,parent,graph)
                if tape is None or len(tape)>len(parent)+2:
                    continue
                fingerprints.add(signature)
                refined=solve(engine,puzzle,[tape,parent],seed,rounds)
                best=min((best,tape,refined),key=len)
                record["starts"].append(dict(kind=kind,context=context,raw=len(tape),after=len(refined),shared_savings=surplus))
                if len(fingerprints)==2:
                    break
    record["after"]=check(puzzle,best)
    return puzzle.id,best,record


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("puzzles","parent","engine","out"):
        p.add_argument("--"+key,type=Path,required=True)
    for key,n in (("count",90),("jobs",6),("cases",22),("palette",56),("rounds",500),("offset",0)):
        p.add_argument("--"+key,type=int,default=n)
    args=p.parse_args()
    puzzles=read_puzzles(args.puzzles)
    parent=read_submission(args.parent)
    selected=sorted((p for p in puzzles if len(parent[p.id])>=35),
                    key=lambda p:hashlib.sha256(("concurrent-edits-"+p.id).encode()).digest())
    work_items=[(p,parent[p.id],args.engine,args.cases,args.palette,args.rounds)
                for p in selected[args.offset:args.offset+args.count]]
    rows,wins={},{}
    with ProcessPoolExecutor(args.jobs) as pool:
        for pid,tape,report in pool.map(work,work_items):
            rows[pid]=report
            if report["after"]<report["before"]:
                wins[pid]=tape
                print(pid,report["before"],report["after"],flush=True)
    args.out.mkdir(parents=True,exist_ok=True)
    write_submission(args.out/"wins.csv",[p for p in puzzles if p.id in wins],wins)
    report=dict(parent_sha256=sha256(args.parent),puzzles_sha256=sha256(args.puzzles),engine_sha256=sha256(args.engine),
                settings={k:v for k,v in vars(args).items() if isinstance(v,int)},rows=rows)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(report,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-rows[i]["after"] for i in wins))


if __name__ == "__main__":
    main()
