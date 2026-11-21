"""Borrow dormant prefix values in unused suffix input slots, then rebuild from official starts."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import gzip
import hashlib
import json
from pathlib import Path

from suffix_search import active_graph, check, compile_graph, first_recipes, read_puzzles, read_submission, remap, schedule_like, sha256, solve, write_submission


def input_slots(tail):
    needed, written = set(), set()
    for _, a, b, dst in tail:
        needed.update({a,b}-written)
        written.add(dst)
    return needed


def resurrect(p, original, cut, binary, seed, rounds):
    from elf import replay
    prefix, suffix = original[:cut], original[cut:]
    registers = [0] * p.registers
    registers[:len(p.seeds)] = p.seeds
    prologue = replace(p, targets=())
    trace = replay(prologue, prefix)
    for (_,_,_,dst), step in zip(prefix, trace):
        registers[dst] = step.output
    roots = set(p.seeds) | {step.output for step in trace}
    remaining = set(p.targets) - roots
    required = sorted(input_slots(suffix))
    slots = required + sorted(set(range(p.registers))-set(required))
    live = [registers[i] for i in required]
    if len(remaining)<2 or len(live)>=p.registers:
        return original, {}
    tail_values = {step.output for step in replay(p, original)[cut:]}
    anchors = set(live) | set(p.seeds)
    score = Counter()
    for v in roots-set(live):
        for a in anchors:
            candidates = (v+a, abs(v-a), v*a, v//a if v%a==0 else 0, a//v if a%v==0 else 0)
            score[v] += sum(1 for t in candidates if t!=v and t!=a and t in tail_values)
    helpers = sorted(score, key=lambda v:(-score[v], v in registers, v))[:p.registers-len(live)]
    if not helpers:
        return original, {}
    inner = replace(p, seeds=tuple(live+helpers), targets=tuple(sorted(remaining)))
    guide = remap(suffix,{j:i for i,j in enumerate(slots)})
    improved = solve(binary,inner,[guide],seed,rounds)
    head = first_recipes(prologue,prefix)
    tail = first_recipes(inner,improved)
    best = original
    for definitions in (head|tail,tail|head):
        try:
            graph = active_graph(p, definitions)
        except (ValueError,KeyError):
            continue
        if len(graph)>=len(best):
            continue
        for tape in (compile_graph(p,graph,attempts=6),schedule_like(p,original,graph)):
            if tape is not None and len(tape)<len(best):
                check(p,tape)
                best=tape
    return best, dict(cut=cut, live=len(live), helpers=len(helpers), dormant=sum(v not in registers for v in helpers),
                      tail=len(improved), new=len(best))


def one(task):
    p,t,binary,rounds = task
    seed = 721337+int(p.id[-4:])
    direct = solve(binary,p,[t],seed,rounds)
    best = min((t,direct), key=len)
    arms=[]
    for cut in (len(t)//3,2*len(t)//3):
        candidate,row = resurrect(p,t,cut,binary,seed,rounds)
        arms.append(row)
        if len(candidate)<len(best):
            best=candidate
    return p.id,best,dict(before=len(t),control=len(direct),arms=arms)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('puzzles','parent','binary','out'):
        ap.add_argument('--'+name,required=True,type=Path)
    ap.add_argument('--reference',type=Path,help='Search parent-specific advantages first')
    ap.add_argument('--count',type=int,default=50)
    ap.add_argument('--jobs',type=int,default=6)
    ap.add_argument('--rounds',type=int,default=460)
    args=ap.parse_args()
    ps=read_puzzles(args.puzzles)
    parent=read_submission(args.parent)
    ref=read_submission(args.reference) if args.reference else parent
    eligible=sorted((p for p in ps if len(parent[p.id])>=50),key=lambda p:
        (min(0,len(parent[p.id])-len(ref[p.id])),hashlib.sha256(('revive1'+p.id).encode()).digest()))[:args.count]
    rows,wins={},{}
    args.out.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(args.jobs) as pool:
        for i,t,record in pool.map(one,[(p,parent[p.id],args.binary,args.rounds) for p in eligible]):
            rows[i]=record
            if len(t)<len(parent[i]):
                wins[i]=t
    write_submission(args.out/'wins.csv',[p for p in ps if p.id in wins],wins)
    packet=dict(parent_sha256=sha256(args.parent),reference_sha256=sha256(args.reference) if args.reference else None,
                binary_sha256=sha256(args.binary),rounds=args.rounds,rows=rows)
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(packet,separators=(',',':')).encode(),mtime=0))
    print(len(rows),len(wins),sum(len(parent[i])-len(t) for i,t in wins.items()),flush=True)


if __name__=='__main__':
    main()
