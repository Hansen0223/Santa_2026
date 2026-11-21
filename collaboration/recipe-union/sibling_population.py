"""Build a population of sibling circuits from each independent contribution, then cross the survivors."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import json
from pathlib import Path
import sys
import subprocess
from contributor_circuits import ROOT, CONTRIBUTOR, fetch, sha, encode, read_puzzles, write_submission, check
from graph import first_recipes

BASE = 'd4f6d99'
RAW = 'collaboration/lacia-independent/2026-11-20/shorter.csv'


def tape(row):
    return tuple(map(tuple,json.loads(row['program'])))


def pack(path, obj):
    path.write_bytes(gzip.compress(json.dumps(obj,separators=(',',':')).encode(),mtime=0))


def evolve(p, parents, mode, seed, rounds, binaries):
    binary=binaries/(mode+('.exe' if (binaries/(mode+'.exe')).exists() else ''))
    parents=list(dict.fromkeys(parents))
    args=encode(p,mode,rounds,seed,parents)
    words=subprocess.run([str(binary.resolve())],input=args,text=True,capture_output=True,check=True).stdout.split()
    n=int(words[0])
    if len(words)!=1+4*n:raise ValueError('truncated native output')
    program=tuple((words[j],*map(int,words[j+1:j+4])) for j in range(1,len(words),4))
    return program,dict(mode=mode,seed=seed,rounds=rounds,parents=[sha(t) for t in parents],sha256=sha(program),length=n)


def graph_edges(p,t):
    return frozenset((v,op,*sorted((x,y))) if op in '+*' else (v,op,x,y)
                     for v,(op,x,y) in first_recipes(p,t).items())


def representatives(p, programs, limit=4):
    unique=sorted(set(programs),key=lambda t:(len(t),sha(t)))
    edges={t:graph_edges(p,t) for t in unique}
    chosen=unique[:1]
    while len(chosen)<min(limit,len(unique)):
        rest=[t for t in unique if t not in chosen]
        def value(t):
            difference=min(len(edges[t]^edges[c]) for c in chosen)
            return (difference/(1+max(0,len(t)-len(unique[0])))**.65,-len(t),sha(t))
        chosen.append(max(rest,key=value))
    return chosen


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('puzzles','binaries','out'):ap.add_argument('--'+key,type=Path,required=True)
    ap.add_argument('--jobs',type=int,default=7)
    a=ap.parse_args();a.out.mkdir(exist_ok=True,parents=True)
    puzzles={p.id:p for p in read_puzzles(a.puzzles)}
    raw={i:tape(r) for i,r in fetch(CONTRIBUTOR,RAW).items()}
    own={i:tape(r) for i,r in fetch(BASE,'submission.csv').items() if i in raw}
    old={i:tape(r) for i,r in fetch('b49db2f','submission.csv').items() if i in raw}
    work=[(i,j) for i in sorted(raw) for j in range(4)]
    def first(job):
        i,j=job;mode=('anneal_diverse','incremental_diverse')[j%2]
        # Half the offspring start without exposure to the refined incumbent.
        group=[raw[i]] if j<2 else [raw[i],old[i],own[i]]
        return evolve(puzzles[i],group,mode,318673+int(i[-4:])+10007*j,780,a.binaries)
    phase=a.out/'siblings.json.gz'
    if phase.is_file():
        archive=json.loads(gzip.decompress(phase.read_bytes()))
        if archive['base']!=BASE or archive['contributor']!=CONTRIBUTOR:raise ValueError('different sibling ancestry')
        population={i:[(tuple(map(tuple,x['program'])),x['search']) for x in rows] for i,rows in archive['cases'].items()}
    else:
        with ThreadPoolExecutor(a.jobs) as pool:results=list(pool.map(first,work))
        population={i:[] for i in raw}
        for (i,_),r in zip(work,results):population[i].append(r)
        pack(phase,dict(base=BASE,contributor=CONTRIBUTOR,cases={i:[dict(search=r,program=t) for t,r in runs] for i,runs in population.items()}))
    survivors={i:representatives(puzzles[i],[own[i],*(t for t,r in population[i])]) for i in raw}
    def cross(job):
        i,j=job;parents=survivors[i]
        # Retain the shortest parent, then also start another search at the most divergent survivor.
        ordered=parents if j==0 else [*parents[1:2],parents[0],*parents[2:]]
        return evolve(puzzles[i],ordered,('incremental_diverse','anneal_diverse')[j],757583+int(i[-4:])+15401*j,1250,a.binaries)
    second=[(i,j) for i in sorted(raw) for j in range(2)]
    with ThreadPoolExecutor(a.jobs) as pool:results=list(pool.map(cross,second))
    children={i:[] for i in raw}
    for (i,_),r in zip(second,results):children[i].append(r)
    rows=[];wins={}
    for i in sorted(raw):
        initial=own[i];one=min([initial,*(t for t,r in population[i])],key=len)
        best=min([one,*(t for t,r in children[i])],key=len)
        z=dict(id=i,before=len(initial),first=len(one),after=len(best),survivors=[sha(t) for t in survivors[i]],
               population=[r for _,r in population[i]],crossover=[r for _,r in children[i]])
        if len(best)<len(initial):check(puzzles[i],best);wins[i]=best;z['program']=best
        rows.append(z)
    write_submission(a.out/'own.csv',[puzzles[i] for i in wins],wins)
    report=dict(base=BASE,contributor=CONTRIBUTOR,wins=len(wins),saved=sum(z['before']-z['after'] for z in rows),
                extra_after_cross=sum(z['first']-z['after'] for z in rows),rows=rows)
    pack(a.out/'results.json.gz',report)
    print(report['wins'],report['saved'],report['extra_after_cross'],flush=True)


if __name__=='__main__':
    main()