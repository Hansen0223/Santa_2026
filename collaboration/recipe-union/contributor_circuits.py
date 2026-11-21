"""Search alternate circuits exposed by the contributor's 25 newly available programs."""
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

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'collaboration/cross-puzzle-templates'))
sys.path.insert(0,str(ROOT/'generative/wang'))
from selector import compile_selection
from replay_search import encode
from elf import read_puzzles,write_submission,check
from graph import active_graph,first_recipes

HEAD='b49db2f'
CONTRIBUTOR='0b893d9'
HISTORICAL=('6e68414','8bde969','138be6d','1fb2d8c')


def fetch(ref,name):
    data=subprocess.check_output(['git','show',ref+':'+name],cwd=ROOT)
    return {r['id']:r for r in csv.DictReader(io.StringIO(data.decode('utf-8-sig')))}


def sha(t):
    return hashlib.sha256(json.dumps(t,separators=(',',':')).encode()).hexdigest()


def solve(job):
    p,lane,parents,binary,rounds=job
    old=parents[0][0]
    graphs=[active_graph(p,first_recipes(p,tape)) for tape,_ in parents]
    stats,chosen=compile_selection(p,old,graphs[0],graphs[1:],True)
    mode='anneal_diverse'
    seed=1007009+int(p.id[-4:])
    seqs=[chosen]+[t for t,_ in parents if t!=chosen]
    raw=subprocess.run([str(binary)],input=encode(p,mode,rounds,seed,seqs),capture_output=True,text=True,check=True).stdout.split()
    evolved=tuple((raw[j],*map(int,raw[j+1:j+4])) for j in range(1,len(raw),4))
    if len(evolved)!=int(raw[0]) or len(raw)!=1+4*len(evolved):raise ValueError('truncated program')
    best=min((chosen,evolved),key=len)
    report=dict(id=p.id,lane=lane,before=len(old),selected=len(chosen),evolved=len(evolved),
                seed=seed,rounds=rounds,model=stats,parents=[dict(credit=c,sha256=sha(t),steps=len(t)) for t,c in parents])
    if len(best)<len(old):
        check(p,best);report['program']=best
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('puzzles','binary','out'):ap.add_argument('--'+k,type=Path,required=True)
    ap.add_argument('--jobs',type=int,default=4);ap.add_argument('--rounds',type=int,default=680)
    args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    ps={p.id:p for p in read_puzzles(args.puzzles)}
    source=fetch(CONTRIBUTOR,'collaboration/lacia-independent/2026-11-20/shorter.csv')
    def tables(pre):
        return [(r,fetch(r,pre+'submission.csv'),fetch(r,pre+'origins.csv')) for r in (HEAD,*HISTORICAL)]
    def convert(z):return tuple(map(tuple,json.loads(z['program'])))
    own=tables('');public=tables('public-assisted/')
    jobs=[]
    for i,row in sorted(source.items()):
        for lane,inputs in [('own',own),('public',public+own)]:
            parents=[]
            def add(t,credit):
                if not parents or (t not in [a for a,_ in parents] and len(t)<=len(parents[0][0])+30):parents.append((t,credit))
            for index,(ref,table,origins) in enumerate(inputs):
                ledger=origins[i]
                add(convert(table[i]),ref+' '+(ledger.get('upstream_source') or ledger['source']))
                if index==0:add(convert(row),'Hiyohane, independently generated in 0b893d9')
            # Keep the newest alternatives and one more distant historical circuit.
            parents=parents[:5]+(parents[-1:] if len(parents)>5 else [])
            jobs.append((ps[i],lane,parents,args.binary.resolve(),args.rounds))
    with ThreadPoolExecutor(args.jobs) as pool:results=list(pool.map(solve,jobs))
    summary={}
    for lane in ('own','public'):
        rows=[z for z in results if z['lane']==lane];wins={z['id']:z['program'] for z in rows if 'program' in z}
        write_submission(args.out/(lane+'.csv'),[ps[i] for i in sorted(wins)],wins)
        with (args.out/(lane+'.origins.csv')).open('w',encoding='utf8',newline='') as f:
            wr=csv.writer(f);wr.writerow(['id','upstream_source'])
            for z in rows:
                if 'program' in z:
                    wr.writerow([z['id'],'Wang Jakie; Hiyohane; '+'; '.join(a['credit'] for a in z['parents'])])
        summary[lane]=dict(wins={i:len(t) for i,t in wins.items()},saved=sum(z['before']-min(z['selected'],z['evolved']) for z in rows))
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(dict(base=HEAD,source=CONTRIBUTOR,results=results,summary=summary),separators=(',',':')).encode(),mtime=0))
    print(summary,flush=True)

if __name__=='__main__':
    main()
