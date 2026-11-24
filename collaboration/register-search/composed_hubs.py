"""Price the joint replacement of several old values through one two-step hub."""
import argparse
from bisect import bisect_left
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
from itertools import combinations_with_replacement
import json
from pathlib import Path
import sys

from interior_bands import ROOT, solve
from helper_triangles import removable_together
from quotient_chains import private_cone
from two_sided_chains import reverse_steps
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes
from solvers.graphs.corpus_prefix import arithmetic_edges

sys.path.insert(0, str(ROOT / "collaboration/structure-controls/ruler"))
from selector import compile_selection


def menu(puzzle, graph, width, per_hub, split, favor_reachable, optimistic):
    uses = Counter(set(puzzle.targets))
    for _, a, b in graph.values():
        uses.update({a, b})
    original = set(puzzle.seeds) | graph.keys()
    operands = sorted(original)
    ancestors = dict.fromkeys(puzzle.seeds, frozenset())
    for v, (_, a, b) in graph.items():
        ancestors[v] = ancestors[a] | ancestors[b] | {a,b}

    cones = {v: private_cone(graph, uses, v) for v in graph}
    demands = defaultdict(dict)
    for root in graph:
        for operand in operands:
            if operand in cones[root] or root in ancestors[operand]:
                continue
            for hub, edge in reverse_steps(root, operand, puzzle.limit):
                if hub not in original:
                    demands[hub].setdefault(root, edge)
    grouped = []
    for hub, roots in demands.items():
        if len(roots) >= 2:
            max_saving = len(removable_together(graph, uses, set(roots)))
            if max_saving >= 2:
                grouped.append((-max_saving, -len(roots), hub))
    if not grouped:
        return [], [], dict(hubs=0)

    one = defaultdict(list)
    for a, b in combinations_with_replacement(operands,2):
        for value, edge in arithmetic_edges(a,b,puzzle.limit):
            if value not in original and len(one[value]) < 3:
                one[value].append(edge)
    if not one:
        return [], [], dict(hubs=len(grouped), selected=0)

    if favor_reachable:
        frontier = sorted(one)

        def nearest(entry):
            saving, users, value = entry
            i = bisect_left(frontier,value)
            delta = min(abs(value-frontier[j]) for j in (i-1,i) if 0 <= j < len(frontier))
            return delta.bit_length(), saving, users, delta, value

        ready = sorted(entry for entry in grouped if entry[-1] in one)[:width]
        remaining = (entry for entry in grouped if entry[-1] not in one)
        group = ready + sorted(remaining,key=nearest)[:width]
    else:
        group = sorted(grouped)[:width]

    def offer(hub, path):
        inputs = {x for _,a,b in path.values() for x in (a,b) if x in original}
        protected = inputs | set().union(*(ancestors[x] for x in inputs))
        roots = {root: edge for root, edge in demands[hub].items() if optimistic or root not in protected}
        if len(roots) < 2:
            return None
        referenced = {x for _,a,b in roots.values() for x in (a,b) if x in original}
        kept = protected | referenced | set().union(*(ancestors[x] for x in referenced))
        can_remove = removable_together(graph,uses,set(roots))
        protected_net = len(can_remove - kept) - len(path)
        net = len(can_remove) - len(path) if optimistic else protected_net
        if net <= 0:
            return None
        return ((-net, -protected_net), tuple(sorted(path.items())), roots)

    baseline, nested = {}, {}
    hits = Counter()
    for _,_,hub in group:
        options = [[],[]]
        for edge in one.get(hub,()):
            candidate = offer(hub,{hub:edge})
            if candidate:
                options[0].append(candidate)
        for operand in operands:
            for middle, edge in reverse_steps(hub,operand,puzzle.limit):
                if middle == hub:
                    continue
                for step in one.get(middle,()):
                    candidate = offer(hub,{middle:step,hub:edge})
                    if candidate:
                        options[1].append(candidate)
        if split and not options[1]:
            # Consider a hub that combines two fresh operands rather than a chain.
            for first in one:
                if first == hub:
                    continue
                for second, edge in reverse_steps(hub,first,puzzle.limit):
                    if not first < second or second == hub or second not in one:
                        continue
                    candidate = offer(hub,{first:one[first][0],second:one[second][0],hub:edge})
                    if candidate:
                        options[1].append(candidate)
        for name, edges, candidates in (("direct",baseline,options[0]),("composed",nested,options[1])):
            if candidates:
                hits[name] += 1
            unique = {(cost,path):roots for cost,path,roots in candidates}
            for cost, path in sorted(unique)[:per_hub]:
                for value, operation in (*path,*unique[cost,path].items()):
                    edges[value,operation] = {value:operation}
    return list(baseline.values()),list(nested.values()),dict(hubs=len(grouped),selected=len(group),**hits)


def work(job):
    puzzle, tape, width, per_hub, split, favor_reachable, optimistic, engine, rounds = job
    graph = active_graph(puzzle, first_recipes(puzzle, tape))
    direct, composed, counts = menu(puzzle, graph, width, per_hub, split, favor_reachable, optimistic)
    best = tape
    info = dict(before=len(tape), **counts)
    if direct:
        info["control"], candidate = compile_selection(puzzle,tape,graph,direct,optimistic)
        best = min((best,candidate),key=len)
    if composed:
        if engine:
            known = set(puzzle.seeds) | graph.keys()
            required = [(v, e) for path in composed for v,e in path.items()
                        if v not in known and any(x not in known for x in e[1:])]
            if required:
                info["start_model"], candidate = compile_selection(
                    puzzle,tape,graph,direct+composed,optimistic,omit_old=2,slack=1,required_recipes=required
                )
                if candidate is not None:
                    changed = active_graph(puzzle,first_recipes(puzzle,candidate))
                    used = any(v in changed and changed[v][0] == e[0] and
                               (changed[v][1:] == e[1:] or e[0] in "+*" and changed[v][1:] == e[1:][::-1])
                               for v,e in required)
                    info["start_uses_hub"] = used
                if candidate is not None and used:
                    seed = 649923 + int(puzzle.id[-4:])
                    plain = solve(engine,puzzle,[tape],seed,rounds)
                    refined = solve(engine,puzzle,[candidate,tape],seed,rounds)
                    best = min((best,plain,candidate,refined),key=len)
                    info["trajectory"] = dict(start=len(candidate), control=len(plain), final=len(refined))
        else:
            info["composed_model"], candidate = compile_selection(puzzle,tape,graph,direct+composed,optimistic)
            best = min((best,candidate),key=len)
    info["after"] = check(puzzle, best)
    return puzzle.id,best,info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("puzzles","parent","out"):
        parser.add_argument("--"+name,type=Path,required=True)
    for name, default in (("count",120),("offset",0),("width",35),("per-hub",4),("jobs",8),("rounds",600)):
        parser.add_argument("--"+name,type=int,default=default)
    parser.add_argument("--engine",type=Path,help="Refine an alternate near-tie start instead of strict graph selection.")
    parser.add_argument("--split",action="store_true")
    parser.add_argument("--favor-reachable",action="store_true")
    parser.add_argument("--optimistic",action="store_true",help="Allow original inputs to be rederived jointly.")
    args = parser.parse_args()
    puzzles = read_puzzles(args.puzzles)
    bank = read_submission(args.parent)
    eligible = sorted((p for p in puzzles if len(bank[p.id]) >= 40),
                      key=lambda p:hashlib.sha256(("paid-shared-hub-"+p.id).encode()).digest())
    selected = eligible[args.offset:args.offset+args.count]
    jobs = [(p,bank[p.id],args.width,args.per_hub,args.split,args.favor_reachable,args.optimistic,args.engine,args.rounds)
            for p in selected]
    rows,wins = {},{}
    with ProcessPoolExecutor(args.jobs) as executor:
        for i,tape,row in executor.map(work,jobs,chunksize=1):
            rows[i] = row
            if len(tape) < len(bank[i]):
                wins[i] = tape
                print(i,len(bank[i]),len(tape),flush=True)
    args.out.mkdir(exist_ok=True,parents=True)
    write_submission(args.out/"wins.csv",[p for p in puzzles if p.id in wins],wins)
    settings = {k:v for k,v in vars(args).items() if isinstance(v,int)}
    report = dict(parent_sha256=sha256(args.parent),settings=settings,eligible=len(eligible),rows=rows)
    if args.engine:
        report["engine_sha256"] = sha256(args.engine)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(report,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-len(tape) for i,tape in wins.items()))


if __name__ == "__main__":
    main()
