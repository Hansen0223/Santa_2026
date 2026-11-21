"""Rebuild noncontiguous, convex regions found by spectral cuts of the arithmetic dependency graph."""
import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path

from interior_bands import active_graph,first_recipes,read_puzzles,read_submission,run_cuts,sha256,write_submission


def region_candidates(p,graph):
    import numpy as np
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.linalg import eigh

    order=list(graph)
    index={v:j for j,v in enumerate(order)}
    n=len(order)
    adj=np.zeros((n,n))
    parents=[[] for _ in order]
    users=[[] for _ in order]
    def connect(a,b,w):
        adj[a,b]+=w
        adj[b,a]+=w
    for j,v in enumerate(order):
        op,a,b=graph[v]
        inputs=[index[x] for x in dict.fromkeys((a,b)) if x in index]
        for i in inputs:
            parents[j].append(i);users[i].append(j)
            connect(j,i,1.4 if op in '*/' else 1.)
        if len(inputs)==2:
            connect(*inputs,.5)
    ancestors=[1<<i for i in range(n)]
    descendants=ancestors.copy()
    for j in range(n):
        for i in parents[j]:
            ancestors[j]|=ancestors[i]
    for j in reversed(range(n)):
        for i in users[j]:
            descendants[j]|=descendants[i]
    targets=set(p.targets)
    found={}
    def offer(indices):
        if not 9<=len(indices)<=105:
            return
        up=down=0
        for i in indices:
            up|=ancestors[i];down|=descendants[i]
        mask=up&down
        size=mask.bit_count()
        if not 9<=size<=108 or mask in found:
            return
        loc=[i for i in range(n) if (mask>>i)&1]
        span=loc[-1]-loc[0]+1
        if span-size<max(3,size//8):
            return
        block=frozenset(order[i] for i in loc)
        ins={x for v in block for x in graph[v][1:]}-block
        outs={order[i] for i in loc if order[i] in targets or any(not (mask>>q)&1 for q in users[i])}
        if not 1<=len(ins)<=p.registers-2 or not 2<=len(outs)<=36:
            return
        gain=(size-len(outs))/(1+len(ins)**.5+len(outs)**.5)
        found[mask]=(-gain,'spectral',loc[0],size,block,ins,outs)
    def split(ids,depth):
        m=len(ids)
        if m<12 or depth>4:
            return
        weights=adj[np.ix_(ids,ids)]
        degree=weights.sum(axis=1)
        if min(degree)<=0:
            return
        inv=degree**-.5
        lap=np.eye(m)-weights*inv[:,None]*inv[None,:]
        _,vectors=eigh(lap,subset_by_index=(0,min(2,m-1)),check_finite=False,driver='evr')
        partitions=[]
        for axis in range(1,vectors.shape[1]):
            value=vectors[:,axis]*inv
            if value[int(np.argmax(abs(value)))]<0:
                value=-value
            perm=np.argsort(value,kind='stable')
            arranged=[ids[i] for i in perm]
            W=weights[np.ix_(perm,perm)];volume=0.;inside=0.;total=degree.sum();best=None
            for j,idx in enumerate(perm[:-1],1):
                volume+=degree[idx]
                inside+=2*W[j-1,:j-1].sum()
                if m//4<=j<=3*m//4 and volume>0 and total>volume:
                    metric=(volume-inside)*(1/volume+1/(total-volume))
                    if best is None or (metric,j)<best:
                        best=metric,j
            if best:
                cut=best[1]
                offer(arranged[:cut]);offer(arranged[cut:])
                if axis==1:
                    partitions=[arranged[:cut],arranged[cut:]]
            for width in sorted({min(65,m//3),min(92,m//2)}):
                if width>=9:
                    for start in sorted({0,(m-width)//2,m-width}):
                        offer(arranged[start:start+width])
        for part in partitions:
            split(part,depth+1)
    count,groups=connected_components(csr_matrix(adj),directed=False)
    for group in range(count):
        ids=np.flatnonzero(groups==group).tolist()
        offer(ids);split(ids,0)
    return sorted(found.values(),key=lambda e:(e[:4],tuple(sorted(e[4]))))


def work(task):
    p,tape,engine,rounds,count=task
    raw=first_recipes(p,tape)
    live=active_graph(p,raw)
    graph={v:e for v,e in raw.items() if v in live}
    choices=region_candidates(p,graph)
    cuts=[]
    for c in choices:
        if any(len(c[4]&prev[4])*2>len(c[4]|prev[4]) for prev in cuts):
            continue
        cuts.append(c)
        if len(cuts)==count:
            break
    i,best,r=run_cuts(p,tape,engine,rounds,graph,cuts,784551+int(p.id[-4:]))
    r.update(after=len(best),candidates=len(choices),chosen=[sorted(c[4]) for c in cuts])
    return i,best,r


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','puzzles','engine','out'):
        ap.add_argument('--'+k,type=Path,required=True)
    for k,n in [('count',100),('offset',0),('jobs',7),('regions',3),('rounds',480)]:
        ap.add_argument('--'+k,type=int,default=n)
    a=ap.parse_args();ps=read_puzzles(a.puzzles);parents=read_submission(a.parent)
    ordered=sorted((p for p in ps if len(parents[p.id])>=35),key=lambda p:hashlib.sha256(('spectral1-'+p.id).encode()).digest())
    jobs=[(p,parents[p.id],a.engine,a.rounds,a.regions) for p in ordered[a.offset:a.offset+a.count]]
    rows,wins={},{}
    with ProcessPoolExecutor(a.jobs) as ex:
        for i,t,row in ex.map(work,jobs):
            rows[i]=row
            if len(t)<len(parents[i]):
                wins[i]=t
    a.out.mkdir(parents=True,exist_ok=True)
    write_submission(a.out/'wins.csv',[p for p in ps if p.id in wins],wins)
    spec=dict(eligible=len(ordered),parent_sha256=sha256(a.parent),engine_sha256=sha256(a.engine),
              settings={k:v for k,v in vars(a).items() if isinstance(v,int)},rows=rows)
    (a.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(spec,separators=(',',':')).encode(),mtime=0))
    print(len(rows),len(wins),sum(len(parents[i])-len(t) for i,t in wins.items()))


if __name__=='__main__':
    main()
