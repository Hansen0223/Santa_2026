"""Find alternate target recipes using two adjacent shared values."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import sys

from quotient_chains import private_cone
from two_sided_chains import reverse_steps
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes
from solvers.graphs.corpus_prefix import arithmetic_edges

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"collaboration/structure-controls/ruler"))
from selector import compile_selection


def explain(puzzle,graph):
    targets = set(puzzle.targets)
    used = Counter(x for _,a,b in graph.values() for x in {a,b})
    uses = used+Counter(targets)
    roots = {v:private_cone(graph,uses,v) for v in sorted(targets & graph.keys()) if not used[v]}
    weights = {v:len(cone)-1 for v,cone in roots.items() if len(cone)>=2}
    if len(weights)<2:
        return [], [], dict(eligible_roots=len(weights))

    # Only independently available operands may support an alternate definition of a terminal root.
    operands = sorted((set(graph)|set(puzzle.seeds))-roots.keys())
    existing = set(graph)|set(puzzle.seeds)
    demand = defaultdict(dict)
    for root in weights:
        for operand in operands:
            if operand in roots[root]:
                continue
            for helper,edge in reverse_steps(root,operand,puzzle.limit):
                if helper not in existing and helper!=root:
                    demand[helper].setdefault(root,edge)
    roots_with = {v:sum(weights[t] for t in targets) for v,targets in demand.items()}
    direct = defaultdict(list)
    for j, a in enumerate(operands):
        for b in operands[:j+1]:
            for v,recipe in arithmetic_edges(a,b,puzzle.limit):
                if v in demand and len(direct[v])<2:
                    direct[v].append(recipe)
    starters = sorted(direct,key=lambda v:(-roots_with[v],v))
    single,edges = [],[]
    pair_candidates = {}
    for first in starters[:160]:
        near = demand[first]
        if len(near)>=2:
            single.append((roots_with[first],first))
        for other in operands:
            for second, recipe in arithmetic_edges(first,other,puzzle.limit):
                if second==first or second not in demand:
                    continue
                far=demand[second]
                # Require both levels to open at least one distinct target recipe.
                if not (near.keys()-far.keys()) or not (far.keys()-near.keys()):
                    continue
                worth=sum(weights[t] for t in near.keys()|far.keys())
                if worth>2:
                    pair_candidates.setdefault((first,second),(worth,recipe))

    # Keep the exact original graph available in both runs. New definitions
    # are selectable individually so the solver can combine across pairs.
    for _,v in sorted(single,reverse=True)[:20]:
        for e in direct[v]:
            edges.append({v:e})
        edges.extend({x:e} for x,e in demand[v].items())
    pairs=[]
    for (a,b),(worth,recipe) in sorted(pair_candidates.items(),key=lambda item:(-item[1][0],item[0]))[:32]:
        for e in direct[a]:
            pairs.append({a:e})
        pairs.append({b:recipe})
        pairs.extend({x:e} for v in (a,b) for x,e in demand[v].items())
    details=dict(eligible_roots=len(weights),reachable_first=len(direct),single=len(single),pairs=len(pair_candidates))
    return edges,pairs,details


def work(task):
    puzzle,parent=task
    original=first_recipes(puzzle,parent)
    graph=active_graph(puzzle,original)
    single,pairs,record=explain(puzzle,graph)
    best=parent
    if single:
        record["single_control"],candidate=compile_selection(puzzle,parent,graph,single,False)
        best=min((candidate,best),key=len)
    if pairs:
        record["two_level"],candidate=compile_selection(puzzle,parent,graph,single+pairs,False)
        best=min((candidate,best),key=len)
    check(puzzle,best)
    record.update(before=len(parent),after=len(best))
    return puzzle.id,best,record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ("puzzles","parent","out"):
        parser.add_argument("--"+key,type=Path,required=True)
    for key,default in (("count",180),("offset",0),("jobs",8)):
        parser.add_argument("--"+key,type=int,default=default)
    args=parser.parse_args()
    puzzles=read_puzzles(args.puzzles)
    bank=read_submission(args.parent)
    eligible=sorted((p for p in puzzles if len(bank[p.id])>=40),
                    key=lambda p:hashlib.sha256(("two-shared-levels-"+p.id).encode()).digest())
    jobs=[(p,bank[p.id]) for p in eligible[args.offset:args.offset+args.count]]
    rows,wins={},{}
    with ProcessPoolExecutor(args.jobs) as pool:
        for i,tape,row in pool.map(work,jobs,chunksize=2):
            rows[i]=row
            if len(tape)<len(bank[i]):
                wins[i]=tape
    args.out.mkdir(parents=True,exist_ok=True)
    write_submission(args.out/"wins.csv",[p for p in puzzles if p.id in wins],wins)
    data=dict(parent_sha256=sha256(args.parent),eligible=len(eligible),
              settings={k:v for k,v in vars(args).items() if isinstance(v,int)},rows=rows)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(data,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-len(tape) for i,tape in wins.items()))


if __name__=="__main__":
    main()
