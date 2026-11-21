"""Compare the same crossover with and without reflection values on a frozen puzzle list."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from elf import check, read_puzzles, read_submission, sha256, write_submission
from generative.wang.replay_search import encode


def execute(exe, p, parent, centers):
    result = []
    for mode in (0, 1):
        lines = encode(p, 'anneal', centers, 655487 + int(p.id[-4:]), [parent]).splitlines()
        header = lines[1].split()
        header[3] = str(mode)
        lines[1] = ' '.join(header)
        words = subprocess.run([str(exe)], input='\n'.join(lines)+'\n', capture_output=True,
                               text=True, check=True).stdout.split()
        tape = tuple((words[j], *map(int, words[j+1:j+4])) for j in range(1,len(words),4))
        if check(p,tape) != int(words[0]) or len(tape)>len(parent):
            raise ValueError(p.id)
        result.append(tape)
    return p.id, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('puzzles','parent','binary','out'):
        parser.add_argument('--'+flag, type=Path, required=True)
    parser.add_argument('--count',type=int,default=80)
    parser.add_argument('--centers',type=int,default=8)
    parser.add_argument('--jobs',type=int,default=8)
    args=parser.parse_args()
    puzzles=read_puzzles(args.puzzles)
    parent_hash=sha256(args.parent)
    bank=read_submission(args.parent)
    group=sorted((p for p in puzzles if len(bank[p.id])>=35),
                 key=lambda p:hashlib.sha256(('mirror-'+p.id).encode()).digest())[:args.count]
    wins={}
    results={}
    with ThreadPoolExecutor(args.jobs) as pool:
        jobs=[pool.submit(execute,args.binary.resolve(),p,bank[p.id],args.centers) for p in group]
        for job in jobs:
            i, tapes=job.result()
            results[i]=[len(bank[i]),*(len(t) for t in tapes)]
            t=min(tapes,key=len)
            if len(t)<len(bank[i]):wins[i]=t
    args.out.mkdir(parents=True,exist_ok=True)
    write_submission(args.out/'wins.csv',[p for p in puzzles if p.id in wins],wins)
    report=dict(parent_sha256=parent_hash,centers=args.centers,columns=['parent','control','reflected'],rows=results)
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(report,separators=(',',':')).encode(),mtime=0))
    print(len(results),sum(len(bank[i])-len(t) for i,t in wins.items()),sum(b<c for _,c,b in results.values()))


if __name__=='__main__':
    main()
