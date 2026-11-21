"""Rank integer scales by repeated cheap residues and connect existing targets across them."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
from math import isqrt
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from square_products import ingredient_bank, compile_selection
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes


def ranked_scales(targets, graph, starts):
    seeds=set()
    for t in targets:
        for k in range(1,25):
            x=isqrt(t//k)
            seeds.update(range(max(200,x-1),min(2_000_000,x+2)+1))
    values=np.array(targets,dtype=np.int64)
    digits=np.array(sorted({0,1,2,3,*starts,*(x for x in graph if x<=131072)}),dtype=np.int64)
    def evaluate(scales):
        batch=np.array(sorted(scales),dtype=np.int64)
        ranked=[]
        for i in range(0,len(batch),256):
            h=batch[i:i+256,None]
            residue=values%h
            residue=np.minimum(residue,h-residue)
            loc=np.minimum(np.searchsorted(digits,residue),len(digits)-1)
            distance=np.minimum(abs(digits[loc]-residue),abs(digits[np.maximum(loc-1,0)]-residue))
            information=np.maximum(0,np.log2(h/(2*np.searchsorted(digits,h//2,side='right')+1))-np.log2(1+2*distance))
            information.sort(axis=1)
            # Exclude the strongest observation, which may have generated this modulus.
            support=np.maximum(information[:,-7:-1]-1,0).sum(axis=1)
            ranked.extend((float(s),int(v)) for s,v in zip(support,h[:,0]))
        return sorted(ranked,reverse=True)
    extra=set()
    for _,h in evaluate(seeds)[:18]:
        for t in targets:
            for k in (1,2,3,4):
                q=(t+h*k//2)//(h*k)
                if 200<=q<=2_000_000:
                    extra.update((q-1,q,q+1))
    return evaluate(seeds|extra)


def bridge_paths(p,graph,scales):
    core,makers,build=ingredient_bank(p,graph)
    hubs=[]
    for score,h in scales:
        if score<=0:
            break
        if build(h) is not None:
            hubs.append(h)
        if len(hubs)==16:
            break
    paths=[]
    for t in p.targets:
        candidates=[]
        for y in (0,*p.targets):
            if t==y:
                continue
            for h in hubs:
                k=(abs(t-y)+h//2)//h
                product=k*h
                if k<2 or product>p.limit:
                    continue
                center=y+product if t>y else y-product
                if not 0<center<=p.limit:
                    continue
                error=t-center
                parts={h,k}
                if error:
                    parts.add(abs(error))
                estimate=sum(0 if v in core else 1 if v in makers else 3 for v in parts)
                if estimate>5:
                    continue
                candidates.append((estimate+bool(y)+bool(error),abs(error),k,h,y,center))
        count=0
        for _,_,k,h,y,center in sorted(set(candidates)):
            error=t-center
            ingredients=[h,k]+([abs(error)] if error else [])
            pieces=[build(v) for v in ingredients]
            if any(piece is None for piece in pieces):
                continue
            patch={}
            for piece in pieces:
                patch.update(piece)
            product=k*h
            patch[product]=('*',h,k)
            if y:
                patch[center]=('+' if t>y else '-',y,product)
            if error:
                patch[t]=('+' if error>0 else '-',center,abs(error))
            if any(v in edge[1:] for v,edge in patch.items()):
                continue
            patch={v:e for v,e in patch.items() if v not in p.seeds}
            paths.append(patch)
            count+=1
            if count==8:
                break
    return hubs,paths


def work(task):
    p,parent=task
    graph=active_graph(p,first_recipes(p,parent))
    offers=ranked_scales(p.targets,graph,p.seeds)
    hubs,patches=bridge_paths(p,graph,offers)
    status,best=compile_selection(p,parent,graph,patches,False) if patches else ({},parent)
    check(p,best)
    return p.id,best,dict(before=len(parent),after=len(best),hubs=hubs,paths=len(patches),search=status)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for opt in ('puzzles','parent','out'):
        ap.add_argument('--'+opt,required=True,type=Path)
    ap.add_argument('--jobs',type=int,default=5)
    ap.add_argument('--count',type=int,default=64)
    args=ap.parse_args()
    ps=read_puzzles(args.puzzles)
    bank=read_submission(args.parent)
    chosen=sorted((p for p in ps if 28<=len(p.targets)<=32 and max(p.seeds)<=35),
                  key=lambda p:hashlib.sha256(('residue1-'+p.id).encode()).digest())[:args.count]
    args.out.mkdir(parents=True,exist_ok=True)
    rows,wins={},{}
    with ProcessPoolExecutor(args.jobs) as pool:
        for i,t,row in pool.map(work,[(p,bank[p.id]) for p in chosen]):
            rows[i]=row
            if len(t)<len(bank[i]):
                wins[i]=t
    write_submission(args.out/'wins.csv',[p for p in ps if p.id in wins],wins)
    data=dict(parent_sha256=sha256(args.parent),rows=rows)
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(data,separators=(',',':')).encode(),mtime=0))
    print(len(rows),len(wins),sum(len(bank[i])-len(t) for i,t in wins.items()),flush=True)


if __name__=='__main__':
    main()
