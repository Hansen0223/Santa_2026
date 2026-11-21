"""Measure whether predicted factors occur in independent contributor programs."""
import argparse
from collections import Counter
import csv
import gzip
import io
import json
from pathlib import Path
import random
import subprocess
import zipfile
from residue_bridges import ROOT, ranked_scales, read_puzzles, sha256
from graph import first_recipes

REVISION='0b893d93056bdaf53c7e538e2e78bb005f3ab2f7'
SOURCE='collaboration/lacia-independent/2026-11-20/shorter.csv'


def programs(raw):
    return {r['id']:tuple(map(tuple,json.loads(r['program']))) for r in csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))}


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ('puzzles','archive','out'):
        cli.add_argument('--'+name,required=True,type=Path)
    args=cli.parse_args()
    ps={p.id:p for p in read_puzzles(args.puzzles)}
    with zipfile.ZipFile(args.archive) as z:
        public=programs(z.read('submission.csv'))
    contributors=programs(subprocess.check_output(['git','show',REVISION+':'+SOURCE],cwd=ROOT))
    rows={}
    for i,t in contributors.items():
        p=ps[i]
        actual=first_recipes(p,t)
        reference=first_recipes(p,public[i])
        uses=Counter(x for _,a,b in actual.values() for x in {a,b})
        relevant={x for x,c in uses.items() if c>=3 and 200<=x<=2_000_000 and x not in reference and x not in p.targets}
        if not relevant:
            continue
        rng=random.Random(7811+int(i[-4:]))
        ts=sorted(set(p.targets)-set(p.seeds))
        arms={}
        for name,targets in [('real',ts),('perturbed',[max(1,x+rng.randint(-3000,3000)) for x in ts])]:
            ranks=ranked_scales(targets,reference,p.seeds)
            hits=[(j+1,h) for j,(_,h) in enumerate(ranks) if h in relevant]
            arms[name]=dict(first_hits=hits[:8],proposed=len(ranks))
        rows[i]=dict(reference_count=len(relevant),arms=arms)
    result=dict(revision=REVISION,source=SOURCE,reference_sha256=sha256(args.archive),rows=rows)
    args.out.write_bytes(gzip.compress(json.dumps(result,separators=(',',':')).encode(),mtime=0))
    for mode in ('real','perturbed'):
        print(mode,{n:sum(any(j<=n for j,_ in x['arms'][mode]['first_hits']) for x in rows.values()) for n in (8,24,64)})


if __name__=='__main__':
    main()
