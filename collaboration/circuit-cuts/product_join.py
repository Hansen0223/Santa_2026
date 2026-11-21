"""Search for two independently built branches that meet at an existing value."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'collaboration/retained-pool'))
from elf import check,read_puzzles,read_submission,sha256,write_submission
from graph import active_graph,compile_graph,first_recipes
from neutral_lead import solve
from solvers.gpu.gpu_join import cut_many
from solvers.gpu.gpu_schedule import schedule_like


def cuts(p,g,count,anchor_count):
    uses=Counter(x for _,a,b in g.values() for x in {a,b})
    goals=set(p.targets)
    candidates=[]
    for v in g:
        if v not in goals and uses[v]<2:
            continue
        surviving,free=cut_many(p,g,{v})
        private=g.keys()-surviving.keys()
        if len(private)<4:
            continue
        anchors=set(p.seeds)|free.keys()
        borders=Counter(x for x1 in private for x in set(g[x1][1:]) if x in anchors)
        priority=sorted(anchors,key=lambda a:(a not in p.seeds,-borders[a],-uses[a],a))
        scale=sorted(anchors,key=lambda a:(abs(a.bit_length()*2-v.bit_length()),-uses[a],a))
        roster=list(dict.fromkeys(priority[:anchor_count*2//3]+scale[:anchor_count//4]+priority))[:anchor_count]
        candidates.append((len(private),v,roster,v in goals))
    # Include shared internal roots as well as entire target branches.
    ranked=sorted(candidates,key=lambda a:(-a[0],a[1]))
    split=[q for q in ranked if q[3]][:count//2]+[q for q in ranked if not q[3]][:count//2]
    selected={q[1] for q in split}
    return (split+[q for q in ranked if q[1] not in selected])[:count]


def search(job):
    p,parent,binary,engine,count,anchors,width,rounds=job
    graph=active_graph(p,first_recipes(p,parent))
    cases=cuts(p,graph,count,anchors)
    text=''.join(' '.join(map(str,(p.limit,v,private+1,width,len(bank),*bank)))+'\n'
                 for private,v,bank,_ in cases)
    lines=iter(subprocess.run([str(binary)],input=text,text=True,capture_output=True,check=True).stdout.splitlines())
    results=[]
    stats=Counter(cuts=len(cases))
    old_set=set(graph)
    for _,v,_,_ in cases:
        entries,number=map(int,next(lines).split())
        stats['entries']+=entries
        stats['witnesses']+=number
        local=[]
        for _ in range(number):
            patch={}
            for _ in range(int(next(lines))):
                out,op,a,b=next(lines).split()
                patch[int(out)]=(op,int(a),int(b))
            trial=graph|patch
            try:
                live=active_graph(p,trial)
            except (ValueError,KeyError):
                continue
            if len(live)>len(parent)+1:
                continue
            changes={u:r for u,r in live.items() if graph.get(u)!=r}
            if changes:
                local.append((len(live),-len(live.keys()-old_set),changes))
        seen=set()
        for size,_,changes in sorted(local,key=lambda q:q[:2]):
            key=frozenset(changes.items())
            if key not in seen:
                results.append((size,v,changes))
                seen.add(key)
                if len(seen)>=4:
                    break
    if next(lines,None) is not None:
        raise ValueError('Unexpected trailing program')
    candidates=list(results)
    for j,(_,v,patch) in enumerate(results):
        new=patch.keys()-old_set
        for _,other,second in results[:j]:
            if v==other or not new.intersection(second):
                continue
            joined=patch|second
            try:
                live=active_graph(p,graph|joined)
            except (ValueError,KeyError):
                continue
            if len(live)<=len(parent)+1:
                candidates.append((len(live),v,joined))
    best=parent
    alternatives=[]
    fingerprints=set()
    for size,_,patch in sorted(candidates,key=lambda q:(q[0],-len(q[2]))):
        key=frozenset(patch.items())
        if key in fingerprints or (size>=len(best) and (engine is None or len(alternatives)>=4)):
            continue
        fingerprints.add(key)
        trial=active_graph(p,graph|patch)
        tape=compile_graph(p,trial,attempts=4)
        if tape is None:
            tape=schedule_like(p,parent,trial)
        if tape is None or len(tape)>len(parent)+1:
            continue
        if len(tape)<len(best):
            best=tape
        if tape!=parent and tape not in alternatives and len(alternatives)<4:
            alternatives.append(tape)
    stats.update(before=len(parent),direct=len(best),patches=len(results),paired=len(candidates)-len(results))
    if engine and alternatives:
        seed=184203+int(p.id[-4:])
        control=solve(engine,p,[parent],seed,rounds)
        treated=solve(engine,p,[min(alternatives,key=len),parent,*alternatives[1:]],seed,rounds)
        stats.update(control=len(control),treated=len(treated),alternatives=len(alternatives))
        best=min((best,control,treated),key=len)
    check(p,best)
    return p.id,best,dict(stats)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for field in ('puzzles','parent','binary','out'):
        ap.add_argument('--'+field,required=True,type=Path)
    ap.add_argument('--engine',type=Path)
    for flag,default in [('count',64),('offset',0),('cuts',6),('anchors',46),('width',200),('jobs',6),('rounds',450)]:
        ap.add_argument('--'+flag,type=int,default=default)
    a=ap.parse_args()
    ps=read_puzzles(a.puzzles)
    bank=read_submission(a.parent)
    selected=sorted((p for p in ps if len(bank[p.id])>=45),key=lambda p:hashlib.sha256(('prod-joins2-'+p.id).encode()).digest())[a.offset:a.offset+a.count]
    wins,rows={},{}
    a.out.mkdir(exist_ok=True,parents=True)
    with ProcessPoolExecutor(a.jobs) as pool:
        for i,t,record in pool.map(search,[(p,bank[p.id],a.binary,a.engine,a.cuts,a.anchors,a.width,a.rounds) for p in selected]):
            rows[i]=record
            if len(t)<len(bank[i]):
                wins[i]=t
    write_submission(a.out/'wins.csv',[p for p in ps if p.id in wins],wins)
    record=dict(parent_sha256=sha256(a.parent),binary_sha256=sha256(a.binary),engine_sha256=sha256(a.engine) if a.engine else None,
                settings={k:v for k,v in vars(a).items() if isinstance(v,int)},rows=rows)
    (a.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(record,separators=(',',':')).encode(),mtime=0))
    print(len(rows),len(wins),sum(len(bank[i])-len(t) for i,t in wins.items()),flush=True)


if __name__=='__main__':
    main()
