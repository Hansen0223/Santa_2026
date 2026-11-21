"""Join a prefix to a different program's suffix by rebuilding its missing live inputs."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'collaboration/retained-pool'))
from neutral_lead import solve
from elf import check,read_puzzles,read_submission,replay,sha256,write_submission
from graph import active_graph,compile_graph,first_recipes
from solvers.gpu.gpu_schedule import schedule_like
from solvers.gpu.pooled_joins import inverse
from solvers.graphs.corpus_prefix import arithmetic_edges


def traces(p,tape):
    trace=replay(p,tape)
    stride=max(3,len(tape)//22)
    cuts=set(range(3,len(tape)-3,stride))
    cuts.update(len(tape)*k//10 for k in range(1,10))
    prefix={}
    prefixes={}
    for j,(v,op,a,b) in enumerate(trace):
        if j in cuts:
            prefixes[j]=(dict(prefix),set(prefix)|set(p.seeds))
        if v not in p.seeds:
            prefix.setdefault(v,(op,a,b))
    wanted=set(p.targets)
    suffix={}
    inputs=set()
    # Each suffix starts with the values read before being defined there.
    for j in range(len(trace)-1,-1,-1):
        v,op,a,b=trace[j]
        inputs.discard(v)
        inputs.update((a,b))
        suffix[v]=(op,a,b)
        if j in cuts:
            yield j,*prefixes[j],dict(suffix),inputs|(wanted-suffix.keys())


def bridge(p,available,required):
    missing=set(required)-available
    patch={}
    if not missing:
        return patch
    cheap={}
    small=sorted(available)[:32]
    for i,a in enumerate(small):
        for b in small[:i+1]:
            for v,r in arithmetic_edges(a,b,p.limit):
                if v not in available and v not in r[1:]:
                    cheap.setdefault(v,r)
    known=set(available)
    while missing:
        best=None
        for v in sorted(missing):
            for a in sorted(known):
                for b,recipe in inverse(v,a,p.limit):
                    if v in recipe[1:]:
                        continue
                    if b in known:
                        candidate=(1,v,recipe,0,None)
                    elif b in cheap and v not in cheap[b][1:]:
                        candidate=(2,v,recipe,b,cheap[b])
                    else:
                        continue
                    if best is None or candidate[:4]<best[:4]:
                        best=candidate
                if best is not None and best[:2]==(1,v):
                    break
        if best is None:
            return None
        _,v,r,b,build=best
        if build:
            patch[b]=build
            known.add(b)
            missing.discard(b)
        patch[v]=r
        known.add(v)
        missing.remove(v)
    return patch


def edge_set(g):
    return frozenset((v,op,*sorted((a,b))) if op in '+*' else (v,op,a,b) for v,(op,a,b) in g.items())


def alternatives(p,base,donors):
    base_graph=first_recipes(p,base)
    parent_edges=edge_set(base_graph)
    old=list(traces(p,base))
    candidates=[]
    stats=Counter()
    for name,donor in donors:
        other=list(traces(p,donor))
        options=[]
        for reverse,src,dst in [(False,old,other),(True,other,old)]:
            length=len(base) if reverse else len(donor)
            for i,pref,known,_,_ in src:
                for j,_,_,tail,req in dst:
                    missing=req-known
                    if len(missing)>3 or i+length-j>len(base)+17:
                        continue
                    # A new suffix may no longer need some earlier calculations.
                    rank=abs(i+length-j-len(base))+2*len(missing)
                    options.append((rank,-min(i,length-j),i,j,reverse,pref,known,tail,req))
        stats['matches']+=len(options)
        for _,_,i,j,reverse,pref,known,tail,req in sorted(options,key=lambda x:x[:5])[:64]:
            patch=bridge(p,known,req)
            if patch is None:
                continue
            stats['bridged']+=bool(patch)
            try:
                # An input already available from the prefix takes precedence.
                g=active_graph(p,tail|patch|pref)
            except (ValueError,KeyError):
                continue
            if len(g)>len(base)+3:
                continue
            edges=edge_set(g)
            if edges==parent_edges:
                continue
            candidates.append((len(g),-len(edges^parent_edges),name,i,j,reverse,len(patch),edges,g))
    candidates.sort(key=lambda x:x[:7])
    output=[]
    chosen=[]
    for _,_,name,i,j,reverse,h,edges,g in candidates:
        if any(len(edges^prev)<3 for prev in chosen):
            continue
        t=compile_graph(p,g,attempts=5)
        if t is None:
            t=schedule_like(p,base,g)
        if t is not None and len(t)<=len(base)+3:
            output.append((t,dict(donor=name,head=i,tail=j,reverse=reverse,adapter=h)))
            chosen.append(edges)
            if len(output)==4:
                break
    return output,dict(stats)


def work(task):
    p,base,donors,engine,rounds=task
    starts,metrics=alternatives(p,base,donors)
    best=base
    row=dict(before=len(base),metrics=metrics,starts=[])
    if starts:
        seed=803211+int(p.id[-4:])
        control=solve(engine,p,[base],seed,rounds)
        best=min((base,control),key=len)
        row['control']=len(control)
        for tape,record in starts[:2]:
            searched=solve(engine,p,[tape],seed,rounds)
            best=min((best,tape,searched),key=len)
            row['starts'].append(dict(record,length=len(tape),searched=len(searched)))
    check(p,best)
    return p.id,best,row


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for field in ('puzzles','parent','engine','out'):
        ap.add_argument('--'+field,required=True,type=Path)
    ap.add_argument('--donors',required=True,nargs='+',type=Path)
    for flag,n in [('count',80),('offset',0),('rounds',430),('jobs',6)]:
        ap.add_argument('--'+flag,type=int,default=n)
    a=ap.parse_args()
    ps=read_puzzles(a.puzzles)
    primary=read_submission(a.parent)
    banks={d.name:read_submission(d) for d in a.donors}
    if len(banks)!=len(a.donors):
        raise ValueError('Use distinct donor file names')
    tasks=[]
    for p in sorted(ps,key=lambda p:hashlib.sha256(('stitch1-'+p.id).encode()).digest()):
        base=primary[p.id]
        if len(base)<40:
            continue
        inc=edge_set(first_recipes(p,base))
        options=[]
        for name,bank in banks.items():
            t=bank.get(p.id)
            if not t or t==base or not 0<=len(t)-len(base)<=18:
                continue
            edges=edge_set(first_recipes(p,t))
            distance=len(edges^inc)
            if distance>=4:
                options.append(((len(t)-len(base)+1)/min(distance,90)**.5,name,t,edges))
        selected=[]
        seen=set()
        for _,name,t,edges in sorted(options,key=lambda x:x[:2]):
            if edges not in seen:
                selected.append((name,t))
                seen.add(edges)
                if len(selected)==2:
                    break
        if selected:
            tasks.append((p,base,selected,a.engine,a.rounds))
    rows,wins={},{}
    a.out.mkdir(exist_ok=True,parents=True)
    with ProcessPoolExecutor(a.jobs) as pool:
        for i,t,row in pool.map(work,tasks[a.offset:a.offset+a.count]):
            rows[i]=row
            if len(t)<len(primary[i]):
                wins[i]=t
    write_submission(a.out/'wins.csv',[p for p in ps if p.id in wins],wins)
    record=dict(parent_sha256=sha256(a.parent),engine_sha256=sha256(a.engine),eligible=len(tasks),rounds=a.rounds,offset=a.offset,
                donors={d.name:sha256(d) for d in a.donors},rows=rows)
    (a.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(record,separators=(',',':')).encode(),mtime=0))
    print(len(rows),len(wins),sum(len(primary[i])-len(t) for i,t in wins.items()),flush=True)


if __name__=='__main__':
    main()
