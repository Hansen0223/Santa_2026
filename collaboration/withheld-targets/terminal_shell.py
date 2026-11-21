"""Optimize all shared boundary values together while retaining the final target operations."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
from dataclasses import replace
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'generative/wang'))
from elf import check,read_puzzles,write_submission
from graph import active_graph,compile_graph,first_recipes
from replay_search import encode
from solvers.gpu.gpu_schedule import schedule_like

BASE='a82562d'


def table(name):
    raw=subprocess.check_output(['git','show',BASE+':'+name],cwd=ROOT)
    return {z['id']:z for z in csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))}


def decomposition(p,t,variant):
    g=active_graph(p,first_recipes(p,t))
    sinks={v:1<<j for j,v in enumerate(p.targets)};depth=Counter()
    for v,(_,a,b) in reversed(g.items()):
        for u in {a,b}:
            sinks[u]=sinks.get(u,0)|sinks.get(v,0);depth[u]=max(depth[u],depth[v]+1)
    if variant=='private':
        locked={v for v in g if sinks.get(v,0).bit_count()==1}
    else:
        locked={v for v in g if depth[v]<3}
    head={v:r for v,r in g.items() if v not in locked}
    shell={v:r for v,r in g.items() if v in locked}
    # The private rule may put an internal goal in the head, so it remains a boundary demand.
    if any(u in locked for _,a,b in head.values() for u in (a,b)):return None
    boundary=(set(p.targets)&head.keys())|{u for _,a,b in shell.values() for u in (a,b) if u in head}
    if not (12<=len(head) and 6<=len(shell) and boundary):return None
    inner=replace(p,targets=tuple(sorted(boundary)))
    tape=compile_graph(inner,head,recompute=True,schedule_width=5)
    if tape is None:return None
    return inner,tape,shell,head


def optimize(p,t,exe,seed,rounds):
    cmd=encode(p,'anneal_diverse',rounds,seed,[t])
    words=subprocess.run([str(exe)],input=cmd,text=True,capture_output=True,check=True).stdout.split()
    result=tuple((words[j],*map(int,words[j+1:j+4])) for j in range(1,len(words),4))
    if len(result)!=int(words[0]) or 1+4*len(result)!=len(words):raise ValueError('truncated graph search')
    return result


def search(job):
    p,lane,tape,exe,rounds,variants=job
    seed=709511+int(p.id[-4:]);best=tape
    rec=dict(id=p.id,lane=lane,before=len(tape),seed=seed,rounds=rounds,arms={})
    for name in variants:
        split=decomposition(p,tape,name)
        if split is None:continue
        inner,current,shell,head=split
        improved=optimize(inner,current,exe,seed,rounds)
        tail=dict(boundary=len(inner.targets),prefix=len(head),initial=len(current),rebuilt=len(improved),terminal=len(shell),result=len(tape))
        if improved!=current and len(improved)<=len(current):
            graph=first_recipes(inner,improved)|shell
            candidates=[schedule_like(p,tape,graph),compile_graph(p,graph,attempts=6,recompute=True,schedule_width=6)]
            for candidate in candidates:
                if candidate is not None and len(candidate)<tail['result']:
                    check(p,candidate)
                    tail['result']=len(candidate)
                    if len(candidate)<len(best):best=candidate
        rec['arms'][name]=tail
    rec['after']=len(best)
    if len(best)<len(tape):rec['program']=best
    return rec


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('puzzles','binary','out'):ap.add_argument('--'+k,type=Path,required=True)
    ap.add_argument('--jobs',type=int,default=6);ap.add_argument('--rounds',type=int,default=560)
    ap.add_argument('--offset',type=int,default=0);ap.add_argument('--count',type=int,default=48)
    ap.add_argument('--lane',choices=('both','own','public'),default='both')
    ap.add_argument('--variant',choices=('both','private','terminal'),default='both')
    a=ap.parse_args();a.out.mkdir(exist_ok=True,parents=True);ps=read_puzzles(a.puzzles)
    tables={};credits={}
    for lane,pre in [('public','public-assisted/'),('own','')]:
        tables[lane]={i:tuple(map(tuple,json.loads(z['program']))) for i,z in table(pre+'submission.csv').items()}
        credits[lane]=table(pre+'origins.csv')
    ps=[p for p in ps if 12<=len(p.targets)<=39 and 100<=len(tables['public'][p.id])<=270]
    ps.sort(key=lambda p:hashlib.sha256(('terminal-shell-1'+p.id).encode()).digest())
    if a.offset<0 or a.count<1:ap.error('choose a nonnegative offset and positive count')
    cases=ps[a.offset:a.offset+a.count]
    if not cases:ap.error('selection is empty')
    lanes=tuple(tables) if a.lane=='both' else (a.lane,)
    variants=('terminal','private') if a.variant=='both' else (a.variant,)
    (a.out/'design.json').write_bytes((json.dumps(dict(base=BASE,ids=[q.id for q in cases],rounds=a.rounds,offset=a.offset,lanes=lanes,variants=variants),indent=2)+'\n').encode())
    jobs={};keys={}
    for p in cases:
        for lane in lanes:
            t=tables[lane][p.id];key=p.id,t
            jobs.setdefault(key,(p,lane,t,a.binary.resolve(),a.rounds,variants));keys[lane,p.id]=key
    with ThreadPoolExecutor(a.jobs) as pool:records=dict(zip(jobs,pool.map(search,jobs.values())))
    summary={}
    for lane in lanes:
        rows=[records[keys[lane,p.id]] for p in cases];wins={r['id']:r['program'] for r in rows if 'program' in r}
        write_submission(a.out/(lane+'.csv'),[p for p in cases if p.id in wins],wins)
        with (a.out/(lane+'.origins.csv')).open('w',encoding='utf8',newline='') as f:
            wr=csv.writer(f);wr.writerow(['id','upstream_source'])
            wr.writerows((i,credits[lane][i].get('upstream_source') or 'Generated from official inputs') for i in wins)
        summary[lane]=dict(wins={i:len(t) for i,t in wins.items()},saved=sum(r['before']-r['after'] for r in rows))
    payload=dict(base=BASE,summary=summary,rows=list(records.values()))
    (a.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(payload,separators=(',',':')).encode(),mtime=0))
    print(summary,flush=True)

if __name__=='__main__':
    main()
