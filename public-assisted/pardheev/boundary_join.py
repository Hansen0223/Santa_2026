"""Join the early operations of one parent to another parent's live boundary through new arithmetic."""
import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
import gzip
import hashlib
import json
from pathlib import Path
import sys

from combine import BASE, ROOT, baseline, donor
from elf import read_puzzles, write_submission, check
from graph import active_graph, compile_graph, first_recipes
from solvers.graphs.corpus_prefix import arithmetic_edges
from solvers.gpu.gpu_schedule import schedule_like

sys.path.insert(0,str(ROOT/'collaboration/cross-puzzle-templates'))
from selector import compile_selection


def formulas(t, a, limit):
    if t > a: yield t-a, ('+', a, t-a)
    if t+a <= limit: yield t+a, ('-', t+a, a)
    if a > t: yield a-t, ('-', a, a-t)
    if t % a == 0: yield t//a, ('*', t//a, a)
    if t*a <= limit: yield t*a, ('/', t*a, a)
    if a % t == 0: yield a//t, ('/', a, a//t)


def bridges(p, boundary, other):
    support={s:0 for s in p.seeds}
    for k,(v,(_,a,b)) in enumerate(other.items()):
        support[v]=support[a]|support[b]|(1<<k)
    # Cheap values in the alternate prefix stay affordable even after pruning it.
    choices=sorted(support,key=lambda x:(support[x].bit_count(),x))[:48]
    cost={};maker={};required=defaultdict(dict);direct=[]
    for j,a in enumerate(choices):
        for b in choices[:j+1]:
            price=(support[a]|support[b]).bit_count()+1
            for h,r in arithmetic_edges(a,b,p.limit):
                if h in p.seeds or h in (a,b):continue
                if h not in cost or price<cost[h]:cost[h]=price;maker[h]=r
    for t in boundary:
        for a in choices:
            for h,r in formulas(t,a,p.limit):
                if t in r[1:] or not 1<=h<=p.limit:continue
                if h in support:
                    direct.append({t:r})
                elif h in maker and h not in boundary:
                    price=1+cost[h]+support[a].bit_count()
                    old=required[h].get(t)
                    if old is None or price<old[0]:required[h][t]=price,r
    def key(h):
        return (-len(required[h]),min(v[0] for v in required[h].values()),cost[h],h)
    selected=sorted(required,key=key)[:28]
    paths=[other,*direct]
    for h in selected:
        paths.append({h:maker[h]})
        paths.extend({t:r} for t,(_,r) in required[h].items())
    return paths, len(direct), len(selected)


def solve(job):
    p,a,b=job;best=a;row=dict(id=p.id,before=len(a),arms=[])
    agraph=first_recipes(p,a);live=active_graph(p,agraph)
    ordered={v:r for v,r in agraph.items() if v in live}
    bgraph=first_recipes(p,b)
    for fraction in (.34,.60):
        cut=int(fraction*len(ordered))
        head=dict(list(ordered.items())[:cut])
        tail=dict(list(ordered.items())[cut:])
        boundary=(set(p.targets)&head.keys())|{u for _,x,y in tail.values() for u in (x,y) if u in head}
        if not boundary:continue
        inner=replace(p,targets=tuple(sorted(boundary)))
        original=active_graph(inner,head)
        initial=compile_graph(inner,original,recompute=True,schedule_width=3)
        if initial is None:continue
        limit=int(len(bgraph)*(fraction+.10))
        other=dict(list(bgraph.items())[:limit])
        paths,straight,hidden=bridges(p,boundary,other)
        rec,tape=compile_selection(inner,initial,original,paths,False)
        rec.update(fraction=fraction,boundary=len(boundary),prefix_before=len(initial),
                   alternate_prefix=len(other),direct_bridges=straight,hidden_bridges=hidden)
        if len(tape)<len(initial):
            joined=first_recipes(inner,tape)|tail
            options=[schedule_like(p,a,joined),compile_graph(p,joined,recompute=True,schedule_width=5)]
            for t in options:
                if t is not None and len(t)<len(best):
                    check(p,t);best=t
        row['arms'].append(rec)
    row['after']=len(best)
    return row,best if len(best)<len(a) else None


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('puzzles','archive','out','selection'):ap.add_argument('--'+k,type=Path,required=True)
    ap.add_argument('--jobs',type=int,default=4);ap.add_argument('--count',type=int,default=24)
    a=ap.parse_args();a.out.mkdir(exist_ok=True,parents=True)
    ps={p.id:p for p in read_puzzles(a.puzzles)}
    loc=baseline('public-assisted/submission.csv');ext=donor(a.archive)
    ids=json.loads(a.selection.read_bytes())['ids']
    ids=sorted(ids,key=lambda i:hashlib.sha256(('two-prefix-1'+i).encode()).digest())[:a.count]
    jobs=[(ps[i],*sorted((ext[i],loc[i]),key=len)) for i in ids]
    with ProcessPoolExecutor(a.jobs) as pool:results=list(pool.map(solve,jobs))
    rows=[r for r,_ in results];win={r['id']:t for r,t in results if t is not None}
    write_submission(a.out/'bridge-wins.csv',[ps[i] for i in sorted(win)],win)
    summary=dict(base=BASE,ids=ids,rows=rows,wins=len(win),saved=sum(r['before']-r['after'] for r in rows))
    (a.out/'bridge-results.json.gz').write_bytes(gzip.compress(json.dumps(summary,separators=(',',':')).encode(),mtime=0))
    print(summary['wins'],summary['saved'],flush=True)


if __name__=='__main__':
    main()