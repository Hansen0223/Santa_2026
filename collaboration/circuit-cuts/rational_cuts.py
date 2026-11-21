"""Resynthesize bounded arithmetic cuts as multivariate polynomials and rational functions."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'collaboration/structure-controls/ruler'),str(ROOT/'collaboration/register-search')]
from elf import check,read_puzzles,read_submission,sha256,write_submission
from graph import active_graph,first_recipes
from interior_bands import compile_on_parent
from selector import compile_selection


def fragment(g,root,leaves):
    nodes=set()
    todo=[root]
    while todo:
        v=todo.pop()
        if v not in leaves and v not in nodes:
            nodes.add(v)
            todo.extend(g[v][1:])
    return {v:e for v,e in g.items() if v in nodes}


def cut_options(g,root):
    start=frozenset(g[root][1:])
    wave={start}
    seen={start}
    options=[]
    for depth in range(1,7):
        next_wave=set()
        for leaves in wave:
            for v in leaves & g.keys():
                more=frozenset((leaves-{v})|set(g[v][1:]))
                if len(more)<=4 and more not in seen:
                    next_wave.add(more)
                    seen.add(more)
        picked=[]
        for leaves in sorted(next_wave,key=lambda s:tuple(sorted(s))):
            region=fragment(g,root,leaves)
            ops=Counter(e[0] for e in region.values())
            varied=bool(ops['+']+ops['-']) and bool(ops['*']+ops['/'])
            if varied and 3<=len(region)<=10:
                rank=(len(region)-len(leaves),ops['/']>0,len(region),-len(leaves))
                options.append((rank,tuple(sorted(leaves)),region))
            picked.append(((len(region)-len(leaves),int(varied),ops['/']),leaves))
        wave={s for _,s in sorted(picked,key=lambda v:v[0],reverse=True)[:6]}
    return sorted(options,key=lambda v:(v[0],v[1]),reverse=True)[:3]


@lru_cache(maxsize=4)
def polynomial_ring(n):
    from sympy import ZZ
    from sympy.polys.rings import ring
    out=ring(','.join('x'+str(i) for i in range(n)),ZZ)
    return out[0],out[1:]


def rational(leaves,graph,root):
    ring,gens=polynomial_ring(len(leaves))
    pieces={v:(x,ring.one) for v,x in zip(leaves,gens)}
    for v,(op,a,b) in graph.items():
        an,ad=pieces[a];bn,bd=pieces[b]
        if op=='+':
            n,d=an*bd+bn*ad,ad*bd
        elif op=='-':
            n,d=an*bd-bn*ad,ad*bd
        elif op=='*':
            n,d=an*bn,ad*bd
        else:
            n,d=an*bd,ad*bn
        if not d or not n or max(len(n),len(d))>14:
            return None
        if max(sum(m) for f in (n,d) for m in f)>8:
            return None
        if not d==ring.one:
            n,d=n.cancel(d)
        pieces[v]=(n,d)
    return pieces[root]


class Builder:
    def __init__(self,p,g):
        self.p=p
        self.g=g
        self.recipes={}
        self.known=set(p.seeds)|g.keys()

    def op(self,op,a,b):
        if op=='+':
            v=a+b
        elif op=='*':
            v=a*b
        else:
            if b==0 or a%b:
                raise ValueError('not an exact quotient')
            v=a//b
        k=abs(v);x,y=abs(a),abs(b)
        if k>self.p.limit:
            raise ValueError('over the bound')
        if not k or k in self.p.seeds or k in (x,y):
            return v
        if op=='+':
            r=('+',min(x,y),max(x,y)) if a*b>=0 else ('-',max(x,y),min(x,y))
        elif op=='*':
            r=('*',min(x,y),max(x,y))
        else:
            r=('/',x,y)
        self.recipes.setdefault(k,r)
        return v

    def constant(self,c):
        k=abs(c)
        if k>24:
            raise ValueError('large coefficient')
        if k and k not in self.known and k not in self.recipes:
            if k==1:
                x=self.p.seeds[0]
                self.recipes[1]=('/',x,x)
            else:
                half=self.constant(k//2)
                value=self.op('+',half,half)
                if k%2:
                    self.op('+',value,self.constant(1))
        return c

    def evaluate(self,terms,leaves,order):
        if not terms:
            return 0
        var=next((i for i in order if any(m[i] for m in terms)),None)
        if var is None:
            return self.constant(int(next(iter(terms.values()))))
        take={};rem={}
        for m,c in terms.items():
            if m[var]:
                m=m[:var]+(m[var]-1,)+m[var+1:]
                take[m]=c
            else:
                rem[m]=c
        a=self.evaluate(take,leaves,order)
        b=self.evaluate(rem,leaves,order)
        return self.op('+',self.op('*',a,leaves[var]),b)

    def factors(self,f,leaves,order):
        coeff,fs=f
        value=self.constant(int(coeff))
        for poly,times in fs:
            k=self.evaluate(dict(poly),leaves,order)
            for _ in range(times):
                value=self.op('*',value,k)
        return value


def canon(e):
    op,a,b=e
    return (op,min(a,b),max(a,b)) if op in '+*' else e


def propose(p,g,root,leaves,region):
    pair=rational(leaves,region,root)
    if pair is None:
        return
    plain=tuple((1,[(poly,1)]) for poly in pair)
    forms=[('expanded',plain)]
    if any(len(poly)>1 and any(sum(m)>1 for m in poly) for poly in pair):
        factored=tuple(poly.factor_list() for poly in pair)
        if any(sum(k for _,k in fs)>1 for _,fs in factored):
            forms.append(('factored',factored))
    order=tuple(range(len(leaves)))
    uses=tuple(sorted(order,key=lambda j:-sum(m[j] for poly in pair for m in poly)))
    for name,(num,den) in forms:
        for permutation in dict.fromkeys((order,order[::-1],uses,uses[::-1])):
            b=Builder(p,g)
            try:
                value=b.op('/',b.factors(num,leaves,permutation),b.factors(den,leaves,permutation))
            except ValueError:
                continue
            if value!=root or root not in b.recipes:
                continue
            path=b.recipes
            if not any(v not in g or canon(g[v])!=canon(e) for v,e in path.items()):
                continue
            # Check which definitions the new root actually needs. Existing boundary
            # values remain paid by the caller. Inactive constant recipes drop out.
            needed={};todo=[root]
            while todo:
                v=todo.pop()
                if v not in leaves and v in path and v not in needed:
                    needed[v]=path[v]
                    todo.extend(path[v][1:])
            if needed:
                yield needed,name


def work(job):
    p,parent,limit=job
    g=active_graph(p,first_recipes(p,parent))
    roots=sorted(g,key=lambda v:hashlib.sha256((p.id+'-'+str(v)).encode()).digest())
    plans={};counts=Counter();best=parent
    for root in roots:
        cuts=cut_options(g,root)
        if not cuts:
            continue
        counts['roots']+=1
        for _,leaves,region in cuts:
            counts['cuts']+=1
            for alt,kind in propose(p,g,root,leaves,region):
                signature=frozenset((v,canon(e)) for v,e in alt.items())
                if signature in plans:
                    continue
                try:
                    merged=active_graph(p,g|alt)
                except (KeyError,ValueError):
                    continue
                counts['legal_dags']+=1
                if len(merged)>len(parent)+2:
                    continue
                plans[signature]=(len(merged),alt,kind)
                if len(merged)<len(best):
                    tape=compile_on_parent(p,parent,merged)
                    if tape is not None and len(tape)<len(best):
                        best=tape
        if counts['roots']>=limit:
            break
    direct=len(best)
    ranked=sorted(plans.values(),key=lambda t:t[0])[:80]
    if ranked:
        summary,mixed=compile_selection(p,parent,g,[x[1] for x in ranked],False)
        best=min((best,mixed),key=len)
    else:
        summary={}
    check(p,best)
    return p.id,best,dict(before=len(parent),direct=direct,after=len(best),counts=dict(counts),
                          eligible_plans=len(plans),selected_plans=len(ranked),cp=summary)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('puzzles','parent','out'):
        ap.add_argument('--'+k,type=Path,required=True)
    for k,n in [('count',48),('offset',0),('jobs',6),('roots',26)]:
        ap.add_argument('--'+k,type=int,default=n)
    a=ap.parse_args();ps=read_puzzles(a.puzzles);bank=read_submission(a.parent)
    selected=sorted((p for p in ps if len(bank[p.id])>=30),key=lambda p:hashlib.sha256(('rational1-'+p.id).encode()).digest())
    jobs=[(p,bank[p.id],a.roots) for p in selected[a.offset:a.offset+a.count]]
    wins,rows={},{}
    with ProcessPoolExecutor(a.jobs) as pool:
        for i,t,row in pool.map(work,jobs):
            rows[i]=row
            if len(t)<len(bank[i]):
                wins[i]=t
    a.out.mkdir(exist_ok=True,parents=True)
    write_submission(a.out/'wins.csv',[p for p in ps if p.id in wins],wins)
    info=dict(rows=rows,parent_sha256=sha256(a.parent),settings={k:v for k,v in vars(a).items() if isinstance(v,int)})
    (a.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(info,separators=(',',':')).encode(),mtime=0))
    print(len(rows),len(wins),sum(len(bank[i])-len(t) for i,t in wins.items()))


if __name__=='__main__':
    main()
