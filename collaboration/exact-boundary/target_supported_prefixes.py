"""Rank physical starting sequences by near-term access to the official targets."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
from functools import cache
import gzip
import hashlib
from itertools import combinations
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT),str(ROOT/"collaboration/register-search")]
from elf import check,read_puzzles,read_submission,replay,sha256,write_submission
from solvers.graphs.corpus_prefix import arithmetic_edges
from tiny import encode
from two_sided_chains import reverse_steps


def prefixes(puzzle, original, breadth, cutoff):
    seeds = frozenset(puzzle.seeds)
    wanted = frozenset(puzzle.targets)
    ancestral = {step.output for step in replay(puzzle,original)}

    @cache
    def complement(operand):
        return {target: frozenset(x for x,_ in reverse_steps(target,operand,puzzle.limit))
                for target in wanted if target != operand}

    def add_frontier(value,available):
        return {v for other in available | {value}
                for v,_ in arithmetic_edges(value,other,puzzle.limit)}

    def merit(known, frontier):
        now = len(wanted & known)
        one = len(wanted & (frontier-known))
        two = 0
        witnesses = 0
        for target in wanted - frontier - known:
            count = sum(bool(complement(v).get(target,frozenset()) & frontier) for v in known)
            two += count>0
            witnesses += min(count,3)
        novelty = len(known - ancestral - seeds)
        return now,one,two,witnesses,novelty

    initial = frozenset(v for seed in seeds for v in add_frontier(seed,seeds))
    beam = [((),seeds,initial)]
    recorded = {}
    for depth in range(1,cutoff+1):
        next_beam = {}
        for sequence,known,frontier in beam:
            supported = Counter()
            for v in known:
                for target, partners in complement(v).items():
                    if target not in known:
                        supported.update(partners & frontier)
            order = sorted(frontier-known,key=lambda v: (v not in wanted,-supported[v],v.bit_length(),v))
            for value in order[:30]:
                together = known | {value}
                if together in next_beam:
                    continue
                answers = frontier | add_frontier(value,known)
                score = merit(together,answers)
                candidate = (*sequence,value)
                next_beam[together] = (score,candidate,together,answers)
        if not next_beam:
            break
        # Alternate priorities: targets closest to completion and broad two-step coverage.
        def key(row,first):
            (now,one,two,witnesses,novel),sequence,*_ = row
            stable = hashlib.sha256(repr(sequence).encode()).digest()
            primary = (8*now+5*one+two) if first else (6*now+3*one+3*two)
            return -primary,-witnesses,-novel,stable
        left = sorted(next_beam.values(),key=lambda row:key(row,True))[:breadth//2]
        right = sorted(next_beam.values(),key=lambda row:key(row,False))[:breadth]
        ranking = list({row[2]:row for row in (*left,*right)}.values())[:breadth]
        beam = [row[1:] for row in ranking]
        if depth in (4,6,8):
            for score,sequence,_,_ in ranking[:8]:
                recorded[sequence]=score
    return recorded


def run(task):
    p,parent,seq,score,engine,width,variant,seed = task
    known=(*p.seeds,*seq)
    hint=tuple(step.output for step in replay(p,parent))
    goal=len(parent)-1
    spec=(p.limit,len(p.seeds),len(known),len(p.targets),len(hint),width,variant,goal,seed,*known,*p.targets,*hint)
    proc=subprocess.run([str(engine)],input=" ".join(map(str,spec))+"\n",text=True,capture_output=True,check=True)
    status,n,edges,duplicates,recipes,*witness=map(int,proc.stdout.split())
    tape=None
    if status:
        if tuple(witness[:len(known)])!=known:
            raise ValueError("Solver returned a different prefix")
        tape=encode(p,tuple(witness[len(p.seeds):]))
        if check(p,tape)>goal:
            raise ValueError("Returned witness exceeds its requested length")
    return p.id,tape,dict(prefix=seq,rank=score,variant=variant,seed=seed,nodes=n,edges=edges,
                           duplicate_states=duplicates,reverse_recipes=recipes,saved=len(parent)-len(tape) if tape else 0)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for arg in ("puzzles","parent","bounds","engine","out"):
        ap.add_argument("--"+arg,type=Path,required=True)
    for key,default in (("count",12),("breadth",16),("width",360),("jobs",8)):
        ap.add_argument("--"+key,type=int,default=default)
    args=ap.parse_args()
    ps=read_puzzles(args.puzzles)
    bank=read_submission(args.parent)
    with args.bounds.open(encoding="utf-8",newline="") as f:
        lower={r["id"]:int(r["certified_lower"]) for r in csv.DictReader(f)}
    selected=sorted((p for p in ps if lower[p.id]<len(bank[p.id])<=34 and len(p.seeds)<=5 and p.limit<=1_250_000),
                    key=lambda p:(p.limit,p.id))[:args.count]
    tasks=[]
    for p in selected:
        offers=prefixes(p,bank[p.id],args.breadth,8)
        print(p.id,len(offers),flush=True)
        for j,(seq,score) in enumerate(offers.items()):
            tasks.append((p,bank[p.id],seq,score,args.engine,args.width,7 if j%2 else 10,980179+int(p.id[-4:])*31+j))
    rows={p.id:[] for p in selected}
    wins={}
    with ThreadPoolExecutor(args.jobs) as pool:
        for pid,tape,row in pool.map(run,tasks):
            rows[pid].append(row)
            if tape is not None and len(tape)<len(wins.get(pid,bank[pid])):
                wins[pid]=tape
                print(pid,len(bank[pid]),len(tape),flush=True)
    args.out.mkdir(parents=True,exist_ok=True)
    write_submission(args.out/"wins.csv",[p for p in ps if p.id in wins],wins)
    report=dict(parent_sha256=sha256(args.parent),bounds_sha256=sha256(args.bounds),engine_sha256=sha256(args.engine),
                width=args.width,breadth=args.breadth,rows=rows)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(report,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(tasks),len(wins),sum(len(bank[i])-len(t) for i,t in wins.items()),flush=True)


if __name__=="__main__":
    main()
