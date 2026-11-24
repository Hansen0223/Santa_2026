"""Recover a common multiplier from two outputs and two retained offsets."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
from itertools import combinations
import json
from math import gcd
from pathlib import Path

from fanout_repair import build_frontier
from helper_triangles import removable_together
from interior_bands import compile_on_parent, solve
from quotient_chains import private_cone
from two_sided_chains import reverse_steps
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes


def offsets(root, nearby, limit):
    yield root, None
    for value in nearby:
        if 0 < root-value <= limit:
            yield root-value, ("+", root-value, value)
        if root+value <= limit:
            yield root+value, ("-", root+value, value)
        if value > root:
            yield value-root, ("-", value, value-root)


def reachable(value, ready, one_step, cap, extra):
    if value in ready:
        return {}
    if value in one_step:
        return {value:one_step[value]}
    if extra:
        for operand in extra:
            for helper, edge in reverse_steps(value, operand, cap):
                if helper!=value and helper in one_step:
                    return {helper:one_step[helper], value:edge}
    return None


def extensions(value, available, newly_available, cap):
    for first in newly_available:
        for second, edge in reverse_steps(value, first, cap):
            if second in available and value not in edge[1:]:
                return {value:edge}
    return None


def propose(puzzle, a, b, ready, offsets_a, offsets_b, allowance, partial, cross, stats):
    one_step = build_frontier(sorted(ready),ready,puzzle.limit)
    options = {}
    for x, fix_a in offsets(a, offsets_a, puzzle.limit):
        for y, fix_b in offsets(b, offsets_b, puzzle.limit):
            if x==b or y==a or x==y and not cross:
                continue
            shared = gcd(x,y)
            if shared <= 1:
                continue
            dividers = (1,2,3,4,5,7,8,9,10,16) if partial else (1,)
            for d in dividers:
                if shared%d:
                    continue
                factor = shared//d
                if factor in ready or factor in (a,b) or factor < 2:
                    continue
                q,r = x//factor,y//factor
                if min(q,r)<2 or a in (q,r) or b in (q,r):
                    continue
                if factor not in one_step:
                    continue
                key = (x,y,factor,fix_a,fix_b)
                options[key] = (q,r)
    stats["common_factors"] += len(options)
    priority = sorted(options,key=lambda k:(
        sum(x not in ready and x not in one_step for x in options[k]),
        int(k[3] is not None)+int(k[4] is not None),
        sum(v.bit_length() for v in options[k]),k[2],k[0],k[1]))
    cache = {}
    for key in priority[:240]:
        x,y,factor,fix_a,fix_b = key
        q,r = options[key]
        if set((q,r,factor)) & ({x,y,a,b} - ready):
            continue
        for first, second in ((q, r), (r, q)) if cross else ((q,r),):
            patch = {factor: one_step[factor]}
            for v in (first, second):
                if v in patch:
                    continue
                if v not in cache:
                    pool = offsets_a[:8] if partial else ()
                    cache[v] = reachable(v,ready,one_step,puzzle.limit,pool)
                ancestry = cache[v]
                if cross and (ancestry is None or len(ancestry)>1):
                    joint = extensions(v, ready | patch.keys(), tuple(patch), puzzle.limit)
                    if joint is not None:
                        ancestry = joint
                if ancestry is None or ancestry.keys() & {a,b,x,y}:
                    break
                patch.update(ancestry)
            else:
                if x not in ready:
                    patch[x] = ("*",factor,q)
                if y not in ready:
                    patch[y] = ("*",factor,r)
                if fix_a:
                    patch[a] = fix_a
                if fix_b:
                    patch[b] = fix_b
                if len(patch)<=allowance:
                    stats["priced"] += 1
                    yield patch


def work(task):
    p,old,count,palette,partial,cross,engine,rounds=task
    graph=active_graph(p,first_recipes(p,old))
    targets=set(p.targets)
    users=Counter(x for _,a,b in graph.values() for x in {a,b})
    uses=users+Counter(targets)
    private={v:len(private_cone(graph,uses,v)) for v in graph}
    leaves=sorted((v for v in graph if private[v]>=3 and v.bit_length()>=16),
                  key=lambda v:(-private[v],v not in targets,users[v],-v.bit_length(),v))[:22]
    candidates=[]
    ancestors={v:set() for v in p.seeds}
    for v,(_,a,b) in graph.items():
        ancestors[v]={a,b}|ancestors[a]|ancestors[b]
    for a,b in combinations(leaves,2):
        if a in ancestors[b] or b in ancestors[a]:
            continue
        removed=removable_together(graph,uses,{a,b})
        if len(removed)>=4:
            candidates.append((-len(removed),a,b,removed))
    best=old
    stats=Counter()
    warm={}
    for score,a,b,removed in sorted(candidates)[:count]:
        roots={a,b}
        fixed={v:e for v,e in graph.items() if v not in removed}
        ready={v for v in (set(p.seeds)|fixed.keys())-roots if not roots & ancestors[v]}
        popular=sorted(ready,key=lambda v:(v not in p.seeds,-users[v],v.bit_length(),v))[:palette]
        a_offsets=tuple(dict.fromkeys((*(v for v in graph[a][1:] if v in ready),*popular)))
        b_offsets=tuple(dict.fromkeys((*(v for v in graph[b][1:] if v in ready),*popular)))
        allowance=-score+2+(1 if engine else -1)
        for patch in propose(p,a,b,ready,a_offsets,b_offsets,allowance,partial,cross,stats):
            candidate=compile_on_parent(p,old,fixed|patch)
            if candidate is None:
                continue
            best=min((best,candidate),key=len)
            stats["scheduled"]+=1
            if engine and len(candidate)<=len(old)+1:
                distance=len(graph.keys()^first_recipes(p,candidate).keys())
                if distance>=2:
                    warm[candidate]=(-distance,len(candidate),a,b)
    record=dict(before=len(old),eligible=len(candidates),selected=min(count,len(candidates)),counts=dict(stats))
    if warm:
        salt=728167+int(p.id[-4:])
        direct=solve(engine,p,[old],salt,rounds)
        best=min((best,direct),key=len)
        record["control"]=len(direct)
        record["starts"]=[]
        for seed in sorted(warm,key=warm.get)[:2]:
            next_candidate=solve(engine,p,[seed,old],salt,rounds)
            best=min((best,next_candidate),key=len)
            record["starts"].append([len(seed),len(next_candidate),*warm[seed]])
    record["after"]=check(p,best)
    return p.id,best,record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("puzzles","parent","out"):
        parser.add_argument("--"+name,type=Path,required=True)
    parser.add_argument("--engine",type=Path)
    parser.add_argument("--partial",action="store_true")
    parser.add_argument("--cross-quotient",action="store_true")
    for k,v in (("count",160),("pairs",4),("palette",24),("jobs",8),("offset",0),("rounds",420)):
        parser.add_argument("--"+k,type=int,default=v)
    args=parser.parse_args()
    puzzles=read_puzzles(args.puzzles)
    bank=read_submission(args.parent)
    order=sorted((p for p in puzzles if len(bank[p.id])>=45),
                 key=lambda p:hashlib.sha256(("common-factor-offset-"+p.id).encode()).digest())
    selected=order[args.offset:args.offset+args.count]
    tasks=[(p,bank[p.id],args.pairs,args.palette,args.partial,args.cross_quotient,args.engine,args.rounds) for p in selected]
    rows,wins={},{}
    with ProcessPoolExecutor(args.jobs) as pool:
        for i,tape,row in pool.map(work,tasks,chunksize=1):
            rows[i]=row
            if len(tape)<len(bank[i]):
                wins[i]=tape
                print(i,len(bank[i]),len(tape),flush=True)
    args.out.mkdir(exist_ok=True,parents=True)
    write_submission(args.out/"wins.csv",[p for p in puzzles if p.id in wins],wins)
    report=dict(parent_sha256=sha256(args.parent),settings={k:v for k,v in vars(args).items() if isinstance(v,int)},rows=rows)
    if args.engine:
        report["engine_sha256"]=sha256(args.engine)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(report,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-len(tape) for i,tape in wins.items()),flush=True)


if __name__=="__main__":
    main()
