"""Search under a tighter register budget, then restore the official capacity."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import gzip
import hashlib
import json
from pathlib import Path

from interior_bands import solve
from relaxed_registers import pressure
from elf import check,read_puzzles,read_submission,sha256,write_submission
from graph import active_graph,compile_graph,first_recipes


def work(job):
    puzzle, parent, engine, rounds, deltas, extra_steps = job
    previous = first_recipes(puzzle,parent)
    active = active_graph(puzzle,previous)
    graph = {v:e for v,e in previous.items() if v in active}
    peak = min(puzzle.registers,pressure(puzzle,graph))
    capacity = sorted({max(len(puzzle.seeds),peak-d) for d in deltas},reverse=True)
    capacity = [size for size in capacity if size<peak and size>=3]
    attempts = []
    for size in capacity:
        reduced = replace(puzzle,registers=size)
        start = compile_graph(reduced,graph,attempts=5,recompute=True,schedule_width=5)
        attempts.append((reduced,start))
    best = parent
    result = dict(before=len(parent),peak=peak,arms=[])
    candidates = [(p,t) for p,t in attempts if t is not None and len(t)<=len(parent)+extra_steps]
    if candidates:
        seed = 280801 + int(puzzle.id[-4:])
        direct = solve(engine,puzzle,[parent],seed,rounds)
        control = solve(engine,puzzle,[direct,parent],seed+1619,rounds)
        best = min((best,direct,control),key=len)
        result["control"] = len(control)
        result["first_control"] = len(direct)
        for reduced,start in candidates:
            compact = solve(engine,reduced,[start],seed,rounds)
            check(puzzle,compact)
            restored = solve(engine,puzzle,[compact,parent],seed+1619,rounds)
            difference = len(active.keys() ^ first_recipes(puzzle,compact).keys())
            best = min((best,start,compact,restored),key=len)
            result["arms"].append(dict(registers=reduced.registers,start=len(start),reduced=len(compact),
                                       restored=len(restored),value_distance=difference))
    result["rejected"] = {str(p.registers):None if t is None else len(t)
                          for p,t in attempts if t is None or len(t)>len(parent)+extra_steps}
    result["after"] = check(puzzle,best)
    return puzzle.id,best,result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("puzzles","parent","out","engine"):
        parser.add_argument("--"+name,type=Path,required=True)
    for name,default in (("count",100),("offset",0),("jobs",10),("rounds",420),("extra-steps",8)):
        parser.add_argument("--"+name,type=int,default=default)
    parser.add_argument("--delta",nargs="+",type=int,default=[3,6])
    args = parser.parse_args()
    if any(d<1 for d in args.delta):
        parser.error("The reduction in capacity must be positive.")
    ps = read_puzzles(args.puzzles)
    bank = read_submission(args.parent)
    eligible = sorted((p for p in ps if len(bank[p.id])>=50),
                      key=lambda p:hashlib.sha256(("tight-scratch-"+p.id).encode()).digest())
    selected = eligible[args.offset:args.offset+args.count]
    tasks = [(p,bank[p.id],args.engine,args.rounds,args.delta,args.extra_steps) for p in selected]
    rows,wins = {},{}
    with ThreadPoolExecutor(args.jobs) as pool:
        for i,tape,row in pool.map(work,tasks):
            rows[i] = row
            if len(tape)<len(bank[i]):
                wins[i] = tape
                print(i,len(bank[i]),len(tape),flush=True)
    args.out.mkdir(exist_ok=True,parents=True)
    write_submission(args.out/"wins.csv",[p for p in ps if p.id in wins],wins)
    record = dict(parent_sha256=sha256(args.parent),engine_sha256=sha256(args.engine),
                  delta=args.delta,eligible=len(eligible),settings={k:v for k,v in vars(args).items() if isinstance(v,int)},rows=rows)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(record,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-len(t) for i,t in wins.items()))


if __name__=="__main__":
    main()
