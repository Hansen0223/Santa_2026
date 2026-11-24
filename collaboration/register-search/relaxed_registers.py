"""Search with one or more temporary extra registers, then rebuild under the official limit."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import gzip
import json
from pathlib import Path

from interior_bands import compile_on_parent, solve
from quotient_chains import inverse_chain, private_cone
from elf import Puzzle, check, read_puzzles, read_submission, sha256, write_submission
from graph import _allocate, active_graph, compile_graph, first_recipes


class RelaxedPuzzle(Puzzle):
    def __post_init__(self):
        if not 1 <= self.registers <= 64:
            raise ValueError("search register count must be between 1 and 64")
        Puzzle(self.id,self.seeds,self.targets,self.limit,min(self.registers,48))


def pressure(puzzle, graph):
    uses = Counter(x for _,a,b in graph.values() for x in {a,b})
    live = sum(uses[v] > 0 for v in set(puzzle.seeds))
    peak = live
    for v,(_,a,b) in graph.items():
        for x in {a,b}:
            uses[x] -= 1
            live -= uses[x] == 0
        peak = max(peak,live+1)
        live += uses[v] > 0
    return peak


def extra_start(puzzle, parent, root, ext):
    if root is None:
        return parent
    graph = active_graph(puzzle,first_recipes(puzzle,parent))
    if root not in graph:
        return parent
    uses = Counter(set(puzzle.targets))
    for _,a,b in graph.values():
        uses.update({a,b})
    cone = private_cone(graph,uses,root)
    fixed = {v:e for v,e in graph.items() if v not in cone}
    ready = set(puzzle.seeds)
    for v,(_,a,b) in fixed.items():
        if a in ready and b in ready:
            ready.add(v)
    candidate = inverse_chain(puzzle,root,ready,len(cone)-1,12)
    if not candidate:
        return parent
    try:
        merged = active_graph(ext,candidate|fixed)
    except (KeyError, ValueError):
        return parent
    old = [v for v in first_recipes(puzzle,parent) if v in merged and v not in candidate]
    inserted = [v for v in merged if v in candidate]
    inserted_set = set(inserted)
    old_position = {v:i for i,v in enumerate(old)}
    needed = {x for v in inserted for x in merged[v][1:]}-inserted_set-set(puzzle.seeds)
    dependents = [i for i,v in enumerate(old) if inserted_set.intersection(merged[v][1:])]
    low = max((old_position[x]+1 for x in needed),default=0)
    high = min(dependents,default=len(old))
    for insertion in range(low,high+1):
        order = old[:insertion]+inserted+old[insertion:]
        tape = _allocate(ext,{v:merged[v] for v in order},False,0,fixed_order=True)
        if tape is not None and check(ext,tape)<len(parent):
            return tape
    tape = compile_graph(ext,merged,attempts=12,schedule_width=18,operation_width=64)
    return tape if tape is not None and len(tape)<len(parent) else parent


def work(task):
    puzzle, parent, solver, rounds, grids, roots = task
    seed = 516873+int(puzzle.id[-4:])
    control = solve(solver,puzzle,[parent],seed,rounds)
    best = min((parent,control),key=len)
    variants = []
    for extra in grids:
        ext = RelaxedPuzzle(puzzle.id,puzzle.seeds,puzzle.targets,puzzle.limit,puzzle.registers+extra)
        start = extra_start(puzzle,parent,roots.get(puzzle.id),ext)
        tape = solve(solver,ext,[start],seed,rounds)
        info = dict(extra=extra,start=len(start),relaxed=len(tape))
        if len(tape)<len(parent):
            graph = active_graph(ext,first_recipes(ext,tape))
            restored = compile_on_parent(puzzle,parent,graph)
            if restored is None or len(restored)>=len(parent):
                restored = compile_graph(puzzle,graph,attempts=8,schedule_width=12,operation_width=40)
            if restored is not None:
                info['strict']=len(restored)
                best = min((best,restored),key=len)
        variants.append(info)
    check(puzzle,best)
    return puzzle.id,best,dict(before=len(parent),control=len(control),variants=variants,after=len(best))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('puzzles','parent','solver','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    for name,n in (('count',100),('offset',0),('jobs',8),('rounds',500)):
        parser.add_argument('--'+name,type=int,default=n)
    parser.add_argument('--extra',nargs='+',type=int,default=[1,4])
    parser.add_argument('--root',action='append',default=[],metavar='PUZZLE:VALUE')
    args=parser.parse_args()
    if any(extra<1 for extra in args.extra):
        parser.error('extra register counts must be positive')
    root_overrides={i:int(v) for i,v in (arg.split(':',1) for arg in args.root)}
    puzzles=read_puzzles(args.puzzles)
    parents=read_submission(args.parent)
    def priority(p):
        tape=parents[p.id]
        nominal=first_recipes(p,tape)
        return (p.id not in root_overrides,-pressure(p,nominal),-len(tape),p.id)
    order=sorted((p for p in puzzles if len(parents[p.id])>=34),key=priority)
    tasks=[(p,parents[p.id],args.solver,args.rounds,args.extra,root_overrides) for p in order[args.offset:args.offset+args.count]]
    rows,wins={},{}
    with ThreadPoolExecutor(args.jobs) as pool:
        for i,tape,row in pool.map(work,tasks):
            rows[i]=row
            if len(tape)<len(parents[i]):
                wins[i]=tape
    args.out.mkdir(parents=True,exist_ok=True)
    data=dict(parent_sha256=sha256(args.parent),solver_sha256=sha256(args.solver),extra=args.extra,
              roots=root_overrides,settings={k:v for k,v in vars(args).items() if isinstance(v,int)},rows=rows)
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0))
    write_submission(args.out/'wins.csv',[p for p in puzzles if p.id in wins],wins)
    print(len(rows),len(wins),sum(rows[i]['before']-len(tape) for i,tape in wins.items()))


if __name__=='__main__':
    main()
