"""Search distinct, near-tied independent and assisted programs before crossing the two starts."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import json
from pathlib import Path
import sys

from donor_masks import read_puzzles,read_submission,search,sha256,write_submission
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'collaboration/retained-pool'))
from neutral_lead import solve
from graph import active_graph,first_recipes


def work(job):
    p,own,front,distance,native,wang,seconds,rounds=job
    seed=317467+int(p.id[-4:])
    independent=search(native,p,own,[],seconds,317467,False)
    incumbent=search(native,p,front,[],seconds,317467,False)
    parents=[independent,incumbent]
    hybrids=[solve(wang,p,parents,seed,rounds),solve(wang,p,parents[::-1],seed,rounds)]
    seen={independent,incumbent}
    crossed=[]
    for candidate in sorted(hybrids,key=len):
        if candidate not in seen and len(candidate)<=len(front)+1:
            seen.add(candidate)
            crossed.append(search(native,p,candidate,[],max(1,seconds//2),953411,True))
    options=[('independent',independent),('frontier',incumbent),('own-first',hybrids[0]),('front-first',hybrids[1])]
    options.extend(('polished-cross',t) for t in crossed)
    label,best=min(options,key=lambda v:len(v[1]))
    return p.id,independent,best,dict(own=len(own),front=len(front),distance=round(distance,5),
        independent=len(independent),incumbent=len(incumbent),hybrids=list(map(len,hybrids)),
        polished=list(map(len,crossed)),best=len(best),winner=label)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('puzzles','own','front','native','wang','out'):
        ap.add_argument('--'+k,type=Path,required=True)
    for k,v in [('jobs',12),('seconds',8),('rounds',1200),('gap',2)]:
        ap.add_argument('--'+k,type=int,default=v)
    a=ap.parse_args();ps=read_puzzles(a.puzzles)
    own,front=read_submission(a.own),read_submission(a.front)
    jobs=[]
    for p in ps:
        x,y=own[p.id],front[p.id]
        if x==y or len(y)<28 or not 0<=len(x)-len(y)<=a.gap:
            continue
        A=set(active_graph(p,first_recipes(p,x)))-set(p.targets)
        B=set(active_graph(p,first_recipes(p,y)))-set(p.targets)
        distance=len(A^B)/max(1,len(A|B))
        if distance>=0.20:
            jobs.append((p,x,y,distance,a.native,a.wang,a.seconds,a.rounds))
    rows,own_wins,mixed_wins={},{},{}
    with ThreadPoolExecutor(a.jobs) as ex:
        for i,x,y,r in ex.map(work,jobs):
            rows[i]=r
            if len(x)<len(own[i]):
                own_wins[i]=x
            if len(y)<len(front[i]) and y!=x:
                mixed_wins[i]=y
    a.out.mkdir(exist_ok=True,parents=True)
    for tag,bank in [('independent',own_wins),('assisted',mixed_wins)]:
        write_submission(a.out/(tag+'.csv'),[p for p in ps if p.id in bank],bank)
    info=dict(rows=rows,inputs={k:sha256(getattr(a,k)) for k in ('puzzles','own','front','native','wang')},
              settings={k:v for k,v in vars(a).items() if isinstance(v,int)})
    (a.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(info,separators=(',',':')).encode(),mtime=0))
    print(len(rows),len(own_wins),len(mixed_wins),sum(r['front']-r['best'] for r in rows.values()))


if __name__=='__main__':
    main()
