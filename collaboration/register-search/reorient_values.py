"""Reorient existing arithmetic dependencies while retaining their numeric values."""
import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
from itertools import combinations, combinations_with_replacement
import json
from pathlib import Path

from interior_bands import compile_on_parent, solve
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes
from solvers.graphs.corpus_prefix import arithmetic_edges


def canonical(edge):
    op,a,b=edge
    return (op,min(a,b),max(a,b)) if op in "+*" else edge


def proposals(puzzle, base, breadth):
    available=sorted(base.keys() | set(puzzle.seeds))
    catalog=defaultdict(set)
    for a,b in combinations_with_replacement(available,2):
        for value,edge in arithmetic_edges(a,b,puzzle.limit):
            if value in base and value not in (a,b) and canonical(edge)!=base[value]:
                catalog[value].add(canonical(edge))

    ancestors={v:set() for v in puzzle.seeds}
    for v,(_,a,b) in base.items():
        ancestors[v]={a,b} | ancestors[a] | ancestors[b]
    pools={False:[],True:[]}
    for v,edges in catalog.items():
        for edge in edges:
            _,a,b=edge
            upstream = ancestors[a] | ancestors[b] | {a,b}
            distance=len(upstream ^ ancestors[v])
            pools[v in upstream].append((-distance,v,edge))
    direct=sorted(pools[False])[:breadth]
    reverse=sorted(pools[True])[:breadth]
    for _,v,e in direct:
        yield "single", {v:e}
    for (_,v,e),(_,w,f) in combinations(direct[:14],2):
        if v!=w:
            yield "pair",{v:e,w:f}
    # New operands may depend on the value being changed. Break that path in
    # the same edit, then validate all other dependencies in the merged graph.
    for _,v,e in reverse:
        for _,w,f in direct:
            if w!=v and v in ancestors[w] and w in (ancestors[e[1]] | ancestors[e[2]] | set(e[1:])):
                yield "reverse",{v:e,w:f}


def work(task):
    puzzle,parent,engine,breadth,rounds = task
    graph=active_graph(puzzle,first_recipes(puzzle,parent))
    base={v:canonical(e) for v,e in graph.items()}
    counts=defaultdict(int)
    choices=defaultdict(list)
    seen=set()
    graph_keys=base.keys()
    for method,patch in proposals(puzzle,base,breadth):
        counts[f"{method}_tested"]+=1
        try:
            candidate=active_graph(puzzle,base|patch)
        except (ValueError,KeyError):
            continue
        if not patch.keys() <= candidate.keys():
            continue
        actual=frozenset((v,candidate[v]) for v in patch)
        if actual in seen:
            continue
        seen.add(actual)
        counts[f"{method}_acyclic"]+=1
        moved=sum(len(set(base[v][1:]) ^ set(candidate[v][1:])) for v in patch)
        dropped=graph_keys-candidate.keys()
        choices[method].append((len(candidate),-moved,tuple(sorted(patch)),candidate,len(dropped)))
    best=parent
    record=dict(before=len(parent),counts=dict(counts),starts=[])
    seed=630911+int(puzzle.id[-4:])
    for method,items in choices.items():
        for _,_,values,candidate,dropped in sorted(items,key=lambda v:v[:3])[:8]:
            tape=compile_on_parent(puzzle,parent,candidate)
            if tape is None:
                continue
            if "control" not in record:
                control=solve(engine,puzzle,[parent],seed,rounds)
                record["control"]=len(control)
                best=min((best,control),key=len)
            refined=solve(engine,puzzle,[tape,parent],seed,rounds)
            best=min((best,tape,refined),key=len)
            record["starts"].append(dict(kind=method,rewritten=values,removed=dropped,raw=len(tape),after=len(refined)))
            break
    record["after"]=check(puzzle,best)
    return puzzle.id,best,record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("puzzles","parent","engine","out"):
        parser.add_argument("--"+name,type=Path,required=True)
    for name,n in (("count",105),("offset",0),("jobs",6),("breadth",26),("rounds",440)):
        parser.add_argument("--"+name,type=int,default=n)
    a=parser.parse_args()
    puzzles=read_puzzles(a.puzzles)
    parents=read_submission(a.parent)
    qualified=sorted((p for p in puzzles if 35<=len(parents[p.id])<=230),
                     key=lambda p:hashlib.sha256(("reorient-values-"+p.id).encode()).digest())
    work_items=[(p,parents[p.id],a.engine,a.breadth,a.rounds) for p in qualified[a.offset:a.offset+a.count]]
    rows,wins={},{}
    with ProcessPoolExecutor(a.jobs) as pool:
        for pid,tape,r in pool.map(work,work_items):
            rows[pid]=r
            if r["after"]<r["before"]:
                wins[pid]=tape
                print(pid,r["before"],r["after"],flush=True)
    a.out.mkdir(parents=True,exist_ok=True)
    write_submission(a.out/"wins.csv",[p for p in puzzles if p.id in wins],wins)
    data=dict(parent_sha256=sha256(a.parent),puzzles_sha256=sha256(a.puzzles),engine_sha256=sha256(a.engine),
              settings={k:v for k,v in vars(a).items() if isinstance(v,int)},rows=rows)
    (a.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(data,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-rows[i]["after"] for i in wins))


if __name__=="__main__":
    main()
