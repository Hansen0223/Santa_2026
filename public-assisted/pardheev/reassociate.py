"""Reassociate signed sums and exact quotients and share the resulting intermediate values."""
import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import sys

from combine import BASE, ROOT, baseline, donor
from elf import read_puzzles, write_submission
from graph import active_graph, first_recipes

sys.path.insert(0,str(ROOT/'collaboration/cross-puzzle-templates'))
from selector import compile_selection


def evaluate(a,b,group,limit):
    x,s=a; y,t=b
    if s==t:
        h=x+y if group=='sum' else x*y
        edge=('+' if group=='sum' else '*',min(x,y),max(x,y))
        sign=s
    else:
        if x==y:return None
        if y>x:x,y,s,t=y,x,t,s
        if group=='sum':
            h=x-y;edge=('-',x,y)
        else:
            h,rem=divmod(x,y)
            if rem:return None
            edge=('/',x,y)
        sign=s
    if h<=0 or h>limit or h in (x,y):return None
    return (h,sign),edge


def signed(edge):
    op,a,b=edge
    return ((a,1),(b,-1 if op in '-/' else 1))


def enumerate_rewrites(p,graph):
    for v,(op,x,y) in graph.items():
        family='sum' if op in '+-' else 'product'
        for j,w in enumerate((x,y)):
            if w not in graph:continue
            branch=graph[w]
            if (branch[0] in '+-')!=(family=='sum'):continue
            outer=signed((op,x,y)); factor=outer[j][1]
            leaves=[(a,s*factor) for a,s in signed(branch)]+[outer[1-j]]
            for k in (0,1):
                q=evaluate(leaves[k],leaves[2],family,p.limit)
                if q is None:continue
                h,first=q
                end=evaluate(h,leaves[1-k],family,p.limit)
                if end is None or end[0]!=(v,1) or v==h[0] or v in first[1:]:continue
                yield h[0],first,v,end[1]
        if op in '+-' and x in graph and y in graph and graph[x][0]==graph[y][0]=='*':
            left=graph[x][1:];right=graph[y][1:]
            for k in set(left)&set(right):
                a=x//k; b=y//k
                q=evaluate((a,1),(b,1 if op=='+' else -1),'sum',p.limit)
                if q and q[0][1]==1 and q[0][0]*k==v and q[0][0]!=v:
                    yield q[0][0],q[1],v,('*',min(k,q[0][0]),max(k,q[0][0]))


def solve(job):
    p,base,other=job
    graph=active_graph(p,first_recipes(p,base));alt=active_graph(p,first_recipes(p,other))
    core=set(graph)|set(p.seeds);pool=defaultdict(set)
    for source in (graph,alt):
        for h,first,v,last in enumerate_rewrites(p,source):
            if v in graph and set(first[1:])<=core and all(u==h or u in core for u in last[1:]):
                pool[h].add((first,v,last))
    candidates=[]
    for h,offers in pool.items():
        dest={v for _,v,_ in offers}
        if h in core or len(dest)>=2:
            candidates.append((h,offers))
    candidates.sort(key=lambda z:(z[0] not in core,-len({v for _,v,_ in z[1]}),z[0]))
    paths=[]
    for h,offers in candidates[:110]:
        for first,v,last in offers:
            if h not in p.seeds:paths.append({h:first})
            paths.append({v:last})
    rec,winner=compile_selection(p,base,graph,paths,False)
    rec.update(id=p.id,before=len(base),after=len(winner),retained=len(candidates),fresh_shared=sum(h not in core for h,_ in candidates))
    return rec,winner if len(winner)<len(base) else None


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('puzzles','archive','out'):ap.add_argument('--'+key,type=Path,required=True)
    ap.add_argument('--count',type=int,default=60);ap.add_argument('--offset',type=int,default=0);ap.add_argument('--jobs',type=int,default=6)
    a=ap.parse_args();a.out.mkdir(exist_ok=True,parents=True)
    ps={p.id:p for p in read_puzzles(a.puzzles)};local=baseline('public-assisted/submission.csv');ext=donor(a.archive)
    ordered=sorted((i for i in ps if ext[i]!=local[i] and min(len(ext[i]),len(local[i]))>=55),key=lambda i:hashlib.sha256(('paired-reassociation'+i).encode()).digest())
    if a.offset<0 or a.offset>=len(ordered) or a.count<1:ap.error('invalid range')
    ids=ordered[a.offset:a.offset+a.count]
    jobs=[(ps[i],*sorted((local[i],ext[i]),key=len)) for i in ids]
    with ProcessPoolExecutor(a.jobs) as pool:results=list(pool.map(solve,jobs))
    rows=[r for r,_ in results];wins={r['id']:t for r,t in results if t is not None}
    write_submission(a.out/'algebra-wins.csv',[ps[i] for i in sorted(wins)],wins)
    report=dict(base=BASE,eligible=len(ordered),ids=ids,wins=len(wins),saved=sum(r['before']-r['after'] for r in rows),rows=rows)
    (a.out/'algebra-results.json.gz').write_bytes(gzip.compress(json.dumps(report,separators=(',',':')).encode(),mtime=0))
    print(report['wins'],report['saved'],flush=True)


if __name__=='__main__':
    main()