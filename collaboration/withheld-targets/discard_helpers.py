"""Rebuild a shared arithmetic dictionary by discarding redundant helpers from a larger feasible set."""
import argparse
from collections import Counter,defaultdict
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
from elf import check,read_puzzles,write_submission
from graph import active_graph,compile_graph,first_recipes
from solvers.gpu.gpu_schedule import schedule_like
from solvers.graphs.corpus_prefix import arithmetic_edges

BASE='d4f6d99'
CAPS=(96,384,1536,6144,24576,98304)


def regions(p,tape):
    graph=active_graph(p,first_recipes(p,tape))
    users=defaultdict(set)
    for v,(_,a,b) in graph.items():
        for u in (a,b):users[u].add(v)
    seen=set();options=[]
    for cap in CAPS:
        known=set(p.seeds);head={}
        for v,e in graph.items():
            if v<=cap and e[1] in known and e[2] in known:
                head[v]=e;known.add(v)
        head.update((v,e) for v,e in graph.items() if v not in head and e[1] in known and e[2] in known)
        boundary={v for v in head if v in p.targets or users[v]-head.keys()}
        h=frozenset(head.keys()-boundary)
        if h in seen or len(h)<3 or not 4<=len(boundary)<=35 or len(head)>55:continue
        seen.add(h)
        options.append((cap,head,boundary))
    if not options:return []
    options.sort(key=lambda z:(-(len(z[1])-len(z[2])),-len(z[2]),z[0]))
    return [(*z,{v:e for v,e in graph.items() if v not in z[1]}) for z in options[:2]]


def inverse(t,u,limit):
    yield abs(t-u)
    if t+u<=limit:yield t+u
    if t%u==0:yield t//u
    if u%t==0:yield u//t
    if t<=limit//u:yield t*u


def palette(p,head,bound):
    seeds=set(p.seeds);fixed=seeds|set(head);early=Counter();birth=Counter()
    seed_steps=set(seeds)
    for a in seeds:
        for b in seeds:
            seed_steps.update(v for v,_ in arithmetic_edges(a,b,p.limit))
    ordered=sorted(fixed)
    for j,a in enumerate(ordered):
        for b in ordered[:j+1]:
            for v,e in arithmetic_edges(a,b,p.limit):
                if v in fixed:continue
                birth[v]+=1
                if a in seed_steps and b in seed_steps:early[v]+=1
    hits=Counter()
    for t in bound:
        possible={v for x in fixed for v in inverse(t,x,p.limit) if v>0 and v!=t and v not in fixed}
        hits.update(possible)
    def rank(v):
        return (-hits[v],-int(v in seed_steps),-min(3,early[v]),-min(4,birth[v]),v)
    frontier=sorted(birth.keys()&hits.keys(),key=rank)[:72]
    frontier+=sorted((hits.keys()-birth.keys()),key=rank)[:18]
    frontier+=sorted((early.keys()-set(frontier)),key=lambda v:(-min(3,early[v]),v))[:24]
    return list(dict.fromkeys(frontier))


def search(job):
    p,tape,lane,options,exe,rounds=job;best=tape;rows=[]
    for cap,head,targets,tail in options:
        goals=sorted(targets);old=sorted(head.keys()-targets);extra=palette(p,head,targets)
        seeds=tuple(dict.fromkeys(p.seeds));seed=int(p.id[-4:])+cap+608551
        fields=(p.limit,len(seeds),len(goals),len(old),len(extra),rounds,seed,*seeds,*goals,*old,*extra)
        sql=subprocess.run([str(exe)],input=' '.join(map(str,fields))+'\n',text=True,capture_output=True,check=True)
        it=iter(sql.stdout.splitlines());n,start,after=map(int,next(it).split())
        rebuilt={}
        for line in it:
            v,op,a,b=line.split();rebuilt[int(v)]=(op,int(a),int(b))
        if n!=len(rebuilt) or start!=len(old) or n!=len(goals)+after:raise ValueError('invalid search response')
        row=dict(cap=cap,before=len(head),after=n,goals=len(goals),pool=len(extra),seed=seed,full=len(tape))
        if n<len(head):
            proposed=tail|rebuilt
            try:joined=active_graph(p,proposed)
            except (KeyError,ValueError):joined=None
            if joined is not None:
                attempts=(schedule_like(p,tape,joined),compile_graph(p,joined,recompute=True,schedule_width=6))
                valid=[s for s in attempts if s is not None]
                if valid:
                    t=min(valid,key=len)
                    if len(t)<len(best):check(p,t);best=t
                    row['full']=min(len(t),len(tape))
        rows.append(row)
    return dict(id=p.id,lane=lane,before=len(tape),after=len(best),regions=rows),best


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('puzzles','archive','binary','out'):ap.add_argument('--'+key,type=Path,required=True)
    ap.add_argument('--count',type=int,default=40);ap.add_argument('--offset',type=int,default=0)
    ap.add_argument('--rounds',type=int,default=260);ap.add_argument('--jobs',type=int,default=6)
    args=ap.parse_args();args.out.mkdir(exist_ok=True,parents=True)
    ps=read_puzzles(args.puzzles);pm={p.id:p for p in ps}
    own=baseline('submission.csv',BASE);public=baseline('public-assisted/submission.csv',BASE)
    external=donor(args.archive);combined={i:min((v,external[i]),key=len) for i,v in public.items()}
    bounds=__import__('csv').DictReader(subprocess.check_output(['git','show',BASE+':collaboration/puzzle-bounds.csv'],cwd=ROOT).decode('utf-8-sig').splitlines())
    exact={row['id'] for row in bounds if int(row['tight'])}
    queue={};lanes={};sizes={}
    for lane,table in [('own',own),('combined',combined)]:
        eligible=[]
        for p in ps:
            if p.id in exact:continue
            t=table[p.id];opts=regions(p,t)
            if opts:
                gain=max(len(h)-len(g) for c,h,g,tail in opts)
                tie=hashlib.sha256(('dictionary-discard-v1'+p.id).encode()).digest()
                eligible.append((-gain,tie,p.id,opts))
        eligible.sort(key=lambda z:z[:2]);sizes[lane]=len(eligible)
        ranked=eligible[:16]+sorted(eligible[16:],key=lambda z:z[1])
        batch=ranked[args.offset:args.offset+args.count];lanes[lane]=[]
        for _,_,i,op in batch:
            key=(i,table[i]);lanes[lane].append(key)
            queue.setdefault(key,(pm[i],table[i],lane,op,args.binary.resolve(),args.rounds))
    design=dict(base=BASE,eligible=sizes,ids={k:[i for i,t in v] for k,v in lanes.items()},rounds=args.rounds)
    (args.out/'design.json').write_text(json.dumps(design,indent=2)+'\n',encoding='utf8')
    with ThreadPoolExecutor(args.jobs) as pool:answer=dict(zip(queue,pool.map(search,queue.values())))
    report=dict(design=design,summary={},records={})
    for lane,ids in lanes.items():
        rows=[];wins={}
        for key in ids:
            z,t=answer[key];rows.append(z)
            if len(t)<z['before']:
                wins[key[0]]=t
                z['program_sha256']=hashlib.sha256(json.dumps(t,separators=(',',':')).encode()).hexdigest()
        write_submission(args.out/(lane+'.csv'),[pm[i] for i in wins],wins)
        report['summary'][lane]=dict(wins=len(wins),saved=sum(r['before']-r['after'] for r in rows))
        report['records'][lane]=rows
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(report,separators=(',',':')).encode(),mtime=0))
    print(report['summary'],flush=True)


if __name__=='__main__':
    main()