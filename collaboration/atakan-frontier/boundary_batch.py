"""Test Atakan's joint-interface and external-alias searches on matched puzzles."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from elf import check, read_puzzles, read_submission, write_submission


def run(p, parent, binary, seed, millis):
    goals=sorted(set(p.targets))
    header=[f'{p.id} {p.limit} {len(p.seeds)} {len(goals)} {len(parent)}',
            ' '.join(map(str,p.seeds)), ' '.join(map(str,goals))]
    payload='\n'.join(header+[' '.join(map(str,op)) for op in parent])+'\n'
    commands=[str(binary.resolve()),'60','24','2',str(seed),str(millis)]
    lines=subprocess.run(commands,input=payload,text=True,capture_output=True,check=True).stdout.splitlines()
    key, size, *meters=lines[0].split()
    tape=tuple((op,int(a),int(b),int(c)) for op,a,b,c in (line.split() for line in lines[1:]))
    if key!=p.id or check(p,tape)!=int(size) or len(tape)>len(parent):
        raise ValueError(f'Invalid result on {p.id}')
    return tape,list(map(int,meters))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for arg in ('puzzles','parent','bin-dir','out'):
        ap.add_argument('--'+arg,required=True,type=Path)
    ap.add_argument('--count',type=int,default=48)
    ap.add_argument('--offset',type=int,default=0)
    ap.add_argument('--millis',type=int,default=600)
    ap.add_argument('--jobs',type=int,default=8)
    args=ap.parse_args()
    ps=read_puzzles(args.puzzles)
    parent_hash=hashlib.sha256(args.parent.read_bytes()).hexdigest()
    parent=read_submission(args.parent)
    modes=['elf_joint_interfaces','elf_outside_alias']
    group=sorted((p for p in ps if 65<=len(parent[p.id]) and len(set(p.targets))<=63),
                 key=lambda p:hashlib.sha256(('interface40-'+p.id).encode()).digest())
    group=group[args.offset:args.offset+args.count]
    wins,records={},{}
    with ThreadPoolExecutor(args.jobs) as pool:
        futures=[(p,m,pool.submit(run,p,parent[p.id],args.bin_dir/(m+('.exe' if sys.platform=='win32' else '')),
                                  282115+int(p.id[-4:]),args.millis)) for p in group for m in modes]
        for p,m,f in futures:
            t,meters=f.result()
            records.setdefault(p.id,{'before':len(parent[p.id])})[m]={'length':len(t),'meters':meters}
            if len(t)<len(wins.get(p.id,parent[p.id])):
                wins[p.id]=t
    args.out.mkdir(parents=True,exist_ok=True)
    write_submission(args.out/'wins.csv',[p for p in ps if p.id in wins],wins)
    j=dict(parent_sha256=parent_hash,millis=args.millis,settings=[60,24,2],seed_offset=282115,rows=records)
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(j,separators=(',',':')).encode(),mtime=0))
    print(len(records),len(wins),sum(len(parent[i])-len(t) for i,t in wins.items()))


if __name__=='__main__':
    main()
