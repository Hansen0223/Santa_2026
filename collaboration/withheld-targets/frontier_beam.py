"""Replan several targets jointly using alternative partial programs and a fixed retained arithmetic graph."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'public-assisted/pardheev'))
from combine import baseline,donor
from elf import read_puzzles,check,write_submission
from graph import first_recipes,active_graph,compile_graph
from solvers.gpu.gpu_schedule import schedule_like

BASE='1a91fe0'


def partition(p,tape):
    g=active_graph(p,first_recipes(p,tape));targets=list(dict.fromkeys(p.targets))
    masks={v:1<<i for i,v in enumerate(targets)}
    for v,(_,x,y) in reversed(g.items()):
        for u in {x,y}:masks[u]=masks.get(u,0)|masks.get(v,0)
    counts=Counter(masks[v] for v in g)
    def released(m):return sum(n for k,n in counts.items() if k and not k&~m)
    plans=[]
    for i in range(len(targets)):
        m=1<<i
        for size in range(2,min(6,len(targets))+1):
            candidates=[(released(m|(1<<j)),j) for j in range(len(targets)) if not m&(1<<j)]
            n,j=max(candidates);m|=1<<j
            if size in (4,6):plans.append((n/size,n,m))
    if not plans:return None
    _,n,m=max(plans)
    if n<8:return None
    chosen=[v for j,v in enumerate(targets) if m&(1<<j)]
    removed={v:e for v,e in g.items() if not masks[v]&~m}
    kept={v:e for v,e in g.items() if v not in removed}
    required=sorted(v for v in chosen if v in removed)
    if len(required)<2:return None
    uses=Counter(u for _,a,b in removed.values() for u in {a,b})
    all_values=set(kept)|set(p.seeds)
    # The engine knows the whole retained computation. Its short two-step dictionary
    # emphasizes values actually used at the old interface, then the original seeds.
    leaves=sorted(all_values,key=lambda v:(-uses[v],v not in p.seeds,-int(v in p.targets),v))
    return kept,removed,required,leaves


def solve(job):
    p,lane,t,split,exe,width,leaves=job;kept,removed,targets,seeds=split;seed=int(p.id[-4:])+260611
    data=' '.join(map(str,(p.limit,len(seeds),len(targets),len(removed),*seeds,*targets)))+'\n'
    data+=''.join(f'{v} {op} {a} {b}\n' for v,(op,a,b) in removed.items())
    result=subprocess.run([str(exe),str(width),str(leaves),str(seed)],input=data,capture_output=True,text=True,check=True)
    lines=iter(result.stdout.splitlines());n,expanded=map(int,next(lines).split());new={}
    for line in lines:
        v,op,a,b=line.split();new[int(v)]=(op,int(a),int(b))
    if n!=len(new):raise ValueError('incomplete beam output')
    best=t
    if len(new)<len(removed):
        graph=kept|new
        choices=(schedule_like(p,t,graph),compile_graph(p,graph,recompute=True,schedule_width=6))
        for v in choices:
            if v is not None and len(v)<len(best):check(p,v);best=v
    row=dict(id=p.id,lane=lane,goals=targets,old_part=len(removed),new_part=n,expanded=expanded,before=len(t),after=len(best))
    if len(best)<len(t):row['sha256']=hashlib.sha256(json.dumps(best,separators=(',',':')).encode()).hexdigest()
    return row,best


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for k in ('puzzles','archive','binary','out'):parser.add_argument('--'+k,required=True,type=Path)
    parser.add_argument('--count',type=int,default=16);parser.add_argument('--offset',type=int,default=0)
    parser.add_argument('--width',type=int,default=4);parser.add_argument('--leaves',type=int,default=32)
    parser.add_argument('--jobs',type=int,default=4)
    a=parser.parse_args();a.out.mkdir(exist_ok=True,parents=True);ps=read_puzzles(a.puzzles);pm={p.id:p for p in ps}
    own=baseline('submission.csv',BASE);pub=baseline('public-assisted/submission.csv',BASE);ext=donor(a.archive)
    combined={i:min((t,ext[i]),key=len) for i,t in pub.items()}
    order=sorted((p.id for p in ps if 12<=len(p.targets)<=40 and 70<=len(combined[p.id])<=220),
                 key=lambda i:hashlib.sha256(('target-order-2'+i).encode()).digest())
    store={};lanes={}
    for lane,table in [('own',own),('combined',combined)]:
        batch=[]
        for i in order:
            split=partition(pm[i],table[i])
            if split is None:continue
            batch.append((i,split))
            if len(batch)>=a.count+a.offset:break
        lanes[lane]=[]
        for i,s in batch[a.offset:]:
            k=(i,table[i]);lanes[lane].append(k)
            store.setdefault(k,(pm[i],lane,table[i],s,a.binary.resolve(),a.width,a.leaves))
    design=dict(base=BASE,ids={label:[i for i,_ in keys] for label,keys in lanes.items()},width=a.width,leaves=a.leaves)
    (a.out/'design.json').write_text(json.dumps(design,indent=2)+'\n',encoding='utf8')
    with ThreadPoolExecutor(a.jobs) as pool:results=dict(zip(store,pool.map(solve,store.values())))
    report=dict(design=design,summary={},rows={})
    for lane,keys in lanes.items():
        group=[results[k] for k in keys];wins={z['id']:t for z,t in group if z['before']>z['after']}
        write_submission(a.out/(lane+'.csv'),[pm[i] for i in wins],wins)
        report['rows'][lane]=[z for z,t in group];report['summary'][lane]=dict(wins=len(wins),saved=sum(z['before']-z['after'] for z,t in group))
    (a.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(report,separators=(',',':')).encode(),mtime=0))
    print(report['summary'],flush=True)


if __name__=='__main__':
    main()