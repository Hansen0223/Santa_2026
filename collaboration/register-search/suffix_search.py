"""Reoptimize the remaining targets from the actual register contents at a cut."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'collaboration/retained-pool'))
from neutral_lead import solve
from elf import arithmetic, check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, compile_graph, first_recipes
from solvers.gpu.gpu_schedule import schedule_like


def remap(tape, indexes):
    return tuple((op, indexes[a], indexes[b], indexes[d]) for op, a, b, d in tape)


def suffix_at(p, tape, cut):
    registers = [0] * p.registers
    registers[:len(p.seeds)] = p.seeds
    remaining = set(p.targets) - set(p.seeds)
    for op, left, right, dst in tape[:cut]:
        number = arithmetic(op, registers[left], registers[right])
        registers[dst] = number
        remaining.discard(number)
    slots = sorted(range(p.registers), key=lambda j: registers[j] == 0)
    inverse = {old: new for new, old in enumerate(slots)}
    starts = tuple(registers[j] for j in slots if registers[j])
    if len(remaining)<2:
        return None
    inner = replace(p, seeds=starts, targets=tuple(sorted(remaining)))
    return inner, remap(tape[cut:], inverse), slots


def assemble(p, program, prefix_length, suffix, slots):
    direct = program[:prefix_length] + remap(suffix, slots)
    check(p, direct)
    graph = first_recipes(p, direct)
    smaller = active_graph(p, graph)
    if len(smaller) >= len(direct):
        return direct
    candidates = [direct]
    for tape in (schedule_like(p, direct, smaller), compile_graph(p, smaller, attempts=4)):
        if tape is not None:
            candidates.append(tape)
    return min(candidates, key=len)


def work(task):
    p, original, binary, rounds, fractions = task
    seed = 337011 + int(p.id[-4:])
    best = original
    details = []
    control = solve(binary, p, [original], seed, rounds)
    if len(control)<len(best):
        best = control
    for percent in fractions:
        k = len(original)*percent//100
        cut = suffix_at(p, original, k)
        if cut is None:
            continue
        inner, tail, slots = cut
        improved = solve(binary, inner, [tail], seed, rounds)
        whole = assemble(p, original, k, improved, slots)
        if len(whole)<len(best):
            best = whole
        details.append(dict(cut=k, slots=len(inner.seeds), targets=len(inner.targets), tail=len(improved), total=len(whole)))
    return p.id, best, dict(before=len(original), control=len(control), suffix=details)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for field in ('puzzles', 'parent', 'binary', 'out'):
        ap.add_argument('--'+field, type=Path, required=True)
    ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--count',type=int, default=96)
    ap.add_argument('--offset',type=int, default=0)
    ap.add_argument('--rounds',type=int, default=500)
    ap.add_argument('--percent',nargs='+',type=int,default=[25,55])
    args = ap.parse_args()
    if any(not 0<n<100 for n in args.percent):
        ap.error('Each cut must lie strictly inside the program')
    ps = read_puzzles(args.puzzles)
    parent = read_submission(args.parent)
    selected = sorted((p for p in ps if len(parent[p.id])>=45),
                      key=lambda p:hashlib.sha256(('suffix1-'+p.id).encode()).digest())[args.offset:args.offset+args.count]
    args.out.mkdir(exist_ok=True,parents=True)
    rows, wins = {}, {}
    with ThreadPoolExecutor(args.jobs) as pool:
        for i, tape, row in pool.map(work, [(p,parent[p.id],args.binary,args.rounds,args.percent) for p in selected]):
            rows[i] = row
            if len(tape)<len(parent[i]):
                wins[i] = tape
    write_submission(args.out/'wins.csv', [p for p in ps if p.id in wins], wins)
    record = dict(parent_sha256=sha256(args.parent), binary_sha256=sha256(args.binary),
                  offset=args.offset, percent=args.percent, rounds=args.rounds, rows=rows)
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(record,separators=(',',':')).encode(),mtime=0))
    print(len(rows), len(wins), sum(len(parent[i])-len(tape) for i,tape in wins.items()), flush=True)


if __name__ == '__main__':
    main()
