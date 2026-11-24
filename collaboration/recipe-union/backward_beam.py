"""Backward beam search over shared, unfinished arithmetic values in several feasible orders."""
import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
import gzip
import hashlib
import heapq
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'collaboration/register-search'))
from elf import check,read_puzzles,read_submission,sha256,write_submission
from graph import first_recipes,recipes_from
from interior_bands import compile_on_parent


def extended_order(anchor,bank,seeds):
    """Insert a donor-only value as soon as any of its known definitions is available."""
    blocked=set(anchor)
    ready=set(seeds)
    missing=[]
    outputs=[]
    waiting=defaultdict(list)
    queue=[]
    for v,choices in bank.items():
        if v in blocked:
            continue
        for _,a,b in sorted(choices):
            need={a,b}-ready
            if not need:
                heapq.heappush(queue,v)
            else:
                j=len(missing)
                outputs.append(v)
                missing.append(len(need))
                for x in need:
                    waiting[x].append(j)
    order=[]
    def emit(x):
        if x in ready:
            return
        ready.add(x)
        order.append(x)
        for j in waiting.pop(x,()):
            missing[j]-=1
            if not missing[j]:
                heapq.heappush(queue,outputs[j])
    for v in [*anchor,None]:
        while queue:
            emit(heapq.heappop(queue))
        if v is not None:
            emit(v)
    return order


def model(order,bank,seeds):
    rank={v:j for j,v in enumerate(order)}
    ways=[]
    must=[]
    for j,v in enumerate(order):
        choices={}
        for edge in sorted(bank[v]):
            deps={x for x in edge[1:] if x not in seeds}
            if any(rank.get(x,j)>=j for x in deps):
                continue
            mask=sum(1<<rank[x] for x in deps)
            choices.setdefault(mask,edge)
        if not choices:
            raise ValueError('No definition in extended order')
        common=None
        for mask in choices:
            closure=0
            while mask:
                bit=mask & -mask
                closure|=must[bit.bit_length()-1]
                mask-=bit
            common=closure if common is None else common & closure
        must.append((1<<j)|common)
        ways.append(tuple(choices.items()))
    return rank,ways,must


def search(p,tape,order,rank,ways,must,width,bound):
    @lru_cache(maxsize=40000)
    def required(mask):
        if not mask:
            return 0
        bit=mask & -mask
        return must[bit.bit_length()-1] | required(mask-bit)
    goals=sum(1<<rank[t] for t in set(p.targets)-set(p.seeds))
    states={goals:(0,None)}
    peak=1
    for j in reversed(range(len(order))):
        bit=1<<j
        nxt={}
        for pending,(cost,trace) in states.items():
            if pending & bit:
                rest=pending-bit
                for deps,edge in ways[j]:
                    new=rest|deps
                    prior=nxt.get(new)
                    if prior is None or cost+1<prior[0]:
                        nxt[new]=(cost+1,(j,edge,trace))
            elif pending not in nxt or cost<nxt[pending][0]:
                nxt[pending]=(cost,trace)
        scores=[]
        for mask,(cost,_) in nxt.items():
            floor=cost+required(mask).bit_count()
            if floor<bound:
                scores.append((floor, cost+mask.bit_count(),mask))
        if not scores:
            return tape,dict(peak=peak,closed_at=j)
        peak=max(peak,len(scores))
        states={mask:nxt[mask] for _,_,mask in heapq.nsmallest(width,scores)}
    steps,trace=states[0]
    g={}
    while trace is not None:
        j,edge,trace=trace
        g[order[j]]=edge
    candidate=compile_on_parent(p,tape,g)
    return (candidate if candidate is not None and len(candidate)<len(tape) else tape),dict(peak=peak,graph=steps)


def work(job):
    p,parent,donors,width,orders=job
    seeds=set(p.seeds)
    bank=defaultdict(set)
    graphs=[]
    for t in dict.fromkeys([parent,*donors]):
        graph=first_recipes(p,t)
        graphs.append(graph)
        for v,recipes in recipes_from(p,t).items():
            bank[v].update(recipes)
    # Preserve incumbent order and add one structurally distinct donor order.
    anchors=[graphs[0]]
    anchors.extend(sorted(graphs[1:],key=lambda g:-len(g.keys()^graphs[0].keys()))[:orders-1])
    best=parent
    rows=[]
    seen=set()
    for g in anchors:
        order=extended_order(g,bank,seeds)
        key=tuple(order)
        if key in seen:
            continue
        seen.add(key)
        rank,ways,must=model(order,bank,seeds)
        sub=[]
        for w in dict.fromkeys([1,width]):
            tape,detail=search(p,parent,order,rank,ways,must,w,len(parent))
            sub.append(dict(width=w,physical=len(tape),**detail))
            if len(tape)<len(best):
                best=tape
        rows.append(sub)
    check(p,best)
    return p.id,best,dict(before=len(parent),after=len(best),donors=len(graphs)-1,
                          pool=len(bank),orders=rows)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('puzzles','parent','out'):
        ap.add_argument('--'+key,type=Path,required=True)
    ap.add_argument('--donors',nargs='+',type=Path,required=True)
    for k,n in [('jobs',6),('width',32),('orders',2),('count',1000),('offset',0)]:
        ap.add_argument('--'+k,type=int,default=n)
    a=ap.parse_args()
    ps=read_puzzles(a.puzzles)
    parent=read_submission(a.parent)
    banks=[read_submission(path) for path in a.donors]
    jobs=[]
    for p in sorted(ps,key=lambda p:hashlib.sha256(('pending-set1-'+p.id).encode()).digest()):
        t=parent[p.id]
        donors=list(dict.fromkeys(b[p.id] for b in banks if p.id in b and b[p.id]!=t))
        if len(t)>=18 and donors:
            jobs.append((p,t,donors,a.width,a.orders))
    rows,wins={},{}
    with ProcessPoolExecutor(a.jobs) as ex:
        for i,t,r in ex.map(work,jobs[a.offset:a.offset+a.count],chunksize=3):
            rows[i]=r
            if len(t)<len(parent[i]):
                wins[i]=t
    a.out.mkdir(parents=True,exist_ok=True)
    write_submission(a.out/'wins.csv',[p for p in ps if p.id in wins],wins)
    info=dict(eligible=len(jobs),parent_sha256=sha256(a.parent),donors={f.name:sha256(f) for f in a.donors},
              settings={k:v for k,v in vars(a).items() if isinstance(v,int)},rows=rows)
    (a.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(info,separators=(',',':')).encode(),mtime=0))
    print(len(rows),len(wins),sum(len(parent[i])-len(t) for i,t in wins.items()))


if __name__=='__main__':
    main()
