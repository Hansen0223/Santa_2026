"""Optimize a circuit after a reversible change to the puzzle's initial numbers."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'collaboration/target-partition'))
from compare import run_native
from elf import check, read_puzzles, write_submission
from graph import active_graph, compile_graph, first_recipes
from solvers.graphs.corpus_prefix import arithmetic_edges

BASE = 'b49db2f'


def frozen(path):
    raw = subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT)
    return {r['id']:r for r in csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))}


def digest(*args):
    return hashlib.sha256(json.dumps(args,separators=(',',':')).encode()).hexdigest()


def exchanges(p, graph):
    weights = Counter()
    for v,(_,a,b) in graph.items():
        weights.update({a,b})
    weights.update(p.targets)
    def rank(old, value, currently):
        accessible = set()
        for u in currently:
            for x,_ in arithmetic_edges(value,u,p.limit):
                if x in graph: accessible.add(x)
        support = sum(1+min(weights[x],6) for x in accessible)
        return (support + 3*min(weights[value],8) - 2*min(weights[old],6),
                value in graph, -value.bit_length(), -value)
    basis=list(p.seeds); visited=set(basis); construction={};recovery={};moves=[]
    for depth in range(2):
        options=[]
        for index,a in enumerate(basis):
            for b in basis:
                if b==a:continue
                choices=[(a+b,('+',a,b),('-',a+b,b))]
                if a>b:choices.append((a-b,('-',a,b),('+',a-b,b)))
                else:choices.append((b-a,('-',b,a),('-',b,b-a)))
                if a<=p.limit//b:choices.append((a*b,('*',a,b),('/',a*b,b)))
                if a%b==0:choices.append((a//b,('/',a,b),('*',a//b,b)))
                for v,forward,reverse in choices:
                    if v in visited or v>p.limit or v in p.targets:continue
                    remaining=[z for j,z in enumerate(basis) if j!=index]
                    options.append((rank(a,v,remaining),index,a,v,forward,reverse))
        if not options:break
        _,index,a,v,fwd,back=max(options)
        construction[v]=fwd;recovery[a]=back;basis[index]=v;visited.add(v)
        moves.append(dict(drop=a,introduce=v,forward=fwd,reverse=back))
    return basis,construction,recovery,moves


def run(job):
    p,tape,exe,rounds=job
    graph=active_graph(p,first_recipes(p,tape))
    seeds,forward,reverse,moves=exchanges(p,graph)
    temporary=replace(p,seeds=tuple(seeds))
    input_tape=compile_graph(temporary,graph | reverse,recompute=True,schedule_width=3)
    seeds=[int(digest('basis1',p.id,k)[:8],16) for k in range(2)]
    direct=run_native(p,tape,exe,seeds[0],rounds)
    direct=run_native(p,direct,exe,seeds[1],rounds)
    best=tape
    result=dict(parent=digest(tape),before=len(tape),moves=moves,direct=len(direct),warm=None)
    if input_tape is not None:
        first=run_native(temporary,input_tape,exe,seeds[0],rounds)
        body=active_graph(temporary,first_recipes(temporary,first))
        options=[]
        for candidate in (body | forward,forward | body):
            restored=compile_graph(p,candidate,recompute=True,schedule_width=3)
            if restored is not None:options.append(restored)
        if options:
            restored=min(options,key=len)
            second=run_native(p,restored if len(restored)<=len(tape)+5 else tape,exe,seeds[1],rounds)
            best=min((tape,restored,second),key=len)
        result.update(warm=len(input_tape),temporary=len(first),restored=min(map(len,options),default=None))
    result['basis']=len(best)
    winner=min((direct,best),key=len)
    if len(winner)<len(tape):
        check(p,winner)
        result['program']=winner
    return result


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    for option in ('puzzles','exe','out'):
        cli.add_argument('--'+option,type=Path,required=True)
    cli.add_argument('--jobs',type=int,default=6)
    cli.add_argument('--rounds',type=int,default=320)
    args=cli.parse_args();args.out.mkdir(exist_ok=True,parents=True)
    ps=read_puzzles(args.puzzles);sources={};credits={}
    for lane,pre in [('own',''),('public','public-assisted/')]:
        sources[lane]={i:tuple(map(tuple,json.loads(v['program']))) for i,v in frozen(pre+'submission.csv').items()}
        credits[lane]=frozen(pre+'origins.csv')
    eligible=[p for p in ps if len(set(p.seeds))>=2 and 15<=len(p.targets)<=37 and 75<=len(sources['public'][p.id])<=275]
    ranked=sorted(eligible,key=lambda p:(-len(sources['public'][p.id])/len(p.targets),p.id))
    selected=sorted(ranked[:len(ranked)//3],key=lambda p:digest('basis1-hard',p.id))[:20]+sorted(ranked[len(ranked)//3:],key=lambda p:digest('basis1-mixed',p.id))[:16]
    design=dict(base=BASE,eligible=len(eligible),hard=[p.id for p in selected[:20]],mixed=[p.id for p in selected[20:]],rounds=args.rounds)
    (args.out/'design.json').write_bytes((json.dumps(design,indent=2)+'\n').encode())
    tasks={};keys={}
    for p in selected:
        for lane in sources:
            tape=sources[lane][p.id];key=p.id+'-'+digest(tape)[:16]
            tasks[key]=(p,tape,args.exe.resolve(),args.rounds);keys[lane,p.id]=key
    with ThreadPoolExecutor(args.jobs) as pool:
        results=dict(zip(tasks,pool.map(run,tasks.values())))
    stats={}
    for lane in sources:
        wins={};savings=Counter();beats=[]
        for p in selected:
            rec=results[keys[lane,p.id]]
            for arm in ('direct','basis'):savings[arm]+=rec['before']-rec[arm]
            if rec['basis']<rec['direct']:beats.append(p.id)
            if 'program' in rec:wins[p.id]=rec['program']
        write_submission(args.out/(lane+'.csv'),[p for p in selected if p.id in wins],wins)
        with (args.out/(lane+'.origins.csv')).open('w',encoding='utf8',newline='') as f:
            writer=csv.writer(f);writer.writerow(['id','upstream_source'])
            writer.writerows((i,credits[lane][i].get('upstream_source') or 'Generated from official inputs') for i in wins)
        stats[lane]=dict(savings=dict(savings),wins={i:len(t) for i,t in wins.items()},beats=beats)
    payload=dict(design=design,stats=stats,rows=results)
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(payload,separators=(',',':')).encode(),mtime=0))
    (args.out/'summary.json').write_bytes((json.dumps(stats,indent=2)+'\n').encode())
    print(stats,flush=True)


if __name__=='__main__':
    main()
