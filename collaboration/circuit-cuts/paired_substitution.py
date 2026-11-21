"""Change both input branches of an arithmetic junction and match their new outputs exactly."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'collaboration/retained-pool'))
from elf import arithmetic, check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, compile_graph, first_recipes
from neutral_lead import solve
from solvers.gpu.gpu_schedule import schedule_like
from solvers.gpu.pooled_joins import inverse


def branches(graph,tip,limit):
    # A chain names the selected operand at each substitution site.
    paths = [(tip,())]
    pending = [(tip,())]
    while pending:
        v,path = pending.pop()
        if len(path)>=4 or v not in graph:
            continue
        op,a,b = graph[v]
        for u,other,left in [(a,b,True),(b,a,False)]:
            if u not in graph or (a==b and not left):
                continue
            step = (op,other,left,a==b)
            chain = (step,*path)
            paths.append((u,chain))
            pending.append((u,chain))
    return sorted(paths,key=lambda q:(-len(q[1]),q[0],q[1]))[:limit]+[(tip,())]


def alternatives(graph,tip,eligible,cap,width):
    options = {tip:({},None)}
    counts = 0
    for start,path in branches(graph,tip,10):
        near = sorted(eligible,key=lambda x:(abs(x-start),x))
        scale = sorted(eligible)
        sampled = [scale[j*len(scale)//width] for j in range(width)]
        anchors = list(dict.fromkeys([*near[:width//2],*sampled,*near]))[:width]
        for substitute in anchors:
            if substitute==start:
                continue
            new = substitute
            patch = {}
            try:
                for op,other,left,both in path:
                    a,b = (new,new) if both else ((new,other) if left else (other,new))
                    new = arithmetic(op,a,b)
                    if not 1<=new<=cap:
                        break
                    if new not in eligible:
                        patch.setdefault(new,(op,a,b))
                else:
                    counts += 1
                    if new!=tip and (new not in options or len(patch)<len(options[new][0])):
                        options[new] = (patch,(start,substitute,len(path)))
            except ValueError:
                continue
    return options,counts


def work(task):
    p,parent,engine,cases,width,rounds = task
    base = active_graph(p,first_recipes(p,parent))
    users = defaultdict(set)
    size = dict.fromkeys(p.seeds,frozenset())
    desc = {}
    for v,(_,a,b) in base.items():
        users[a].add(v);users[b].add(v)
        size[v] = size[a]|size[b]|{v}
    for v in reversed(base):
        desc[v] = {v}.union(*(desc[w] for w in users[v]))
    paid = set(p.seeds)|base.keys()
    junctions = []
    for v,(_,a,b) in base.items():
        if a==b or a not in base or b not in base or a in size[b] or b in size[a]:
            continue
        left,right=size[a]-size[b],size[b]-size[a]
        rank=min(len(left),len(right))+min(8,len(left|right))*.25+min(3,len(users[v]))
        junctions.append((-rank,v,a,b))
    records = []
    best = parent
    metrics = Counter()
    seen = set()
    for _,v,a,b in sorted(junctions)[:cases]:
        safe = paid-desc[v]
        left,n = alternatives(base,a,safe,p.limit,width)
        right,m = alternatives(base,b,safe,p.limit,width)
        metrics.update(cases=1,branches=n+m)
        for x,(p1,h1) in left.items():
            if h1 is None:
                continue
            for y,finish in inverse(v,x,p.limit):
                entry = right.get(y)
                if entry is None or entry[1] is None or v in finish[1:]:
                    continue
                p2,h2 = entry
                if max(h1[2],h2[2])<1 or (not p1 and not p2):
                    continue
                metrics['matched']+=1
                patch = p1|p2|{v:finish}
                key=frozenset(patch.items())
                if key in seen:
                    continue
                seen.add(key)
                try:
                    whole=active_graph(p,base|patch)
                except (ValueError,KeyError):
                    continue
                if len(whole)<=len(parent)+2 and whole.keys()-base.keys():
                    records.append((len(whole),v,h1,h2,whole))
    seed=422521+int(p.id[-4:])
    report=dict(before=len(parent),metrics=dict(metrics),candidates=len(records),starts=[])
    picked=set()
    for _,v,h1,h2,g in sorted(records,key=lambda x:x[:4]):
        fresh=frozenset(g.keys()-base.keys())
        if fresh in picked:continue
        t=compile_graph(p,g,attempts=3)
        if t is None:t=schedule_like(p,parent,g)
        if t is None or len(t)>len(parent)+2:continue
        if not picked:
            control=solve(engine,p,[parent],seed,rounds)
            report['control']=len(control)
            best=min((control,best),key=len)
        picked.add(fresh)
        s=solve(engine,p,[t],seed,rounds)
        report['starts'].append(dict(junction=v,left=h1,right=h2,raw=len(t),searched=len(s)))
        best=min((best,t,s),key=len)
        if len(picked)>=2:break
    check(p,best)
    report['final']=len(best)
    return p.id,best,report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('puzzles','parent','engine','out'):
        ap.add_argument('--'+key,type=Path,required=True)
    for key,n in [('count',75),('offset',0),('jobs',6),('cases',20),('width',46),('rounds',400)]:
        ap.add_argument('--'+key,type=int,default=n)
    args=ap.parse_args();ps=read_puzzles(args.puzzles);bank=read_submission(args.parent)
    selected=sorted((p for p in ps if len(bank[p.id])>=25),key=lambda p:hashlib.sha256(('pairsub1-'+p.id).encode()).digest())
    tasks=[(p,bank[p.id],args.engine,args.cases,args.width,args.rounds) for p in selected[args.offset:args.offset+args.count]]
    rows,wins={},{}
    with ProcessPoolExecutor(args.jobs) as ex:
        for i,t,row in ex.map(work,tasks):
            rows[i]=row
            if len(t)<len(bank[i]):wins[i]=t
    args.out.mkdir(exist_ok=True,parents=True)
    write_submission(args.out/'wins.csv',[p for p in ps if p.id in wins],wins)
    info=dict(parent_sha256=sha256(args.parent),engine_sha256=sha256(args.engine),settings={k:v for k,v in vars(args).items() if isinstance(v,int)},rows=rows)
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(info,separators=(',',':')).encode(),mtime=0))
    print(len(rows),len(wins),sum(len(bank[i])-len(t) for i,t in wins.items()),flush=True)


if __name__=='__main__':
    main()
