"""Search for two replacement outputs that reuse an operand and the first output."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import gzip
import json
from itertools import combinations
from pathlib import Path

from fanout_repair import build_frontier
from helper_triangles import removable_together
from interior_bands import compile_on_parent, solve
from quotient_chains import private_cone
from two_sided_chains import reverse_steps
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes


def bridges(first, second, ready, frontier, limit, allowance, anchors):
    """Invert the final joint operation, then try the remaining unary obligation."""
    unavailable = {first, second}
    outputs = [(second, None)]
    if allowance >= 2:
        outputs.extend((middle, edge) for a in anchors
                       for middle, edge in reverse_steps(second, a, limit)
                       if middle not in ready | unavailable)
    for middle, finish in outputs:
        spent = int(finish is not None)
        forbidden = unavailable | {middle}
        for helper, edge in reverse_steps(middle, first, limit):
            if helper in forbidden:
                continue
            for source, start in reverse_steps(first, helper, limit):
                if source in forbidden:
                    continue
                paid = {helper, source} - ready
                if not 0 < len(paid) + spent <= allowance:
                    continue
                births = {v: frontier[v] for v in paid if v in frontier}
                missing = paid - births.keys()
                if missing:
                    if len(missing) != 1 or not births:
                        continue
                    need, = missing
                    bridge, = births
                    for other, recipe in reverse_steps(need, bridge, limit):
                        if other in ready or other == bridge:
                            births[need] = recipe
                            break
                    else:
                        continue
                patch = births | {first: start, middle: edge}
                if finish:
                    patch[second] = finish
                yield patch, bool(finish)


def work(job):
    p, old, pairs, palette, engine, rounds = job
    graph = active_graph(p, first_recipes(p, old))
    targets = set(p.targets)
    consumers = Counter(v for _,a,b in graph.values() for v in {a,b})
    uses = consumers + Counter(targets)
    private = {v:len(private_cone(graph, uses, v)) for v in graph}
    roots = sorted(graph, key=lambda v:(-private[v],v not in targets,-consumers[v],v))[:36]
    ancestors = {v:set() for v in p.seeds}
    for v,(_,a,b) in graph.items():
        ancestors[v] = {a,b} | ancestors[a] | ancestors[b]
    candidates = []
    for a,b in combinations(roots,2):
        removed = removable_together(graph, uses, {a,b})
        if len(removed) >= 2:
            candidates.append((-len(removed), a not in ancestors[b] and b not in ancestors[a],a,b,removed))
    best = old
    warm = {}
    counts = Counter()
    for size, _, a,b,removed in sorted(candidates)[:pairs]:
        keep = {v:e for v,e in graph.items() if v not in removed}
        ready = {v for v in keep.keys() | set(p.seeds) if v not in (a,b) and not ({a,b} & ancestors[v])}
        finish = build_frontier(sorted(ready), ready, p.limit)
        popular = sorted(ready, key=lambda v:(v not in p.seeds,-consumers[v],v))[:palette]
        visited = set()
        for first, second in ((a,b),(b,a)):
            menu = tuple(dict.fromkeys((*[v for v in graph[second][1:] if v in ready],*popular)))
            for patch, extended in bridges(first,second,ready,finish,p.limit,min(-size,3),menu):
                key = tuple(sorted(patch.items()))
                if key in visited or (patch.keys() - {a,b}) & (keep.keys() - ready):
                    continue
                visited.add(key)
                counts["extended" if extended else "direct"] += 1
                tape = compile_on_parent(p,old,keep | patch)
                if tape is None:
                    continue
                counts["compiled"] += 1
                best = min((best,tape),key=len)
                if engine and len(tape) <= len(old)+1:
                    distance = len(graph.keys() ^ first_recipes(p,tape).keys())
                    if distance >= 2:
                        warm[tape] = (len(tape),-distance)
    record = dict(before=len(old),selected=min(pairs,len(candidates)),counts=dict(counts))
    if warm:
        salt = 915739 + int(p.id[-4:])
        direct = solve(engine,p,[old],salt,rounds)
        record["control"] = len(direct)
        best = min((best,direct),key=len)
        record["restarts"] = []
        for candidate in sorted(warm,key=warm.get)[:2]:
            tape = solve(engine,p,[candidate,old],salt,rounds)
            record["restarts"].append([len(candidate),len(tape)])
            best = min((best,tape),key=len)
    record["after"] = check(p,best)
    return p.id,best,record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("puzzles","parent","out"):
        parser.add_argument("--"+key,type=Path,required=True)
    parser.add_argument("--engine",type=Path)
    for key,n in (("count",100),("pairs",20),("palette",20),("jobs",6),("rounds",400)):
        parser.add_argument("--"+key,type=int,default=n)
    args = parser.parse_args()
    puzzles = read_puzzles(args.puzzles)
    parent = read_submission(args.parent)
    selected = sorted((p for p in puzzles if len(parent[p.id]) >= 35),
                      key=lambda p:(-(len(parent[p.id])-len(set(p.targets)-set(p.seeds))),p.id))[:args.count]
    tasks = [(p,parent[p.id],args.pairs,args.palette,args.engine,args.rounds) for p in selected]
    rows, wins = {}, {}
    with ProcessPoolExecutor(args.jobs) as pool:
        for pid,tape,record in pool.map(work,tasks,chunksize=1):
            rows[pid] = record
            if len(tape) < len(parent[pid]):
                wins[pid] = tape
    args.out.mkdir(parents=True,exist_ok=True)
    write_submission(args.out/"wins.csv",[p for p in puzzles if p.id in wins],wins)
    report = dict(parent_sha256=sha256(args.parent), engine_sha256=sha256(args.engine) if args.engine else None,
                  settings={k:v for k,v in vars(args).items() if isinstance(v,int)},rows=rows)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(report,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-len(t) for i,t in wins.items()))


if __name__ == "__main__":
    main()
