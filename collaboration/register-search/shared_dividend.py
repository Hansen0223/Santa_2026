"""Join two output branches by sharing a dividend before optional offsets."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
from itertools import combinations, product
import json
from math import lcm
from pathlib import Path

from common_offset_factors import offsets
from fanout_repair import build_frontier
from helper_triangles import removable_together
from interior_bands import compile_on_parent, solve
from quotient_chains import private_cone
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes


def patches(puzzle, left, right, ready, anchors, limit, stats):
    frontier=build_frontier(sorted(ready),ready,puzzle.limit)
    supported=ready|frontier.keys()
    choices=set()
    forms_left=list(offsets(left,anchors,puzzle.limit))
    forms_right=list(offsets(right,anchors,puzzle.limit))
    for (a,fix_a),(b,fix_b) in product(forms_left,forms_right):
        if a==b or a==right or b==left:
            continue
        common=lcm(a,b)
        if common>puzzle.limit:
            continue
        stats["bounded_common"]+=1
        for multiplier in (1,2,3):
            dividend=common*multiplier
            if dividend>puzzle.limit or dividend not in supported or dividend in (a,b,left,right):
                continue
            da,db=dividend//a,dividend//b
            if da==db or min(da,db)<2 or {da,db} & {a,b,left,right} or not {da,db}<=supported:
                continue
            patch={v:frontier[v] for v in {dividend,da,db}-ready}
            if a not in ready:
                patch[a]=("/",dividend,da)
            if b not in ready:
                patch[b]=("/",dividend,db)
            if fix_a:
                patch[left]=fix_a
            if fix_b:
                patch[right]=fix_b
            if not {left,right}<=patch.keys() or len(patch)>limit:
                continue
            key=frozenset(patch.items())
            if key not in choices:
                choices.add(key)
                stats["patches"]+=1
                yield patch


def work(task):
    puzzle,parent,engine,pair_count,palette,rounds = task
    graph=active_graph(puzzle,first_recipes(puzzle,parent))
    targets=set(puzzle.targets)
    readers=Counter(x for _,a,b in graph.values() for x in {a,b})
    uses=readers+Counter(targets)
    sizes={v:len(private_cone(graph,uses,v)) for v in graph}
    roots=sorted((v for v in graph if sizes[v]>=3),key=lambda v:(v not in targets,-sizes[v],v.bit_length(),v))[:28]
    ancestors={v:set() for v in puzzle.seeds}
    for v,(_,a,b) in graph.items():
        ancestors[v]={a,b}|ancestors[a]|ancestors[b]
    pairs=[]
    for a,b in combinations(roots,2):
        if a in ancestors[b] or b in ancestors[a]:
            continue
        removed=removable_together(graph,uses,{a,b})
        if len(removed)>=4:
            pairs.append((abs(a-b).bit_length(),-len(removed),a,b,removed))
    best=parent
    metrics=Counter()
    warm={}
    for _,_,a,b,removed in sorted(pairs)[:pair_count]:
        fixed={v:r for v,r in graph.items() if v not in removed}
        ready={v for v in (fixed.keys()|set(puzzle.seeds))-{a,b} if not {a,b}&ancestors[v]}
        anchors=sorted(ready,key=lambda v:(v not in puzzle.seeds,-readers[v],v))[:palette]
        for patch in patches(puzzle,a,b,ready,anchors,len(removed)+3,metrics):
            tape=compile_on_parent(puzzle,parent,fixed|patch)
            if tape is None:
                continue
            metrics["scheduled"]+=1
            best=min((best,tape),key=len)
            if len(tape)<=len(parent)+1:
                delta=len(first_recipes(puzzle,tape).keys()^graph.keys())
                if delta>=2:
                    warm[tape]=(len(tape),-delta,a,b)
    row=dict(before=len(parent),pairs=min(pair_count,len(pairs)),counts=dict(metrics),starts=[])
    if warm:
        seed=917455+int(puzzle.id[-4:])
        control=solve(engine,puzzle,[parent],seed,rounds)
        row["control"]=len(control)
        best=min((best,control),key=len)
        for tape in sorted(warm,key=warm.get)[:2]:
            refined=solve(engine,puzzle,[tape,parent],seed,rounds)
            row["starts"].append([*warm[tape],len(refined)])
            best=min((best,refined),key=len)
    row["after"]=check(puzzle,best)
    return puzzle.id,best,row


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("puzzles","parent","engine","out"):
        p.add_argument("--"+k,type=Path,required=True)
    for k,n in (("count",105),("pairs",10),("palette",18),("rounds",360),("jobs",5)):
        p.add_argument("--"+k,type=int,default=n)
    a=p.parse_args()
    puzzles=read_puzzles(a.puzzles)
    digest=sha256(a.parent)
    parents=read_submission(a.parent)
    if sha256(a.parent)!=digest:
        raise ValueError("Parent changed while loading")
    chosen=sorted((p for p in puzzles if 24<=len(parents[p.id])<=190),
                  key=lambda p:hashlib.sha256(("shared-dividend-"+p.id).encode()).digest())[:a.count]
    tasks=[(p,parents[p.id],a.engine,a.pairs,a.palette,a.rounds) for p in chosen]
    rows,wins={},{}
    with ProcessPoolExecutor(a.jobs) as pool:
        for pid,tape,row in pool.map(work,tasks):
            rows[pid]=row
            if row["after"]<row["before"]:
                wins[pid]=tape
                print(pid,row["before"],row["after"],flush=True)
    a.out.mkdir(parents=True,exist_ok=True)
    write_submission(a.out/"wins.csv",[p for p in puzzles if p.id in wins],wins)
    rec=dict(parent_sha256=digest,puzzles_sha256=sha256(a.puzzles),engine_sha256=sha256(a.engine),
             settings={k:v for k,v in vars(a).items() if isinstance(v,int)},rows=rows)
    (a.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(rec,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-rows[i]["after"] for i in wins))


if __name__=="__main__":
    main()
