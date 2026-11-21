"""Look for shorter arithmetic graphs with temporary workspace, then compile them at 48 registers."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'generative/wang'))
from elf import check,read_puzzles,write_submission
from graph import first_recipes,compile_graph
from replay_search import encode
from solvers.gpu.gpu_schedule import schedule_like

BASE='95f3008'


def table(path):
    data=subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT)
    return {z['id']:z for z in csv.DictReader(io.StringIO(data.decode('utf-8-sig')))}


def pressure(p,tape):
    # Each occurrence lives from its producing operation to its last operand read.
    origin=list(range(-len(p.seeds),0))+[None]*(p.registers-len(p.seeds))
    last={}
    for k,(_,a,b,dest) in enumerate(tape):
        last[origin[a]]=last[origin[b]]=k
        origin[dest]=k
    delta=[0]*(len(tape)+1)
    for node,end in last.items():
        start=max(0,node+1);delta[start]+=1;delta[end+1]-=1
    used=peak=pressure_sum=0
    for change in delta[:-1]:
        used+=change;peak=max(peak,used);pressure_sum+=max(0,used-34)
    return peak,pressure_sum


def search(job):
    p,lane,tape,exe,rounds=job
    roomy=SimpleNamespace(id=p.id,seeds=p.seeds,targets=p.targets,limit=p.limit,registers=72)
    seed=231133+int(p.id[-4:])
    def optimize(q,t):
        raw=subprocess.run([str(exe)],input=encode(q,'anneal_diverse',rounds,seed,[t]),text=True,capture_output=True,check=True).stdout.split()
        out=tuple((raw[k],*map(int,raw[k+1:k+4])) for k in range(1,len(raw),4))
        if len(out)!=int(raw[0]) or len(raw)!=1+4*len(out):raise ValueError('truncated program')
        return out
    virtual=optimize(roomy,tape)
    high=max(max(instr[1:]) for instr in virtual)
    best=tape;restored=None
    if len(virtual)<len(tape):
        if high<p.registers:
            check(p,virtual);best=virtual;restored=len(best)
        else:
            graph=first_recipes(roomy,virtual)
            options=[schedule_like(p,tape,graph),compile_graph(p,graph,attempts=8,recompute=True,schedule_width=8,operation_width=20)]
            valid=[v for v in options if v is not None]
            if valid:
                recovered=min(valid,key=len);restored=len(recovered)
                if len(recovered)<len(best):check(p,recovered);best=recovered
    direct=optimize(p,tape)
    regular=len(direct)
    if regular<len(best):check(p,direct);best=direct
    row=dict(id=p.id,lane=lane,before=len(tape),after=len(best),expanded=len(virtual),largest_register=high,restored=restored,
             direct=regular,peak=pressure(p,tape),seed=seed,rounds=rounds)
    if len(best)<len(tape):row['program']=best
    return row


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('puzzles','binary','out'):ap.add_argument('--'+k,type=Path,required=True)
    ap.add_argument('--jobs',type=int,default=5);ap.add_argument('--rounds',type=int,default=420)
    a=ap.parse_args();a.out.mkdir(exist_ok=True,parents=True)
    ps=read_puzzles(a.puzzles);jobmap={};keys={};credits={};ranked={}
    for lane,pre in [('public','public-assisted/'),('own','')]:
        base={i:tuple(map(tuple,json.loads(z['program']))) for i,z in table(pre+'submission.csv').items()}
        credits[lane]=table(pre+'origins.csv');cases=[]
        for p in ps:
            if len(base[p.id])<100:continue
            peak,area=pressure(p,base[p.id])
            cases.append((peak,area,p.id,p))
        cases.sort(key=lambda z:(-z[0],-z[1],z[2]))
        ranked[lane]=[p.id for _,_,_,p in cases[:36]]
        for _,_,i,p in cases[:36]:
            t=base[i];key=(i,t)
            jobmap.setdefault(key,(p,lane,t,a.binary.resolve(),a.rounds));keys[lane,i]=key
    (a.out/'design.json').write_bytes((json.dumps(dict(base=BASE,initial_registers=48,search_registers=72,ids=ranked,rounds=a.rounds),indent=2)+'\n').encode())
    with ThreadPoolExecutor(a.jobs) as pool:res=dict(zip(jobmap,pool.map(search,jobmap.values())))
    summary={}
    for lane,ids in ranked.items():
        rows=[res[keys[lane,i]] for i in ids];wins={z['id']:z['program'] for z in rows if 'program' in z}
        write_submission(a.out/(lane+'.csv'),[p for p in ps if p.id in wins],wins)
        with (a.out/(lane+'.origins.csv')).open('w',encoding='utf8',newline='') as f:
            wr=csv.writer(f);wr.writerow(['id','upstream_source'])
            wr.writerows((i,credits[lane][i].get('upstream_source') or 'Generated from official inputs') for i in sorted(wins))
        summary[lane]=dict(wins={i:len(t) for i,t in wins.items()},saved=sum(z['before']-z['after'] for z in rows),
                           extra=sum(z['direct']-z['after'] for z in rows),above_limit=sum(z['largest_register']>=48 for z in rows))
    payload=dict(base=BASE,ids=ranked,rows=list(res.values()),summary=summary)
    (a.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(payload,separators=(',',':')).encode(),mtime=0))
    print(summary,flush=True)

if __name__=='__main__':
    main()
