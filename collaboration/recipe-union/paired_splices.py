"""Exchange pairs of formulas whose donor subgraphs share a newly introduced intermediate."""
import argparse
import csv
import io
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from elf import check, read_puzzles, write_submission
from graph import active_graph, compile_graph, first_recipes
from generative.wang.replay_search import encode


def canonical(recipe):
    op, a, b = recipe
    if op in '+*':
        a, b = sorted((a, b))
    return op, a, b


def fragments(puzzle, base, guide):
    seeds = set(puzzle.seeds)
    for v in base.keys() & guide.keys():
        if canonical(base[v]) == canonical(guide[v]):
            continue
        fragment = {v: guide[v]}
        pending = list(guide[v][1:])
        while pending:
            node = pending.pop()
            if node in base or node in seeds or node in fragment:
                continue
            fragment[node] = guide[node]
            pending.extend(guide[node][1:])
        if len(fragment) <= 32:
            yield v, fragment


def alternative_starts(puzzle, primary, tapes):
    base = active_graph(puzzle, first_recipes(puzzle, primary))
    seen = set()
    variants = []
    counts = Counter()
    for tape in tapes:
        guide = active_graph(puzzle, first_recipes(puzzle, tape))
        parts = sorted(fragments(puzzle, base, guide))
        plans = []
        for i, (v, frag) in enumerate(parts):
            plans.append(('single', frag))
            for w, other in parts[:i]:
                if (frag.keys() & other.keys()) - {v, w}:
                    plans.append(('paired', {**frag, **other}))
        for mode, patch in plans:
            key = frozenset((n, canonical(rec)) for n, rec in patch.items())
            if key in seen:
                continue
            seen.add(key)
            counts[mode] += 1
            try:
                g = active_graph(puzzle, base | patch)
            except (KeyError, ValueError):
                continue
            if len(g) > len(primary) + 5:
                continue
            edits = frozenset((n,canonical(rec)) for n,rec in g.items()
                              if n not in base or canonical(rec) != canonical(base[n]))
            if edits:
                variants.append((len(g), mode, edits, g))
    variants.sort(key=lambda entry:(entry[0], -len(entry[2]), sorted(entry[2])))
    starts = []
    fingerprints = []
    modes = []
    for length, mode, edges, graph in variants:
        if fingerprints and length >= len(primary) and any(
                len(edges ^ before) < 3 for before in fingerprints):
            continue
        program = compile_graph(puzzle, graph, attempts=4)
        if program and program != primary and program not in starts:
            starts.append(program)
            modes.append(mode)
            fingerprints.append(edges)
            if len(starts) == 5:
                break
    return starts, modes, counts


def evolve(puzzle, binary, seed, rounds, parents):
    words = subprocess.run([str(binary)],input=encode(puzzle,'anneal',rounds,seed,parents),
                           text=True,capture_output=True,check=True).stdout.split()
    n = int(words[0])
    if len(words) != 1 + 4*n:
        raise ValueError(f'Truncated solver output on {puzzle.id}')
    tape = tuple((words[i],*map(int,words[i+1:i+4])) for i in range(1,len(words),4))
    if check(puzzle,tape) != n:
        raise ValueError(puzzle.id)
    return tape


def run(job):
    puzzle, base, guides, binary, rounds = job
    starts, kinds, counts = alternative_starts(puzzle, base, guides)
    seed = 716052 + int(puzzle.id[-4:])
    control = evolve(puzzle,binary,seed,rounds,[base,*guides[:5]])
    candidate = min([base,*starts,control],key=len)
    treatment = None
    if starts:
        first = min([base,*starts],key=len)
        parents = list(dict.fromkeys([first,base,*starts,*guides]))[:14]
        treatment = evolve(puzzle,binary,seed,rounds,parents)
        candidate = min((candidate,treatment),key=len)
    return puzzle.id,candidate,dict(parent=len(base),single_pairs=dict(counts),starts=list(zip(kinds,map(len,starts))),
                   control=len(control),treatment=len(treatment) if treatment is not None else None,after=len(candidate))


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--puzzles',type=Path,required=True)
    a.add_argument('--parent',type=Path,required=True)
    a.add_argument('--donors',type=Path,nargs='+',required=True)
    a.add_argument('--binary',type=Path,required=True)
    a.add_argument('--out',type=Path,required=True)
    a.add_argument('--count',type=int,default=64)
    a.add_argument('--offset',type=int,default=0)
    a.add_argument('--rounds',type=int,default=180)
    a.add_argument('--jobs',type=int,default=8)
    args=a.parse_args()
    puzzles=read_puzzles(args.puzzles)
    tables = []
    inputs = []
    for file in [args.parent, *args.donors]:
        raw = file.read_bytes()
        inputs.append(dict(name=file.name, sha256=hashlib.sha256(raw).hexdigest()))
        rows = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
        tables.append({r['id']: tuple(tuple(op) for op in json.loads(r['program'])) for r in rows})
    incumbent, *donors = tables
    jobs=[]
    for puzzle in puzzles:
        i=puzzle.id
        primary=incumbent[i]
        if not 35 <= len(primary) <= 300:
            continue
        guides=list(dict.fromkeys(d[i] for d in donors if i in d and d[i] != primary))
        base_edges={n:canonical(rec) for n,rec in first_recipes(puzzle,primary).items()}
        unique={}
        for t in guides:
            edges=frozenset((n,canonical(rec)) for n,rec in first_recipes(puzzle,t).items()
                            if n not in base_edges or base_edges[n]!=canonical(rec))
            if edges:
                unique.setdefault(edges,t)
        if not unique:
            continue
        # Rank puzzles by strong but structurally different alternatives.
        ranked=sorted(unique.items(),key=lambda x:(max(1,len(x[1])-len(primary)+2)/max(1,len(x[0]))**.5,len(x[1])))
        quality=max(1,len(ranked[0][1])-len(primary)+2)/len(ranked[0][0])**.5
        jobs.append((quality,puzzle.id,(puzzle,primary,[t for _,t in ranked[:5]],args.binary.resolve(),args.rounds)))
    selected=sorted(jobs,key=lambda x:x[:2])[args.offset:args.offset+args.count]
    wins={}
    rows={}
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        for i,t,data in pool.map(run,[j for _,_,j in selected]):
            rows[i]=data
            if len(t)<len(incumbent[i]):
                wins[i]=t
    args.out.mkdir(exist_ok=True,parents=True)
    write_submission(args.out/'wins.csv',[p for p in puzzles if p.id in wins],wins)
    summary=dict(inputs=inputs,offset=args.offset,rounds=args.rounds,rows=rows)
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(summary,separators=(',',':')).encode(),mtime=0))
    print('searched',len(rows),'shortened',len(wins),'saved',sum(len(incumbent[i])-len(t) for i,t in wins.items()))


if __name__=='__main__':
    main()
