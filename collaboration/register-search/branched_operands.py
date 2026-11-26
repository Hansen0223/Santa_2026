"""Replace expensive private cones using two operands that can share their construction."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
from math import isqrt
from pathlib import Path

from fanout_repair import build_frontier
from interior_bands import compile_on_parent
from quotient_chains import private_cone
from two_sided_chains import reverse_steps
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes
from solvers.graphs.corpus_prefix import arithmetic_edges


def candidates(root, ready, first, limit, budget, width, anchor_count):
    """Join an exact inverse from the root with one- and two-step operand births."""
    anchors = sorted(ready,key=lambda v:(abs(v-root).bit_length(),v))[:anchor_count]
    newborn = sorted(first,key=lambda v:(abs(v-root).bit_length(),v.bit_length(),v))[:width]
    offers = {}
    for left in newborn:
        if left == root:
            continue
        for right, outer in reverse_steps(root,left,limit):
            if right in ready or right in (root,left):
                continue
            if right in first:
                offers.setdefault((left,right),{left:first[left],right:first[right],root:outer})
                continue
            # Prefer using the first operand again to make the second.
            for other, edge in reverse_steps(right,left,limit):
                if other in ready or other == left:
                    offers.setdefault((left,right),{left:first[left],right:edge,root:outer})
                    break
            else:
                if budget < 4:
                    continue
                for anchor in anchors:
                    for mid, edge in reverse_steps(right,anchor,limit):
                        if mid in first and mid not in (root,right,left):
                            offers.setdefault((left,right),{left:first[left],mid:first[mid],right:edge,root:outer})
                            break
                    if (left,right) in offers:
                        break
    # The inverse helper deliberately omits identities such as a+a; handle the useful case here.
    if root % 2 == 0 and root // 2 in first:
        half=root//2
        offers[(half,half,"+")]={half:first[half],root:("+",half,half)}
    square=isqrt(root)
    if square*square==root and square!=root and square in first:
        offers[(square,square,"*")]={square:first[square],root:("*",square,square)}
    return sorted(offers.values(),key=lambda patch:(len(patch),sum(v.bit_length() for v in patch),tuple(sorted(patch))))


def shared_operands(root, ready, first, limit):
    """Solve for x in expressions combining x with an arithmetic use of x and a."""
    offers = {}
    for a in sorted(ready):
        divisors = ((root+a,2), (root-a,2), (root,a+1), (root,a-1),
                    (a,root+1), (a,root-1), (a*root,root+1), (a*root,root-1),
                    (a*root,a+1), (a*root,a-1))
        options = {n//d for n,d in divisors if n>0 and d>0 and n%d==0}
        square_values = [a*root]
        if root % a == 0:
            square_values.append(root//a)
        if a % root == 0:
            square_values.append(a//root)
        for value in square_values:
            x = isqrt(value)
            if x*x == value:
                options.add(x)
        for linear,constant in ((a,-root),(-a,-root),(-a,root),
                                (-root,a),(-root,-a),(root,-a)):
            discriminant = linear*linear-4*constant
            if discriminant < 0:
                continue
            square = isqrt(discriminant)
            if square*square == discriminant:
                for numerator in (-linear-square,-linear+square):
                    if numerator>0 and numerator%2==0:
                        options.add(numerator//2)

        for x in sorted((options & first.keys()) - {root}):
            for y,inner in arithmetic_edges(x,a,limit):
                if y in ready or y in (x,root):
                    continue
                for value,outer in arithmetic_edges(x,y,limit):
                    if value == root:
                        offers.setdefault((x,y), {x:first[x],y:inner,root:outer})
    return sorted(offers.values(),key=lambda patch:(sum(v.bit_length() for v in patch),tuple(sorted(patch))))


def work(task):
    puzzle, parent, maximum_roots, width, anchors, algebraic = task
    graph = active_graph(puzzle,first_recipes(puzzle,parent))
    targets = set(puzzle.targets)
    uses = Counter(targets)
    for _,a,b in graph.values():
        uses.update({a,b})
    options = []
    for root in graph:
        cone=private_cone(graph,uses,root)
        if len(cone)>=4:
            options.append((-len(cone),root not in targets,root,cone))
    best=parent
    records=[]
    for neg_size,_,root,cone in sorted(options)[:maximum_roots]:
        fixed={v:edge for v,edge in graph.items() if v not in cone}
        ready=set(puzzle.seeds)
        for v,(_,a,b) in fixed.items():
            if a in ready and b in ready:
                ready.add(v)
        first=build_frontier(sorted(ready),ready,puzzle.limit)
        budget=min(4,-neg_size-1)
        proposals = (shared_operands(root,ready,first,puzzle.limit) if algebraic
                     else candidates(root,ready,first,puzzle.limit,budget,width,anchors))
        scheduled=[]
        for patch in proposals[:24]:
            if len(patch)>budget or (patch.keys()-{root}) & (fixed.keys()-ready):
                continue
            candidate=compile_on_parent(puzzle,parent,fixed|patch)
            if candidate is not None:
                scheduled.append(len(candidate))
                best=min((candidate,best),key=len)
        records.append(dict(root=root,old_size=-neg_size,proposals=len(proposals),scheduled=scheduled))
    return puzzle.id,best,dict(before=len(parent),after=check(puzzle,best),selected=records)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ("puzzles","parent","out"):
        parser.add_argument("--"+key,type=Path,required=True)
    for key,default in (("count",160),("jobs",6),("width",160),("roots",8),("anchors",18)):
        parser.add_argument("--"+key,type=int,default=default)
    parser.add_argument("--algebraic",action="store_true",help="Solve the shared-operand form directly")
    parser.add_argument("--smallest",action="store_true",help="Prioritize smaller target values")
    args=parser.parse_args()
    puzzles=read_puzzles(args.puzzles)
    parents=read_submission(args.parent)
    direction=1 if args.smallest else -1
    ranked=sorted((p for p in puzzles if len(parents[p.id])>=28),
                  key=lambda p:(direction*sum(v.bit_length() for v in p.targets)/len(p.targets),p.id))
    selected=ranked[:args.count]
    jobs=[(p,parents[p.id],args.roots,args.width,args.anchors,args.algebraic) for p in selected]
    rows,wins={},{}
    with ProcessPoolExecutor(args.jobs) as pool:
        for future in as_completed(pool.submit(work,job) for job in jobs):
            pid,tape,record=future.result()
            rows[pid]=record
            if record["after"]<record["before"]:
                wins[pid]=tape
                print(pid,record["before"],record["after"],flush=True)
    args.out.mkdir(parents=True,exist_ok=True)
    write_submission(args.out/"wins.csv",[p for p in puzzles if p.id in wins],wins)
    receipt=dict(parent_sha256=sha256(args.parent),puzzles_sha256=sha256(args.puzzles),
                 settings={k:v for k,v in vars(args).items() if isinstance(v,int)},
                 rows={p.id:rows[p.id] for p in selected})
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(receipt,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-rows[i]["after"] for i in wins))


if __name__=="__main__":
    main()
