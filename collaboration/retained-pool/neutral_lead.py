"""Switch the leading program with a neutral archive donor, holding all other search inputs fixed."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'public-assisted/pardheev'))
from combine import decode
from elf import read_puzzles, read_submission, write_submission
from graph import first_recipes
from generative.wang.replay_search import encode
import subprocess
from elf import check


def fingerprint(p,tape):
    return frozenset((v,op,*sorted((a,b))) if op in '+*' else (v,op,a,b)
                     for v,(op,a,b) in first_recipes(p,tape).items())


def solve(binary,p,parents,seed,rounds):
    words=subprocess.run([str(binary)],input=encode(p,'incremental',rounds,seed,parents),
                         text=True,capture_output=True,check=True).stdout.split()
    tape=tuple((words[j],*map(int,words[j+1:j+4])) for j in range(1,len(words),4))
    if len(words)!=1+4*len(tape) or check(p,tape)!=int(words[0]):
        raise ValueError(p.id)
    return tape


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for arg in ('puzzles','parent','archive','binary','out'):
        ap.add_argument('--'+arg,type=Path,required=True)
    ap.add_argument('--count',type=int,default=64)
    ap.add_argument('--offset',type=int,default=0)
    ap.add_argument('--rounds',type=int,default=800)
    ap.add_argument('--jobs',type=int,default=8)
    args=ap.parse_args()
    ps=read_puzzles(args.puzzles)
    parent=read_submission(args.parent)
    archive_hash=hashlib.sha256(args.archive.read_bytes()).hexdigest()
    with zipfile.ZipFile(args.archive) as archive:
        manifest=json.loads(archive.read('replay_132638_manifest.json'))
        keys=['local_neutral_archive.csv','ishan_v4_archive.csv','wang_archive.csv','lucifer19_132646.csv']
        expected={e['file']:e['sha256'] for e in manifest['public_inputs']+manifest['donor_inputs']}
        banks={}
        for key in keys:
            raw=archive.read(key)
            if hashlib.sha256(raw).hexdigest()!=expected[key]:
                raise ValueError(key)
            banks[key]=decode(raw)
    ranking=[]
    for p in ps:
        base=parent[p.id]
        if len(base)<35:
            continue
        g=fingerprint(p,base)
        offers=[]
        for k,bank in banks.items():
            t=bank[p.id]
            distance=len(g ^ fingerprint(p,t))
            if 0<=len(t)-len(base)<=5 and distance>=4:
                offers.append(((len(t)-len(base)+1)/(min(distance,75)**.5),k,t))
        if offers:
            priority,name,donor=min(offers)
            others=list(dict.fromkeys(banks[k][p.id] for k in keys if k!=name))
            parents=list(dict.fromkeys([base,donor,*others]))
            ranking.append((priority,p.id,p,name,parents))
    selected=sorted(ranking,key=lambda x:x[:2])[args.offset:args.offset+args.count]
    rows,wins={},{}
    def try_both(entry):
        _,i,p,name,parents=entry
        seed=336418+int(i[-4:])
        control=solve(args.binary,p,parents,seed,args.rounds)
        switched=solve(args.binary,p,[parents[1],parents[0],*parents[2:]],seed,args.rounds)
        return i,min([parents[0],control,switched],key=len),dict(donor=name,parent=len(parents[0]),
           alternate=len(parents[1]),control=len(control),switched=len(switched))
    with ThreadPoolExecutor(args.jobs) as pool:
        for i,t,record in pool.map(try_both,selected):
            rows[i]=record
            if len(t)<len(parent[i]):wins[i]=t
    args.out.mkdir(parents=True,exist_ok=True)
    write_submission(args.out/'wins.csv',[p for p in ps if p.id in wins],wins)
    j=dict(parent_sha256=hashlib.sha256(args.parent.read_bytes()).hexdigest(),archive_sha256=archive_hash,
           eligible=len(ranking),offset=args.offset,rounds=args.rounds,rows=rows)
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(j,separators=(',',':')).encode(),mtime=0))
    print(len(rows),len(wins),sum(len(parent[i])-len(t) for i,t in wins.items()))


if __name__=='__main__':
    main()
