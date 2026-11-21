"""Combine approximate square roots inferred from targets into shared product circuits."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import csv
from functools import lru_cache
import gzip
import hashlib
import io
import json
from math import isqrt
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'collaboration/cross-puzzle-templates'))
from selector import compile_selection
from elf import check,read_puzzles,write_submission
from graph import active_graph,first_recipes
from solvers.graphs.corpus_prefix import arithmetic_edges

BASE='b49db2f'
SCALES=(1,2,3,4,5,6,8,9,12,16)


def frozen(path):
    data=subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT)
    return {r['id']:r for r in csv.DictReader(io.StringIO(data.decode('utf-8-sig')))}


def shape(p):
    hits=set()
    for t in p.targets:
        if t<20000:continue
        for k in SCALES:
            x=isqrt(t//k)
            for a in (x,x+1):
                if abs(t-k*a*a)<=max(300,a//5):
                    hits.add(t)
    return len(hits)


def ingredient_bank(p,g):
    use=Counter(v for r in g.values() for v in set(r[1:]))
    cones={v:0 for v in p.seeds}
    for i,(v,(_,a,b)) in enumerate(g.items()):
        cones[v]=cones[a]|cones[b]|(1<<i)
    core=set(cones)
    candidates=sorted(core,key=lambda v:(cones[v].bit_count(),-use[v],v))
    makers={};ranks={}
    for i,a in enumerate(candidates):
        for b in candidates[:i+1]:
            cost=(cones[a]|cones[b]).bit_count()
            for v,r in arithmetic_edges(a,b,p.limit):
                if v in core:continue
                rank=(cost,-(use[a]+use[b]))
                if v not in ranks or rank<ranks[v]:
                    ranks[v]=rank;makers[v]=r

    @lru_cache(maxsize=None)
    def build(v):
        if v in core:return {}
        if v in makers:return {v:makers[v]}
        best=None
        for u in candidates[:48]:
            options=[(v-u,('+',u,v-u)),(u-v,('-',u,u-v)),(v+u,('-',v+u,u))]
            if v%u==0:options.append((v//u,('*',u,v//u)))
            if u%v==0:options.append((u//v,('/',u,u//v)))
            if v<=p.limit//u:options.append((v*u,('/',v*u,u)))
            for other,edge in options:
                if other not in makers or other==v or u==v:continue
                key=(ranks[other][0]+cones[u].bit_count(),other,edge)
                if best is None or key<best:best=key
        if best is None:return None
        _,other,edge=best
        return {other:makers[other],v:edge}
    return core,makers,build


def discover(p,g,core,makers):
    votes=Counter()
    for t in p.targets:
        for k in SCALES:
            root=isqrt(t//k)
            for a in range(max(12,root-2),root+4):
                residual=abs(t-k*a*a)
                if residual>max(2500,a*3):continue
                votes[a]+=(4 if residual<=max(64,a//4) else 1)+(k==1)+(residual in core)
    for _,(op,a,b) in g.items():
        if op=='*' and a==b and a>=12:votes[a]+=5
    return sorted(votes,key=lambda a:(-(votes[a]+5*(a in core)+2*(a in makers)),-votes[a],a))[:24]


def shifted_product(p,t,a,b,k,d,e,build):
    xy=a*b
    shifted=xy+d
    product=k*shifted
    if not (0<xy<=p.limit and 0<shifted<=p.limit and 0<product<=p.limit and product+e==t):return None
    edges={}
    for v in {a,b,*(abs(x) for x in (d,e) if x),*([k] if k>1 else [])}:
        support=build(v)
        if support is None:return None
        edges.update(support)
    edges[xy]=('*',a,b)
    if d:edges[shifted]=('+' if d>0 else '-',xy,abs(d))
    if k>1:edges[product]=('*',k,shifted)
    if e:edges[t]=('+' if e>0 else '-',product,abs(e))
    for v in list(edges):
        if v in p.seeds:del edges[v]
        elif v in edges[v][1:]:return None
    return edges


def solve(job):
    p,tape,lane=job
    g=active_graph(p,first_recipes(p,tape));core,makers,build=ingredient_bank(p,g)
    roots=discover(p,g,core,makers);roots=[a for a in roots if build(a) is not None]
    paths=[];feasible=Counter()
    for t in set(p.targets)-set(p.seeds):
        options=[]
        for j,a in enumerate(roots):
            for b in roots[:j+1]:
                xy=a*b
                if xy>p.limit:continue
                k=max(1,(t+xy//2)//xy)
                if k>2048 or (k>1 and k not in core and k not in makers):continue
                r=t-k*xy
                d0=(r+k//2)//k
                if abs(d0)>max(3500,2*min(a,b)):continue
                for d in {0,d0}:
                    e=r-k*d
                    if abs(e)>max(3500,2*min(a,b)):continue
                    parts={a,b,*(abs(x) for x in (d,e) if x),*([k] if k>1 else [])}
                    estimated=sum(0 if x in core else (1 if x in makers else 2.5) for x in parts)
                    rank=(estimated+bool(d)+bool(e)+int(k>1),abs(e)+abs(d),a,b,k,d,e)
                    options.append(rank)
        paths_for_goal=0
        for _,_,a,b,k,d,e in sorted(set(options)):
            patch=shifted_product(p,t,a,b,k,d,e,build)
            if patch is None:continue
            paths.append(patch);paths_for_goal+=1
            feasible['square' if a==b else 'cross']+=1
            if paths_for_goal>=9:break
    if paths:result,best=compile_selection(p,tape,g,paths,False)
    else:result,best={},tape
    row=dict(id=p.id,lane=lane,before=len(tape),after=len(best),roots=roots,routes=dict(feasible),solver=result)
    if len(best)<len(tape):
        check(p,best);row['program']=best
    return row


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--puzzles',type=Path,required=True);cli.add_argument('--out',type=Path,required=True)
    cli.add_argument('--jobs',type=int,default=4);cli.add_argument('--limit',type=int,default=36)
    args=cli.parse_args();args.out.mkdir(exist_ok=True,parents=True)
    puzzles=read_puzzles(args.puzzles);tables={};credits={}
    for lane,pre in [('public','public-assisted/'),('own','')]:
        tables[lane]={i:tuple(map(tuple,json.loads(r['program']))) for i,r in frozen(pre+'submission.csv').items()}
        credits[lane]=frozen(pre+'origins.csv')
    selected=[p for p in puzzles if 12<=len(p.targets)<=38 and max(p.seeds)<=64 and shape(p)>=4]
    selected.sort(key=lambda p:(-shape(p),hashlib.sha256(('near-squares1'+p.id).encode()).digest()))
    selected=selected[:args.limit]
    jobs={};keys={}
    for p in selected:
        for lane,table in tables.items():
            t=table[p.id];key=(p.id,t)
            jobs.setdefault(key,(p,t,lane));keys[p.id,lane]=key
    design=dict(base=BASE,ids=[q.id for q in selected],priority='number of near scaled squares',scales=SCALES)
    (args.out/'design.json').write_bytes((json.dumps(design,indent=2)+'\n').encode())
    with ProcessPoolExecutor(args.jobs) as pool:
        results=dict(zip(jobs,pool.map(solve,jobs.values())))
    stats={}
    for lane in tables:
        rows=[results[keys[p.id,lane]] for p in selected]
        wins={q['id']:q['program'] for q in rows if 'program' in q}
        write_submission(args.out/(lane+'.csv'),[p for p in selected if p.id in wins],wins)
        with (args.out/(lane+'.origins.csv')).open('w',encoding='utf8',newline='') as f:
            writer=csv.writer(f);writer.writerow(['id','upstream_source'])
            writer.writerows((i,credits[lane][i].get('upstream_source') or 'Generated from official inputs') for i in wins)
        stats[lane]=dict(saved=sum(q['before']-q['after'] for q in rows),wins={i:len(t) for i,t in wins.items()})
    payload=dict(design=design,stats=stats,rows=list(results.values()))
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(payload,separators=(',',':')).encode(),mtime=0))
    print(stats,flush=True)


if __name__=='__main__':
    main()
