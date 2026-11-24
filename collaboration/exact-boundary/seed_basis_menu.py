"""Rebuild small puzzles using independently generated alternatives to the original number basis."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import csv
import gzip
from itertools import combinations_with_replacement
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT),str(ROOT/"collaboration/register-search"),str(ROOT/"collaboration/structure-controls/ruler")]
from elf import check,read_puzzles,read_submission,sha256,write_submission
from graph import active_graph,first_recipes
from quotient_chains import private_cone
from selector import compile_selection
from solvers.graphs.corpus_prefix import arithmetic_edges
from two_sided_chains import reverse_steps


def seed_paths(puzzle):
    seeds = set(puzzle.seeds)
    reached = {v:{} for v in seeds}
    previous = sorted(seeds)
    edge_order = ("+", "-", "*", "/")
    for depth in range(1,4):
        new = {}
        # A newly generated value must be an operand of the next result.
        for a in previous:
            for b,route in reached.items():
                support = reached[a] | route
                if len(support)>=depth:
                    continue
                for value,edge in arithmetic_edges(a,b,puzzle.limit):
                    if value not in reached:
                        proposed = support | {value:edge}
                        old = new.get(value)
                        key = (len(proposed),edge_order.index(edge[0]),edge[1:])
                        if old is None or key < old[0]:
                            new[value] = key,proposed
        reached.update((v,path) for v,(_,path) in sorted(new.items()))
        previous = sorted(new)
    return reached


def menus(puzzle,graph,widths):
    known = set(puzzle.seeds) | graph.keys()
    goals = set(puzzle.targets)
    uses = Counter(goals)
    for _,a,b in graph.values():
        uses.update({a,b})
    cones = {v:private_cone(graph,uses,v) for v in graph}
    paths = seed_paths(puzzle)
    offers = defaultdict(dict)
    for root in graph:
        for value in sorted(known):
            if value==root:
                continue
            for other,edge in reverse_steps(root,value,puzzle.limit):
                if other not in known and other in paths:
                    offers[other].setdefault(root,edge)
    drafts = []
    for value,alternatives in offers.items():
        supplied = paths[value]
        score = len(set().union(*(cones[root] - alternatives.keys() for root in alternatives))) - len(supplied)
        value_weight = len(alternatives) + sum(root in goals for root in alternatives)
        entire = supplied | alternatives
        drafts.append((-score,-value_weight,len(supplied),value,entire))
    # A target can use two independently generated values generated from the official seeds.
    pair_count = 0
    for root in sorted(goals & graph.keys()):
        by_pair = []
        for a,left in paths.items():
            if a in known:
                continue
            for b,edge in reverse_steps(root,a,puzzle.limit):
                if b<=a or b in known or b not in paths:
                    continue
                right = paths[b]
                union = left | right
                if len(union)>5:
                    continue
                benefit = len(cones[root])-len(union)-1
                by_pair.append((-benefit,len(union),a,b,union | {root:edge}))
        pair_count+=len(by_pair)
        for impact,cost,a,_,route in sorted(by_pair,key=lambda x:x[:4])[:8]:
            drafts.append((impact,-2,cost,a,route))
    drafts.sort(key=lambda q:q[:4])
    outputs = []
    for n in widths:
        entries = {}
        for *_,route in drafts[:n]:
            entries.update(((v,e),{v:e}) for v,e in route.items() if v not in puzzle.seeds)
        outputs.append(list(entries.values()))
    return outputs,dict(seed_values=len(paths),single=len(offers),pairs=pair_count)


def work(job):
    p,parent,donors,widths = job
    graph = active_graph(p,first_recipes(p,parent))
    old_edges = { (v,e):{v:e} for tape in donors for v,e in first_recipes(p,tape).items() if v not in p.seeds}
    fragments,counts = menus(p,graph,widths)
    best = parent
    baseline,candidate = compile_selection(p,parent,graph,list(old_edges.values()),True)
    best = min((best,candidate),key=len)
    trials = []
    for width,entries in zip(widths,fragments):
        if not entries:
            continue
        result,candidate = compile_selection(p,parent,graph,list(old_edges.values())+entries,True)
        best = min((best,candidate),key=len)
        trials.append(dict(width=width,added=len(entries),**result))
    return p.id,best,dict(before=len(parent),after=check(p,best),control=baseline,trials=trials,**counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("puzzles","parent","bounds","out"):
        parser.add_argument("--"+name,type=Path,required=True)
    parser.add_argument("--donors",nargs="*",type=Path,default=[])
    parser.add_argument("--puzzle-id",nargs="*")
    parser.add_argument("--widths",nargs="+",type=int,default=[12,40,100])
    parser.add_argument("--jobs",type=int,default=8)
    parser.add_argument("--count",type=int,default=32)
    args = parser.parse_args()
    puzzles = read_puzzles(args.puzzles)
    bank = read_submission(args.parent)
    donors = [read_submission(f) for f in args.donors]
    with args.bounds.open(encoding="utf-8",newline="") as f:
        lower = {r["id"]:int(r["certified_lower"]) for r in csv.DictReader(f)}
    eligible = sorted((p for p in puzzles if lower[p.id]<len(bank[p.id])<=35 and len(p.seeds)<=5
                       and (not args.puzzle_id or p.id in args.puzzle_id)),key=lambda p:(p.limit,p.id))
    eligible = eligible[:args.count]
    tasks = [(p,bank[p.id],list(dict.fromkeys(d[p.id] for d in donors if p.id in d
              and len(d[p.id]) <= len(bank[p.id])+6)),args.widths) for p in eligible]
    rows,wins = {},{}
    with ProcessPoolExecutor(args.jobs) as pool:
        for pid,tape,row in pool.map(work,tasks,chunksize=1):
            rows[pid] = row
            if len(tape)<len(bank[pid]):
                wins[pid] = tape
                print(pid,len(bank[pid]),len(tape),flush=True)
    args.out.mkdir(exist_ok=True,parents=True)
    write_submission(args.out/"wins.csv",[p for p in puzzles if p.id in wins],wins)
    record = dict(parent_sha256=sha256(args.parent),bounds_sha256=sha256(args.bounds),widths=args.widths,
                  donors={f.name:sha256(f) for f in args.donors},rows=rows)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(record,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(len(bank[i])-len(t) for i,t in wins.items()))


if __name__=="__main__":
    main()
