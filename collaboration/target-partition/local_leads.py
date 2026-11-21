"""Search puzzles where a repository program strictly improves a fixed public reference."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import json
from pathlib import Path

from donor_masks import read_puzzles,read_submission,search,sha256,write_submission


def work(task):
    p,label,parent,exe,seconds = task
    best = parent
    runs = []
    for offset in (441113,607619):
        for helpers in (False,True):
            tape = search(exe,p,parent,[],seconds,offset,helpers)
            runs.append(dict(seed=offset+int(p.id[-4:]),helpers=helpers,steps=len(tape)))
            if len(tape)<len(best):
                best=tape
    return p.id,label,best,dict(before=len(parent),after=len(best),runs=runs)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('puzzles','own','assisted','frontier','reference','exe','out'):
        ap.add_argument('--'+k,required=True,type=Path)
    ap.add_argument('--jobs',type=int,default=12)
    ap.add_argument('--seconds',type=int,default=16)
    args=ap.parse_args()
    ps=read_puzzles(args.puzzles)
    sources={k:read_submission(getattr(args,k)) for k in ('own','assisted','frontier','reference')}
    jobs=[]
    for p in ps:
        i=p.id
        own,assisted,front,reference=(sources[k][i] for k in ('own','assisted','frontier','reference'))
        if front!=assisted or len(front)>=len(reference):
            continue
        if len(own)<=len(front)+2:
            jobs.append((p,'independent',own,args.exe,args.seconds))
        if assisted!=own:
            jobs.append((p,'assisted',assisted,args.exe,args.seconds))
    wins={'independent':{},'assisted':{}}
    rows={}
    with ThreadPoolExecutor(args.jobs) as pool:
        for i,label,t,row in pool.map(work,jobs):
            rows.setdefault(i,{})[label]=row
            if row['after']<row['before']:
                wins[label][i]=t
    args.out.mkdir(exist_ok=True,parents=True)
    for label,bank in wins.items():
        write_submission(args.out/(label+'.csv'),[p for p in ps if p.id in bank],bank)
    report=dict(inputs={k:sha256(getattr(args,k)) for k in (*sources,'exe')},rows=rows,seconds=args.seconds,jobs=args.jobs)
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(report,separators=(',',':')).encode(),mtime=0))
    print(len(rows),len(jobs),{lane:len(bank) for lane,bank in wins.items()})


if __name__=='__main__':
    main()
