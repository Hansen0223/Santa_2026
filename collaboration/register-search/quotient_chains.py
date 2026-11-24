"""Replace private arithmetic cones with backward quotient-and-remainder chains."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import json
from pathlib import Path

from interior_bands import compile_on_parent
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, compile_graph, first_recipes
from solvers.graphs.corpus_prefix import arithmetic_edges


def private_cone(graph, uses, root):
    # Shared internal values can become private when all consumers are removed together.
    removed = {root}
    deleted_uses = Counter()
    pending = [root]
    while pending:
        value = pending.pop()
        for operand in set(graph[value][1:]):
            if operand not in graph:
                continue
            deleted_uses[operand] += 1
            if deleted_uses[operand] == uses[operand]:
                removed.add(operand)
                pending.append(operand)
    return removed


def inverse_chain(puzzle, root, available, budget, width):
    pool = sorted(available)
    # Exact arithmetic over the fixed pool handles the expensive final beam layer.
    finish = {}
    for j, a in enumerate(pool):
        for b in pool[:j+1]:
            for value, recipe in arithmetic_edges(a, b, puzzle.limit):
                if value not in available:
                    finish.setdefault(value, recipe)
    if root in finish:
        return {root: finish[root]}
    moduli = [v for v in pool if 3 <= v < root]
    residue = {}
    for m in moduli:
        table = defaultdict(list)
        for r in pool:
            table[r % m].append(r)
        residue[m] = table
    layers = [{root: ()}] + [{} for _ in range(budget)]
    for depth in range(budget + 1):
        states = layers[depth]
        beam = sorted(states, key=lambda v: (v not in available, v not in finish, v.bit_length(), v))[:width]
        next_layer = layers[depth + 1] if depth < budget else None
        for v in beam:
            path = states[v]
            if v in available:
                return dict(path)
            if depth < budget and v in finish:
                return dict((*path, (v,finish[v])))
            if next_layer is None:
                continue
            for m in moduli:
                if m >= v:
                    break
                y, r = divmod(v, m)
                if not r:
                    next_layer.setdefault(y, (*path, (v,("*", y, m))))
                if depth + 2 > budget:
                    continue
                later = layers[depth + 2]
                for subtract in (False, True):
                    key = (-r if subtract else r) % m
                    for k in residue[m].get(key, ()):
                        base = v + k if subtract else v - k
                        if base <= 0 or base > puzzle.limit:
                            continue
                        y = base // m
                        if y >= v or base in available or base in (m, y):
                            continue
                        if any(x in (v, base, y) for x, _ in path):
                            continue
                        sequence=((v,("-" if subtract else "+",base,k)), (base,("*",y,m)))
                        later.setdefault(y,(*path,*sequence))
        # Add / subtract an already-available value in one step. The predecessor stays positive.
        if next_layer is not None and depth + 1 < budget:
            for v in beam:
                for k in pool:
                    if k >= v:
                        break
                    y = v-k
                    next_layer.setdefault(y, (*states[v], (v,("+",y,k))))
    return None


def work(job):
    puzzle, parent, width, roots = job
    graph = active_graph(puzzle, first_recipes(puzzle,parent))
    uses = Counter(t for t in set(puzzle.targets))
    for _, a, b in graph.values():
        uses.update({a,b})
    cuts = []
    for root in graph:
        if uses[root] != 1 or root.bit_length() < 22:
            continue
        cone = private_cone(graph, uses, root)
        if 4 <= len(cone) <= 10:
            cuts.append((-len(cone),-root.bit_length(),root,cone))
    best = parent
    rows = []
    # Stop after the most promising candidates in this pilot.
    for _, _, root, cone in sorted(cuts)[:roots]:
        fixed = {v: e for v, e in graph.items() if v not in cone}
        available = set(puzzle.seeds)
        for v, (_,a,b) in fixed.items():
            if a in available and b in available:
                available.add(v)
        path = inverse_chain(puzzle, root, available, len(cone)-1, width)
        info = dict(root=root, old=len(cone))
        if path:
            info["path"] = len(path)
            merged = path | fixed
            candidate = compile_on_parent(puzzle, parent, merged)
            if candidate is None or len(candidate) >= len(parent):
                try:
                    live = active_graph(puzzle, merged)
                except (KeyError, ValueError):
                    live = {}
                if live and len(live) < len(parent):
                    info["graph"] = len(live)
                    candidate = compile_graph(puzzle, live, attempts=12, schedule_width=16, operation_width=64)
            if candidate is not None:
                info["physical"] = len(candidate)
                best = min((best,candidate), key=len)
        rows.append(info)
    check(puzzle,best)
    return puzzle.id,best,dict(before=len(parent),after=len(best),eligible=len(cuts),cuts=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("puzzles","parent","out"):
        parser.add_argument("--"+key,type=Path,required=True)
    for key,n in (("count",180),("offset",0),("width",12),("roots",2),("jobs",9)):
        parser.add_argument("--"+key,type=int,default=n)
    args=parser.parse_args()
    puzzles=read_puzzles(args.puzzles)
    parents=read_submission(args.parent)
    order=sorted(puzzles,key=lambda p:(-max(p.targets).bit_length(), p.id))
    jobs=[(p,parents[p.id],args.width,args.roots) for p in order[args.offset:args.offset+args.count]]
    rows,wins={},{}
    with ProcessPoolExecutor(args.jobs) as pool:
        for i,tape,record in pool.map(work,jobs,chunksize=2):
            rows[i]=record
            if len(tape)<len(parents[i]):
                wins[i]=tape
    args.out.mkdir(parents=True,exist_ok=True)
    write_submission(args.out/"wins.csv",[p for p in puzzles if p.id in wins],wins)
    report=dict(parent_sha256=sha256(args.parent),settings={k:v for k,v in vars(args).items() if isinstance(v,int)},rows=rows)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(report,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-len(t) for i,t in wins.items()))


if __name__ == "__main__":
    main()
