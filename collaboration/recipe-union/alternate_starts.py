"""Start local search from structurally different historical circuits, then compare to the current best."""
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
sys.path.insert(0,str(ROOT/'generative/wang'))
from elf import check,read_puzzles,write_submission
from graph import first_recipes
from replay_search import encode

BASE='95f3008'
SOURCES=('work/virtual/fresh-full.csv','work/gen/atlas-continued.csv','work/gen/konbu-fresh.csv',
         'work/gen/atlas-expanded.csv','work/virtual/current-priced.csv','work/virtual/matrix-mid-raw.csv',
         'work/gen/arsen-fresh.csv','work/gen/best-generated.csv','work/cones/independent.csv',
         'work/virtual/powers-full.csv','work/gen/fresh-current.csv','work/gen/atakan-frontier-full.csv',
         'work/cones/fresh-relations.csv','work/creative/matrix-program-independent.csv',
         'work/virtual/matrix-graft-independent.csv','work/creative/matrix-prepay-fresh.csv','work/gen/konbu-complete.csv')


def frozen(path):
    data=subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT)
    return {r['id']:r for r in csv.DictReader(io.StringIO(data.decode('utf-8-sig')))}


def as_tape(row):
    return tuple(map(tuple,json.loads(row['program'])))


def pack(path,data):
    raw=(json.dumps(data,separators=(',',':'))+'\n').encode()
    path.write_bytes(gzip.compress(raw,mtime=0) if path.suffix=='.gz' else raw)


def load(path):
    data=path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix=='.gz' else data)


def fingerprint(tape):
    return hashlib.sha256(json.dumps(tape,separators=(',',':')).encode()).hexdigest()


def prepare(puzzles,directory,out):
    current={i:as_tape(row) for i,row in frozen('submission.csv').items()}
    candidates={i:{} for i in current}
    hashes={}
    for name in SOURCES:
        f=directory/name
        if not f.exists():continue
        hashes[name]=hashlib.sha256(f.read_bytes()).hexdigest()
        with f.open(encoding='utf-8-sig',newline='') as stream:
            for row in csv.DictReader(stream):
                i=row['id'];t=as_tape(row)
                if t!=current[i] and len(t)<=len(current[i])+24:
                    candidates[i].setdefault(t,name)
    entries=[]
    for p in puzzles:
        incumbent=current[p.id]
        current_graph=set(first_recipes(p,incumbent).items())
        options=[]
        for t,name in candidates[p.id].items():
            other=set(first_recipes(p,t).items())
            difference=len(other-current_graph)/max(1,len(other))
            if difference<.035:continue
            price=len(t)-len(incumbent)
            priority=difference/(3+max(0,price))**.7
            options.append((priority,name,t,other))
        if not options:continue
        options.sort(key=lambda v:(-v[0],len(v[2]),v[1]))
        first=options[0]
        selected=[first]
        if len(options)>1:
            others=[v for v in options[1:] if len(v[3]-first[3])>=4]
            if others:selected.append(max(others,key=lambda v:v[0]*len(v[3]-first[3])/len(v[3])))
        parents=[dict(source=name,program=t,sha256=fingerprint(t)) for _,name,t,_ in selected]
        entries.append(dict(id=p.id,priority=round(first[0],7),parents=parents))
    # Test the highest ranked third along with a reproducible sample of the rest.
    entries.sort(key=lambda v:(-v['priority'],v['id']))
    top_n=min(24,len(entries)//3)
    high=entries[:top_n];others=entries[top_n:]
    random_order=sorted(others,key=lambda v:hashlib.sha256(('old-basin-1'+v['id']).encode()).digest())
    pilot=high+random_order[:24];seen={v['id'] for v in pilot}
    ordered=pilot+[v for v in entries if v['id'] not in seen]
    pack(out/'donors.json.gz',dict(base=BASE,sources=hashes,entries=ordered))
    pack(out/'design.json',dict(base=BASE,sources=hashes,eligible=len(entries),pilot=[v['id'] for v in pilot],order=[v['id'] for v in ordered]))
    print('circuits with different recipes',len(entries),'pilot',len(pilot),flush=True)


def search(job):
    p,lane,tape,credit,donors,binary,rounds=job
    alternatives=[tuple(map(tuple,z['program'])) for z in donors]
    seed=1207003+int(p.id[-4:])
    mode=binary.stem
    best=tape;arms={}
    for name,group in [('current-first',[tape,*alternatives]),('alternative-first',[alternatives[0],tape,*alternatives[1:]])]:
        group=list(dict.fromkeys(group))
        if name=='alternative-first' and tape==alternatives[0]:
            arms[name]=arms['current-first'];continue
        result=subprocess.run([str(binary)],input=encode(p,mode,rounds,seed,group),
                              text=True,capture_output=True,check=True)
        fields=result.stdout.split();n=int(fields[0])
        if len(fields)!=1+n*4:raise ValueError('truncated program')
        candidate=tuple((fields[k],*map(int,fields[k+1:k+4])) for k in range(1,len(fields),4))
        arms[name]=len(candidate)
        if len(candidate)<len(best):
            check(p,candidate);best=candidate
    row=dict(id=p.id,lane=lane,before=len(tape),after=len(best),arms=arms,seed=seed,rounds=rounds,
             parent_sha256=fingerprint(tape),upstream_source=credit,donors=[z['sha256'] for z in donors])
    if len(best)<len(tape):row['program']=best
    return row


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--puzzles',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--prepare-from',type=Path);ap.add_argument('--binary',type=Path)
    ap.add_argument('--block',type=int,default=0);ap.add_argument('--jobs',type=int,default=6)
    ap.add_argument('--rounds',type=int,default=360);ap.add_argument('--lane',choices=('own','public','both'),default='both')
    a=ap.parse_args();a.out.mkdir(exist_ok=True,parents=True)
    puzzles=read_puzzles(a.puzzles);pm={p.id:p for p in puzzles}
    if a.prepare_from:
        prepare(puzzles,a.prepare_from,a.out)
        return
    if not a.binary:ap.error('--binary required for search')
    entries=load(a.out/'donors.json.gz')['entries'][48*a.block:48*(a.block+1)]
    if not entries:ap.error('block outside the allocated range')
    lanes=('own','public') if a.lane=='both' else (a.lane,)
    for lane in lanes:
        pre='public-assisted/' if lane=='public' else ''
        base=frozen(pre+'submission.csv');credits=frozen(pre+'origins.csv')
        stem=f'{lane}-{a.block:02d}';record=a.out/(stem+'.json.gz')
        if record.is_file():results=load(record)
        else:
            jobs=[]
            for v in entries:
                i=v['id'];parent=as_tape(base[i]);credit=credits[i].get('upstream_source') or 'Generated from official inputs'
                jobs.append((pm[i],lane,parent,credit,v['parents'],a.binary.resolve(),a.rounds))
            with ThreadPoolExecutor(a.jobs) as pool:results=list(pool.map(search,jobs))
            pack(record,results)
        wins={z['id']:z['program'] for z in results if 'program' in z}
        write_submission(a.out/(stem+'.csv'),[pm[i] for i in sorted(wins)],wins)
        with (a.out/(stem+'.origins.csv')).open('w',encoding='utf8',newline='') as stream:
            wr=csv.writer(stream);wr.writerow(['id','upstream_source'])
            wr.writerows((z['id'],'Wang Jakie; independently generated historical alternatives; '+z['upstream_source']) for z in results if z['id'] in wins)
        summary=dict(tested=len(results),wins=len(wins),saved=sum(z['before']-z['after'] for z in results),extra_from_alternative_first=sum(max(0,min(z['before'],z['arms']['current-first'])-z['after']) for z in results))
        pack(a.out/(stem+'.json'),summary)
        print(stem,summary,flush=True)


if __name__=='__main__':
    main()
