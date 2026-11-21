"""Recombine recipes from local search trajectories on changed puzzle programs."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from donor_masks import ROOT, read_puzzles, read_submission, write_submission, sha256
sys.path.insert(0,str(ROOT/'collaboration/structure-controls/ruler'))
from elf import arithmetic, check
from graph import active_graph, first_recipes
from selector import compile_selection


def harvest(exe,p,tape,seconds,seed,directory):
    header=['P',p.id,len(p.seeds),*p.seeds,len(p.targets),*p.targets,p.limit,p.registers,len(tape)]
    stream=[' '.join(map(str,header)),*(' '.join(map(str,op)) for op in tape),'0']
    with tempfile.TemporaryDirectory(dir=directory) as folder:
        dump=Path(folder)/'recipes.txt'
        proc=subprocess.run([str(exe),'--time',str(seconds),'--seed',str(seed),'--dump',str(dump),
                            '--hall','1','--alts','20','--kicks','1000','--kslack','2','--group','5'],
                            input='\n'.join(stream)+'\n',text=True,capture_output=True,check=True)
        with dump.open() as f:
            label,i,n=f.readline().split()
            if (label,i)!=('D',p.id):
                raise ValueError(p.id)
            edges=set()
            seen=0
            for line in f:
                op,sa,sb,sv=line.split()
                a,b,v=map(int,(sa,sb,sv))
                seen+=1
                if min(a,b,v)<1 or max(a,b,v)>p.limit or arithmetic(op,a,b)!=v:
                    raise ValueError((p.id,line))
                if v in (a,b) or v in p.seeds:
                    continue
                if op in '+*' and a>b:
                    a,b=b,a
                edges.add((v,op,a,b))
            if seen!=int(n):
                raise ValueError('Incomplete recipe dump')
    words=proc.stdout.split()
    if words:
        candidate=tuple((words[j],*map(int,words[j+1:j+4])) for j in range(4,len(words),4))
        if words[:3]!=['R',p.id,str(len(tape))] or check(p,candidate)!=int(words[3]):
            raise ValueError(p.id)
        return edges,candidate
    return edges,tape


def extract(p,g,votes):
    # Define new helpers from old values, then allow short chains between helpers.
    known=set(g)|set(p.seeds)
    ranked=sorted(votes,key=lambda e:(-votes[e],e))
    defs=defaultdict(list)
    for depth in range(2):
        layer=defaultdict(list)
        for v,op,a,b in ranked:
            if v not in known and a in known and b in known and len(layer[v])<2:
                layer[v].append((op,a,b))
        defs.update(layer)
        known.update(layer)
    # Estimate which old computations become dead when this recipe replaces one.
    uses=Counter(t for t in set(p.targets))
    for _,a,b in g.values():
        uses.update({a,b})
    def removed(v,inputs):
        dropped=set()
        stack=[v]
        while stack:
            x=stack.pop()
            if x in dropped:
                continue
            dropped.add(x)
            for u in g[x][1:]:
                if u in g and uses[u]==1 and u not in inputs:
                    stack.append(u)
        return len(dropped)
    alternatives=[]
    for v,op,a,b in ranked:
        if v not in g or a not in known or b not in known:
            continue
        original=g[v]
        if original==(op,a,b) or (op in '+*' and original==(op,b,a)):
            continue
        path={v:(op,a,b)}
        stack=[a,b]
        while stack:
            x=stack.pop()
            if x in defs and x not in path:
                edge=defs[x][0]
                path[x]=edge
                stack.extend(edge[1:])
        leaves={u for edge in path.values() for u in edge[1:]}-set(path)
        gain=removed(v,leaves)-len(path)
        alternatives.append((gain,votes[v,op,a,b],v,op,a,b,path))
    alternatives.sort(key=lambda t:t[:-1],reverse=True)
    return alternatives


def work(task):
    p,parents,exe,out,seconds=task
    votes=Counter()
    tapes=[]
    counts=[]
    for k,t in enumerate(parents):
        edges,candidate=harvest(exe,p,t,seconds,313371+6803*k+int(p.id[-4:]),out)
        votes.update(edges)
        tapes.append(candidate)
        counts.append(len(edges))
    best=min(tapes+[parents[0]],key=len)
    anchor=best
    graph=active_graph(p,first_recipes(p,anchor))
    candidates=extract(p,graph,votes)
    trials=[]
    # A broad optimization and smaller, less cyclic neighborhoods have different search costs.
    for options in [candidates[:160],candidates[:44],candidates[44:100]]:
        if options:
            info,candidate=compile_selection(p,anchor,graph,[t[-1] for t in options],False)
            trials.append(info)
            if len(candidate)<len(best):
                best=candidate
    check(p,best)
    return p.id,best,dict(before=len(parents[0]),starts=list(map(len,parents)),direct=list(map(len,tapes)),
                         recipes=counts,unique=len(votes),alternatives=len(candidates),trials=trials,after=len(best))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('puzzles','parent','previous','exe','out'):
        ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--donors',type=Path,nargs='*',default=[])
    ap.add_argument('--seconds',type=int,default=12)
    ap.add_argument('--jobs',type=int,default=5)
    a=ap.parse_args()
    ps=read_puzzles(a.puzzles)
    bank,old=map(read_submission,(a.parent,a.previous))
    donors=[read_submission(path) for path in a.donors]
    a.out.mkdir(parents=True,exist_ok=True)
    jobs=[]
    for p in ps:
        i=p.id
        if bank[i]!=old[i] and len(set(p.targets)-set(p.seeds))<=63:
            parents=list(dict.fromkeys([bank[i],old[i],*(d[i] for d in donors if i in d)]))
            jobs.append((p,parents,a.exe,a.out,a.seconds))
    rows,wins={},{}
    with ProcessPoolExecutor(a.jobs) as pool:
        for i,t,record in pool.map(work,jobs):
            rows[i]=record
            if len(t)<len(bank[i]):
                wins[i]=t
    write_submission(a.out/'wins.csv',[p for p in ps if p.id in wins],wins)
    info=dict(rows=rows,inputs={k:sha256(getattr(a,k)) for k in ('parent','previous','puzzles','exe')},
              donors=[sha256(f) for f in a.donors],seconds=a.seconds)
    (a.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(info,separators=(',',':')).encode(),mtime=0))
    print(len(rows),len(wins),sum(len(bank[i])-len(t) for i,t in wins.items()))


if __name__=='__main__':
    main()
