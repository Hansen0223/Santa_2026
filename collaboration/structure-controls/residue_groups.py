"""Rebuild groups of targets from inferred arithmetic scales and a retained prefix."""
import argparse
from bisect import bisect_left
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
import gzip
import hashlib
import json
from pathlib import Path
from residue_bridges import ranked_scales, ingredient_bank, read_puzzles, read_submission, sha256, write_submission
from elf import check
from graph import active_graph, compile_graph, first_recipes
from generative.run_source import WORK, solve_stream
from solvers.gpu.gpu_join import cut_many
from solvers.gpu.gpu_schedule import schedule_like


def score_residue(t,h,small):
    rem=min(t%h,(-t)%h)
    j=bisect_left(small,rem)
    nearest=min(abs(v-rem) for v in small[max(0,j-1):j+1])
    return (1.+nearest)/h, min(rem,1_000_000)


def rebuild(p,old,binary):
    g=active_graph(p,first_recipes(p,old))
    core,_,build=ingredient_bank(p,g)
    ranked=ranked_scales(p.targets,g,p.seeds)
    modest=sorted({0,1,*[x for x in core if x<=131072]})
    choices=[]
    for rating,h in ranked:
        if rating<=0:
            break
        if h in core:
            continue
        construction=build(h)
        if construction:
            choices.append((h,construction))
            if len(choices)==4:
                break
    best=old
    observations=[]
    for h,make_h in choices[:2]:
        targets=sorted(p.targets,key=lambda t:(score_residue(t,h,modest),t))[:8]
        kept,free=cut_many(p,g,set(targets))
        available=set(free)|set(p.seeds)
        anchors=Counter(x for v,(_,a,b) in g.items() if v not in kept for x in {a,b} if x in available)
        # The subproblem starts from surviving arithmetic values. The final program pays for every used one.
        anchors=list(dict.fromkeys([*p.seeds,*sorted(anchors,key=lambda x:(-anchors[x],x))[:22]]))
        for helper in (False,True):
            roots=[*anchors,*([h] if helper else [])]
            inner=replace(p,seeds=tuple(roots),targets=tuple(targets))
            fresh=solve_stream(binary,('3','.18','40','32','8','5','0'),[inner],None,'original',0)[p.id]
            fragment=first_recipes(inner,fresh)
            candidates=[]
            restore=make_h if helper else {}
            for proposal in ((g|restore|fragment)|kept, (g|fragment)|restore|kept):
                try:
                    viable=active_graph(p,proposal)
                except (ValueError,KeyError):
                    continue
                candidates.append(len(viable))
                if len(viable)<len(best):
                    tape=compile_graph(p,viable,attempts=6)
                    if tape is None:
                        tape=schedule_like(p,old,viable)
                    if tape is not None and len(tape)<len(best):
                        check(p,tape)
                        best=tape
            observations.append(dict(scale=h,helper=helper,goals=targets,retained=len(kept),fresh=len(fresh),graph=min(candidates,default=None)))
    return p.id,best,dict(before=len(old),after=len(best),trials=observations)


def apply(task):
    return rebuild(*task)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for opt in ('puzzles','parent','binary','out'):
        ap.add_argument('--'+opt,required=True,type=Path)
    ap.add_argument('--count',type=int,default=32)
    ap.add_argument('--jobs',type=int,default=5)
    args=ap.parse_args()
    WORK.mkdir(exist_ok=True,parents=True)
    ps=read_puzzles(args.puzzles)
    bank=read_submission(args.parent)
    cohort=sorted((p for p in ps if 28<=len(p.targets)<=32 and max(p.seeds)<=35),
                  key=lambda p:hashlib.sha256(('residue1-'+p.id).encode()).digest())[:args.count]
    args.out.mkdir(exist_ok=True,parents=True)
    wins,rows={},{}
    with ProcessPoolExecutor(args.jobs) as pool:
        for i,t,row in pool.map(apply,[(p,bank[p.id],args.binary) for p in cohort]):
            rows[i]=row
            if len(t)<len(bank[i]):
                wins[i]=t
    write_submission(args.out/'wins.csv',[p for p in ps if p.id in wins],wins)
    record=dict(parent_sha256=sha256(args.parent),binary_sha256=sha256(args.binary),rows=rows)
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(record,separators=(',',':')).encode(),mtime=0))
    print(len(rows),len(wins),sum(len(bank[i])-len(t) for i,t in wins.items()))


if __name__=='__main__':
    main()
