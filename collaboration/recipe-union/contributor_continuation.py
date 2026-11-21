"""Continue independent and public donor searches with two native graph neighborhoods."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import gzip
import json
from pathlib import Path
import subprocess
from contributor_circuits import ROOT, fetch, sha, encode, read_puzzles, write_submission, check, CONTRIBUTOR

BASE='95f3008'


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('puzzles','binaries','out'):ap.add_argument('--'+key,type=Path,required=True)
    ap.add_argument('--jobs',type=int,default=5);ap.add_argument('--rounds',type=int,default=1600)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    ps={p.id:p for p in read_puzzles(a.puzzles)}
    archive=fetch(CONTRIBUTOR,'collaboration/lacia-independent/2026-11-20/shorter.csv')
    rows={};credits={}
    for rev in (BASE,'b49db2f','6e68414','8bde969'):
        for lane,pre in [('own',''),('public','public-assisted/')]:
            rows[rev,lane]=fetch(rev,pre+'submission.csv');credits[rev,lane]=fetch(rev,pre+'origins.csv')
    jobs=[]
    for i,z in archive.items():
        external=tuple(map(tuple,json.loads(z['program'])))
        for lane in ('own','public'):
            def from_ref(rev,source):
                tape=tuple(map(tuple,json.loads(rows[rev,source][i]['program'])))
                ledger=credits[rev,source][i];credit=ledger.get('upstream_source') or 'Generated from official inputs'
                return tape,rev+'/'+source+' '+credit
            first=from_ref(BASE,lane);teammate=(external,'Hiyohane, 0b893d9')
            inputs=[first,teammate,from_ref(BASE,'own'),from_ref('b49db2f',lane),from_ref('6e68414',lane),from_ref('8bde969',lane)]
            for index,mode in enumerate(('incremental_diverse','anneal_diverse')):
                ordered=inputs[:] if index==0 else [teammate,first,*inputs[2:]]
                distinct={}
                for tape,credit in ordered:distinct.setdefault(tape,credit)
                jobs.append((i,lane,mode,list(distinct.items()),len(first[0]),146851+int(i[-4:])+4099*index))
    def run(job):
        i,lane,mode,parents,before,seed=job
        exe=a.binaries/(mode+('.exe' if (a.binaries/(mode+'.exe')).exists() else ''))
        raw=subprocess.run([str(exe.resolve())],input=encode(ps[i],mode,a.rounds,seed,[t for t,_ in parents]),capture_output=True,text=True,check=True).stdout.split()
        n=int(raw[0]);t=tuple((raw[j],*map(int,raw[j+1:j+4])) for j in range(1,len(raw),4))
        if len(t)!=n or len(raw)!=1+n*4:raise ValueError('truncated program')
        z=dict(id=i,lane=lane,mode=mode,seed=seed,rounds=a.rounds,before=before,after=n,parents=[dict(sha256=sha(p),credit=c) for p,c in parents])
        if n<before:check(ps[i],t);z['program']=t
        return z
    with ThreadPoolExecutor(a.jobs) as pool:results=list(pool.map(run,jobs))
    summary={}
    for lane in ('own','public'):
        wins={}
        for z in results:
            i=z['id']
            if z['lane']==lane and 'program' in z and (i not in wins or z['after']<wins[i]['after']):wins[i]=z
        write_submission(a.out/(lane+'.csv'),[ps[i] for i in sorted(wins)],{i:z['program'] for i,z in wins.items()})
        with (a.out/(lane+'.origins.csv')).open('w',encoding='utf8',newline='') as f:
            wr=csv.writer(f);wr.writerow(['id','upstream_source'])
            wr.writerows((i,'Wang Jakie; Hiyohane; '+'; '.join(x['credit'] for x in z['parents'])) for i,z in sorted(wins.items()))
        summary[lane]=dict(saved=sum(z['before']-z['after'] for z in wins.values()),wins={i:z['after'] for i,z in wins.items()})
    (a.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(dict(base=BASE,results=results,summary=summary),separators=(',',':')).encode(),mtime=0))
    print(summary,flush=True)

if __name__=='__main__':
    main()
