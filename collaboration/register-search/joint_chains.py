"""Combine alternate arithmetic chains that share a newly computed value."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path

from two_sided_chains import arithmetic_edges, check, private_cone, read_puzzles, read_submission, search, sha256, write_submission
from interior_bands import compile_on_parent
from graph import active_graph, first_recipes


def reachable(puzzle, graph):
    values = set(puzzle.seeds)
    for v, (_, a, b) in graph.items():
        if a in values and b in values:
            values.add(v)
    return values


def candidates(puzzle, graph, root, cone, width):
    remaining = {v:e for v,e in graph.items() if v not in cone}
    available = reachable(puzzle, remaining)
    pool = sorted(available)
    finish = {}
    for j,a in enumerate(pool):
        for b in pool[:j+1]:
            for v,e in arithmetic_edges(a,b,puzzle.limit):
                if v not in available:
                    finish.setdefault(v,e)
    options = {}
    for path in search(puzzle, root, pool, finish, len(cone)+1, width):
        if path:
            options.setdefault(frozenset(path.items()),path)
    return sorted(options.values(),key=len)


def work(task):
    puzzle,parent,root_count,width = task
    graph = active_graph(puzzle,first_recipes(puzzle,parent))
    uses = Counter(set(puzzle.targets))
    for _,a,b in graph.values():
        uses.update({a,b})
    cuts = []
    for root in graph:
        if uses[root] != 1 or root.bit_length() < 20:
            continue
        cone = private_cone(graph,uses,root)
        if 4 <= len(cone) <= 10:
            cuts.append((-len(cone),-root.bit_length(),root,cone))
    arms = []
    seen = defaultdict(list)
    proposals = []
    pairs = set()
    for _,_,root,cone in sorted(cuts)[:root_count]:
        for path in candidates(puzzle,graph,root,cone,width):
            # A value in the old graph may be computed already, so pair by genuinely new values.
            novel = path.keys() - graph.keys()
            for value in sorted(novel):
                for j in seen[value]:
                    old_root, old_cone, other = arms[j]
                    if old_root == root or cone & old_cone:
                        continue
                    self_id = len(arms)
                    pair = (j,self_id)
                    if pair in pairs:
                        continue
                    pairs.add(pair)
                    gross = len(cone) + len(old_cone) - len(path.keys() | other.keys())
                    if gross > 0:
                        proposals.append((-gross,j,self_id))
                seen[value].append(len(arms))
            arms.append((root,cone,path))
    best = parent
    trials = []
    for _,j,k in sorted(proposals)[:16]:
        r1,c1,a = arms[j]
        r2,c2,b = arms[k]
        fixed = {v:e for v,e in graph.items() if v not in (c1 | c2)}
        legal = []
        for replacements in (a | b,b | a):
            candidate = compile_on_parent(puzzle,parent,replacements | fixed)
            if candidate is not None:
                legal.append(len(candidate))
                best = min((candidate,best),key=len)
        trials.append(dict(roots=[r1,r2],shared=sorted(a.keys() & b.keys()),costs=[len(a),len(b)],physical=legal))
    check(puzzle,best)
    return puzzle.id,best,dict(before=len(parent),after=len(best),arms=len(arms),pairs=len(pairs),proposals=len(proposals),trials=trials)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("puzzles","parent","out"):
        parser.add_argument("--"+name,type=Path,required=True)
    for name,default in (("count",145),("offset",0),("roots",14),("width",14),("jobs",8)):
        parser.add_argument("--"+name,type=int,default=default)
    args=parser.parse_args()
    puzzles=read_puzzles(args.puzzles)
    bank=read_submission(args.parent)
    order=sorted(puzzles,key=lambda p:hashlib.sha256(("joint-chains1-"+p.id).encode()).digest())
    jobs=[(p,bank[p.id],args.roots,args.width) for p in order[args.offset:args.offset+args.count]]
    rows,wins={},{}
    with ProcessPoolExecutor(args.jobs) as pool:
        for i,tape,row in pool.map(work,jobs,chunksize=3):
            rows[i]=row
            if len(tape)<len(bank[i]):
                wins[i]=tape
    args.out.mkdir(parents=True,exist_ok=True)
    write_submission(args.out/"wins.csv",[p for p in puzzles if p.id in wins],wins)
    info=dict(parent_sha256=sha256(args.parent),settings={k:v for k,v in vars(args).items() if isinstance(v,int)},rows=rows)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(info,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-len(t) for i,t in wins.items()))


if __name__=="__main__":
    main()
