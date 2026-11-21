"""Search distinct high-quality source circuits against the corresponding independent and public programs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from combine import ROOT, BASE, baseline, donor
from elf import check, read_puzzles, write_submission
from graph import first_recipes

sys.path.insert(0, str(ROOT/'generative/wang'))
from replay_search import encode


def fingerprint(program):
    return hashlib.sha256(json.dumps(program,separators=(',',':')).encode()).hexdigest()


def selection(puzzles, local, external):
    ranked = []
    for p in puzzles:
        current, alternate = local[p.id], external[p.id]
        if len(alternate)>len(current)+3 or not 65<=len(alternate)<=275:
            continue
        graph = set(first_recipes(p,alternate).items())
        difference = len(graph-set(first_recipes(p,current).items()))/max(1,len(graph))
        if difference < 0.22:
            continue
        tie = hashlib.sha256(('pardheev-graph-search-1'+p.id).encode()).hexdigest()
        ranked.append((p.id,difference,len(current)-len(alternate),tie))
    ranked.sort(key=lambda z:(-z[2],-z[1],z[3]))
    top = ranked[:32]
    rest = sorted(ranked[32:],key=lambda z:z[3])
    return top+rest


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('puzzles','archive','binary','out'):ap.add_argument('--'+key,type=Path,required=True)
    ap.add_argument('--offset',type=int,default=0);ap.add_argument('--count',type=int,default=80)
    ap.add_argument('--jobs',type=int,default=6);ap.add_argument('--rounds',type=int,default=700)
    a=ap.parse_args(); a.out.mkdir(exist_ok=True,parents=True)
    puzzles=read_puzzles(a.puzzles);pm={p.id:p for p in puzzles}
    own=baseline('submission.csv');local=baseline('public-assisted/submission.csv');other=donor(a.archive)
    entries=selection(puzzles,local,other)
    if a.offset<0 or a.count<1 or a.offset>=len(entries):ap.error('empty or invalid range')
    batch=entries[a.offset:a.offset+a.count];ids=[z[0] for z in batch]
    design=dict(base=BASE,eligible=len(entries),ids=ids,offset=a.offset,rounds=a.rounds,
                engine_sha256=hashlib.sha256(a.binary.read_bytes()).hexdigest())
    (a.out/'design.json').write_text(json.dumps(design,indent=2)+'\n',encoding='utf8')

    def solve(i):
        p=pm[i];parents=list(dict.fromkeys(sorted((other[i],local[i],own[i]),key=len)))
        before=len(parents[0]);seed=247043+int(i[-4:])
        output=subprocess.run([str(a.binary.resolve())],input=encode(p,'anneal_diverse',a.rounds,seed,parents),
                              text=True,capture_output=True,check=True).stdout.split()
        n=int(output[0])
        if len(output)!=1+4*n:raise ValueError('incomplete result')
        program=tuple((output[j],*map(int,output[j+1:j+4])) for j in range(1,len(output),4))
        if n<before:check(p,program)
        return dict(id=i,seed=seed,before=before,after=min(before,n),digest=fingerprint(program) if n<before else None),program if n<before else None

    with ThreadPoolExecutor(a.jobs) as pool:results=list(pool.map(solve,ids))
    receipts=[r for r,_ in results]
    wins={r['id']:t for r,t in results if t is not None}
    write_submission(a.out/'search-wins.csv',[pm[i] for i in sorted(wins)],wins)
    summary=dict(design=design,wins=len(wins),saved=sum(z['before']-z['after'] for z in receipts),rows=receipts)
    (a.out/'search-results.json.gz').write_bytes(gzip.compress(json.dumps(summary,separators=(',',':')).encode(),mtime=0))
    print(summary['wins'],summary['saved'],flush=True)


if __name__=='__main__':
    main()