"""Construct complete programs from initial values, with optional target bands."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import gzip
import hashlib
import json
from math import gcd
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/"collaboration/register-search")]
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, compile_graph, first_recipes
from interior_bands import solve
from solvers.graphs.crossover_graft import optimize


PROFILES = ((2, 10, 8, 4, 54, 0), (3, 14, 10, 4, 64, 1), (3, 14, 10, 4, 64, 3))


def calculate(puzzle, engine, profile, timeout):
    fields = (puzzle.id, puzzle.limit, len(puzzle.seeds), len(puzzle.targets), -1,
              *puzzle.seeds, *puzzle.targets)
    wire = " ".join(map(str, fields)) + "\n"
    try:
        result = subprocess.run([str(engine), *map(str, profile)], input=wire, capture_output=True,
                                text=True, timeout=timeout, check=True,
                                creationflags=getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0))
    except subprocess.TimeoutExpired:
        return None, {"status": "timeout"}
    except subprocess.CalledProcessError as error:
        return None, {"status": "engine-error", "exit_code": error.returncode}
    header, *lines = result.stdout.splitlines()
    key, length, groups = header.split()
    program = []
    for line in lines:
        op, a, b, destination = line.split()
        program.append((op, int(a), int(b), int(destination)))
    program = tuple(program)
    if key != puzzle.id or check(puzzle, program) != int(length):
        raise ValueError(f"Constructor returned an invalid program for {puzzle.id}")
    return program, {"steps": len(program), "groups": int(groups)}


def affinity(a, b):
    return (abs(a-b).bit_length() - .65*gcd(a,b).bit_length(), b)


def anchor_menu(puzzle, graph, goals, width):
    seeds = tuple(dict.fromkeys(puzzle.seeds))
    consumers = Counter(u for _, a, b in graph.values() for u in {a, b})
    extras = graph.keys() - set(seeds) - set(goals)
    closest = sorted(extras, key=lambda v:(min(affinity(t,v)[0] for t in goals), -consumers[v], v))
    smaller = sorted(extras, key=lambda v:(v.bit_length(), -consumers[v], v))
    # Keep seeds and room for two populations of reusable values that serve different purposes.
    room = max(0, width-len(seeds))
    short = smaller[:room//2]
    near = [v for v in closest if v not in short][:room-len(short)]
    return seeds+tuple(short+near)


def stitched(puzzle, engine, width, band, largest_first, timeout):
    graph = {}
    open_targets = set(puzzle.targets)-set(puzzle.seeds)
    snapshots = []
    while open_targets:
        if largest_first is None:
            pivot = min(open_targets, key=lambda x: (
                sum(sorted(affinity(x,t)[0] for t in open_targets-{x})[:band-1]), x))
        else:
            pivot = max(open_targets) if largest_first else min(open_targets)
        group = (pivot,*sorted(open_targets-{pivot},key=lambda t:affinity(pivot,t))[:band-1])
        seeds = anchor_menu(puzzle,graph,group,width)
        local = replace(puzzle,seeds=seeds,targets=group)
        profile = PROFILES[2] if largest_first else PROFILES[1]
        tape,result = calculate(local,engine,profile,timeout)
        snapshots.append(dict(goals=group,seeds=seeds,**result))
        if tape is None:
            return None, snapshots
        for value, recipe in first_recipes(local,tape).items():
            if value not in puzzle.seeds:
                graph.setdefault(value, recipe)
        open_targets -= graph.keys()
    program = compile_graph(puzzle,graph,attempts=4,recompute=True,schedule_width=10)
    return program, snapshots


def work(task):
    puzzle, old, engine, polish, band, width, timeout, rounds, graft = task
    best = old
    direct, ordered = [], []
    alternatives = set()
    for profile in PROFILES:
        candidate, report = calculate(puzzle,engine,profile,timeout)
        direct.append(report)
        if candidate is not None:
            alternatives.add(candidate)
            best = min((best,candidate),key=len)
    for direction in ((False, True, None) if graft else (False, True)):
        candidate, pieces = stitched(puzzle,engine,width,band,direction,timeout)
        if candidate is not None:
            alternatives.add(candidate)
            best = min((best,candidate),key=len)
        ordered.append(dict(largest_first=direction,parts=pieces,physical=len(candidate) if candidate is not None else None))
    result = dict(before=len(old),direct=direct,stitched=ordered)
    if graft and alternatives:
        grafted = optimize(puzzle, old, tuple(sorted(alternatives)), 2, 30, 6)
        result["grafted"] = len(grafted)
        best = min((best,grafted),key=len)
    if polish:
        parent_graph = active_graph(puzzle,first_recipes(puzzle,old))
        distinct = []
        for candidate in alternatives:
            if len(candidate)>len(old)*1.10:
                continue
            change = len(first_recipes(puzzle,candidate).keys()^parent_graph.keys())
            if change>=3:
                distinct.append((len(candidate),-change,candidate))
        if distinct:
            salt = 500873 + int(puzzle.id[-4:])
            reference = solve(polish,puzzle,[old],salt,rounds)
            best = min((best,reference),key=len)
            result["control"] = len(reference)
            result["refined"] = []
            for _,change,candidate in sorted(distinct)[:2]:
                refined = solve(polish,puzzle,[candidate,old],salt,rounds)
                best = min((best,refined),key=len)
                result["refined"].append([len(candidate),len(refined),-change])
    result["after"] = check(puzzle,best)
    return puzzle.id,best,result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("puzzles","parent","reference","engine","source","out"):
        parser.add_argument("--"+name,type=Path,required=True)
    parser.add_argument("--polish",type=Path)
    parser.add_argument("--graft",action="store_true")
    parser.add_argument("--ranking",choices=("gap","balanced"),default="gap")
    for name,default in (("count",30),("band",9),("width",24),("jobs",8),("timeout",10),("rounds",360)):
        parser.add_argument("--"+name,type=int,default=default)
    args = parser.parse_args()
    if not 2 <= args.band <= 63 or not 3 <= args.width <= 48:
        parser.error("Unsupported band or register width")
    puzzles = read_puzzles(args.puzzles)
    parent = read_submission(args.parent)
    baseline = read_submission(args.reference)
    def ordering(p):
        gap=len(parent[p.id])-len(baseline[p.id])
        salt=hashlib.sha256(("cold-groups-239-"+p.id).encode()).digest()
        return -gap if args.ranking=="gap" else 0,salt
    eligible=sorted((p for p in puzzles if 48<=len(parent[p.id])<=230 and 12<=len(set(p.targets))<=63
                     and p.registers==48 and len(set(p.seeds))<=args.width),key=ordering)
    cohort=eligible[:args.count]
    tasks=[(p,parent[p.id],args.engine,args.polish,args.band,args.width,args.timeout,args.rounds,args.graft) for p in cohort]
    wins,rows={},{}
    with ThreadPoolExecutor(args.jobs) as executor:
        for i,tape,row in executor.map(work,tasks):
            rows[i]=row
            if len(tape)<len(parent[i]):
                wins[i]=tape
                print(i,len(parent[i]),len(tape),flush=True)
    args.out.mkdir(exist_ok=True,parents=True)
    write_submission(args.out/"wins.csv",[p for p in puzzles if p.id in wins],wins)
    record=dict(parent_sha256=sha256(args.parent),reference_sha256=sha256(args.reference),
                engine_sha256=sha256(args.engine),source=json.loads(args.source.read_bytes()),
                settings={k:v for k,v in vars(args).items() if isinstance(v,(int,str))},
                profiles=PROFILES,rows=rows)
    if args.polish:
        record["polish_sha256"]=sha256(args.polish)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(record,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-len(t) for i,t in wins.items()),flush=True)


if __name__=="__main__":
    main()
