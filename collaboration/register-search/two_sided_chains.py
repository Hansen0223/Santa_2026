"""Meet a backwards quotient search with exact short constructions from the fixed graph."""
import argparse
from bisect import bisect_left
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import gzip
from heapq import nsmallest
import json
from pathlib import Path

from interior_bands import compile_on_parent
from quotient_chains import private_cone
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes
from solvers.graphs.corpus_prefix import arithmetic_edges


def reverse_steps(value, operand, cap):
    if value > operand:
        yield value - operand, ("+", value - operand, operand)
    if value <= cap - operand:
        yield value + operand, ("-", value + operand, operand)
    if operand > value:
        yield operand - value, ("-", operand, operand - value)
    if operand > 1 and value % operand == 0:
        yield value // operand, ("*", value // operand, operand)
    if operand > 1 and value <= cap // operand:
        yield value * operand, ("/", value * operand, operand)
    if operand > value and operand % value == 0:
        yield operand // value, ("/", operand, operand // value)


def substitutions(puzzle, value, pool, finish):
    for operand in pool:
        for predecessor, edge in reverse_steps(value, operand, puzzle.limit):
            if predecessor not in (value, operand) and predecessor in finish:
                yield {value: edge, predecessor: finish[predecessor]}
    # Doubling needs only one new helper when both operands are the same.
    if value % 2 == 0 and value // 2 in finish:
        half = value // 2
        yield {value: ("+",half,half),half:finish[half]}


def search(puzzle, root, pool, finish, budget, width, *, proximity=False):
    available = set(pool)
    anchors = sorted(available | finish.keys()) if proximity else None
    pending = {root: ()}
    attempts = []

    def near(value):
        i = bisect_left(anchors, value)
        gap = min(abs(value - anchors[j]) for j in (i-1, i) if 0 <= j < len(anchors))
        return gap.bit_length(), gap, value

    for depth in range(budget + 1):
        priority = lambda v: (v not in available,v not in finish,v.bit_length(),v)
        beam = nsmallest(width, pending, key=priority)
        if anchors and len(pending) > width:
            chosen = beam[:(width+1)//2]
            beam = chosen + nsmallest(width-len(chosen), pending.keys()-set(chosen), key=near)
        next_pending = {}
        for v in beam:
            prefix = dict(pending[v])
            if v in available:
                attempts.append(prefix)
                continue
            if depth < budget and v in finish:
                attempts.append(prefix | {v: finish[v]})
                continue
            if depth + 2 <= budget:
                for suffix in substitutions(puzzle,v,pool,finish):
                    if not (suffix.keys() & prefix.keys()):
                        attempts.append(prefix | suffix)
                        if len(attempts) >= 12:
                            return attempts
            if depth + 3 > budget:
                continue
            for operand in pool:
                for prior, edge in reverse_steps(v,operand,puzzle.limit):
                    if prior in (v,operand) or prior in prefix:
                        continue
                    next_pending.setdefault(prior,(*pending[v],(v,edge)))
        if len(attempts) >= 8:
            break
        pending = next_pending
        if not pending:
            break
    return attempts


def split_three(puzzle, root, finish):
    # Both operands have a one-step definition using the fixed pool.
    for a in sorted(finish,key=lambda v:(v.bit_length(),v)):
        for b, edge in reverse_steps(root,a,puzzle.limit):
            if a<=b and b!=root and a!=root and b in finish:
                yield {root:edge,a:finish[a],b:finish[b]}
            elif edge[0] in "-/" and b<a and b!=root and a!=root and b in finish:
                yield {root:edge,a:finish[a],b:finish[b]}


def work(task):
    puzzle,parent,root_count,width,shared,proximity = task
    original = first_recipes(puzzle,parent)
    graph = active_graph(puzzle,original)
    targets = set(puzzle.targets)
    consumers = Counter()
    for _, a, b in graph.values():
        consumers.update({a,b})
    uses = consumers + Counter(targets)
    owner = {value: 1 << j for j, value in enumerate(sorted(targets))} if shared else {}
    if shared:
        for value, (_, a, b) in reversed(graph.items()):
            for operand in {a,b}:
                owner[operand] = owner.get(operand,0) | owner.get(value,0)
    cuts = []
    for v in graph:
        support = owner.get(v,0).bit_count()
        wanted = (consumers[v] >= 2 and support >= 2) if shared else uses[v] == 1
        if not wanted or v.bit_length() < 21:
            continue
        cone = private_cone(graph,uses,v)
        if 4 <= len(cone) <= 10:
            cuts.append((-len(cone),-support,-v.bit_length(),v,cone))
    best = parent
    rows = []
    for _,_,_,root,removed in sorted(cuts)[:root_count]:
        fixed = {v:e for v,e in graph.items() if v not in removed}
        available = set(puzzle.seeds)
        for v, (_,a,b) in fixed.items():
            if a in available and b in available:
                available.add(v)
        pool = sorted(available)
        finish = {}
        for j,a in enumerate(pool):
            for b in pool[:j+1]:
                for v,e in arithmetic_edges(a,b,puzzle.limit):
                    if v not in available:
                        finish.setdefault(v,e)
        candidates = []
        if root in finish:
            candidates.append({root: finish[root]})
        if root not in finish:
            for idx,path in enumerate(split_three(puzzle,root,finish)):
                candidates.append(path)
                if idx == 5:
                    break
        candidates.extend(search(puzzle,root,pool,finish,len(removed)-1,width,proximity=proximity))
        trial = set()
        tried = 0
        for path in sorted(candidates,key=len):
            if not path:
                continue
            key = frozenset(path.items())
            if key in trial:
                continue
            trial.add(key)
            tried += 1
            candidate = compile_on_parent(puzzle,parent,path | fixed)
            if candidate is not None and len(candidate)<len(best):
                best = candidate
        rows.append(dict(root=root,old=len(removed),tries=tried,shortest=min(map(len,candidates),default=None),
                         targets=owner.get(root,0).bit_count() if shared else None))
    check(puzzle,best)
    return puzzle.id,best,dict(before=len(parent),after=len(best),cuts=rows,eligible=len(cuts))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("puzzles","parent","out"):
        parser.add_argument("--"+name,type=Path,required=True)
    for name, default in (("count",96),("offset",0),("roots",3),("width",18),("jobs",9)):
        parser.add_argument("--"+name,type=int,default=default)
    parser.add_argument("--shared",action="store_true",help="Rebuild roots used in at least two target branches.")
    parser.add_argument("--proximity",action="store_true",help="Keep some numbers near the single-operation frontier.")
    args=parser.parse_args()
    puzzles=read_puzzles(args.puzzles)
    bank=read_submission(args.parent)
    import hashlib
    order=sorted(puzzles,key=lambda p:hashlib.sha256(("two-sided1-"+p.id).encode()).digest())
    task=[(p,bank[p.id],args.roots,args.width,args.shared,args.proximity)
          for p in order[args.offset:args.offset+args.count]]
    rows,wins={},{}
    with ProcessPoolExecutor(args.jobs) as pool:
        for i,tape,row in pool.map(work,task,chunksize=2):
            rows[i]=row
            if len(tape)<len(bank[i]):
                wins[i]=tape
                print(i,len(bank[i]),len(tape),flush=True)
    args.out.mkdir(parents=True,exist_ok=True)
    write_submission(args.out/"wins.csv",[p for p in puzzles if p.id in wins],wins)
    data=dict(parent_sha256=sha256(args.parent),settings={k:v for k,v in vars(args).items() if isinstance(v,int)},rows=rows)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(data,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-len(t) for i,t in wins.items()))


if __name__=="__main__":
    main()
