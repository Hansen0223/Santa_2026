"""Search for a constructible upper anchor shared by several target complements."""
import argparse
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'collaboration/cross-puzzle-templates'))
from elf import check, read_puzzles, write_submission
from graph import active_graph, first_recipes
from selector import compile_selection
from solvers.graphs.corpus_prefix import arithmetic_edges

BASE = 'aacd89c'


def archived(name):
    data = subprocess.check_output(['git','show',BASE+':public-assisted/'+name],cwd=ROOT)
    return {r['id']:r for r in csv.DictReader(io.StringIO(data.decode('utf-8-sig')))}


def anchor_routes(p, original):
    goals = set(p.targets) - set(p.seeds)
    core = set(original) | set(p.seeds)
    depend = {v:0 for v in p.seeds}
    targets = {v:1 << i for i,v in enumerate(sorted(goals))}
    for v, (_,a,b) in original.items():
        depend[v] = depend[a] | depend[b] | targets.get(v,0)
    use = Counter(v for r in original.values() for v in set(r[1:]))
    use.update(goals)
    removable = {}
    for v, (_,a,b) in original.items():
        removable[v] = 1 + sum(removable.get(u,0) for u in {a,b} if use[u] == 1)
    makers = {v:None for v in core}
    source_mask = dict(depend)
    # Prefer operands which depend on fewer of the targets being rebuilt.
    values = sorted(core,key=lambda v:(depend[v].bit_count(),-use[v],v))
    for i,a in enumerate(values):
        for b in values[:i+1]:
            mask = depend[a] | depend[b]
            for v,e in arithmetic_edges(a,b,p.limit):
                if v not in makers or (v not in core and mask.bit_count()<source_mask[v].bit_count()):
                    makers[v] = e
                    source_mask[v] = mask
    units = sorted(v for v in core if 2<=v<=16)
    upper = sorted((v for v in makers if max(goals)//4<v<=p.limit))
    routes = []
    for anchor in upper:
        choices = []
        for t in goals:
            remainder = anchor-t
            if remainder<=0 or (source_mask[anchor]&targets[t]) or removable.get(t,1)<2:
                continue
            patch = {}
            if makers[anchor] is not None:
                patch[anchor] = makers[anchor]
            if remainder in makers and not source_mask[remainder]&targets[t]:
                if makers[remainder] is not None:
                    patch[remainder] = makers[remainder]
            else:
                eligible = []
                for k in units:
                    q, r = divmod(remainder,k)
                    if r or q==t or q not in makers or source_mask[q]&targets[t] or depend[k]&targets[t]:
                        continue
                    eligible.append((q not in core,k,q))
                if not eligible:
                    continue
                _,k,q = min(eligible)
                if makers[q] is not None:
                    patch[q] = makers[q]
                patch[remainder] = ('*',k,q)
            patch[t] = ('-',anchor,remainder)
            if any(v in e[1:] for v,e in patch.items()):
                continue
            choices.append((removable[t],patch))
        if len(choices)>=2:
            estimates = [cost - len(path) + int(anchor not in core) for cost,path in choices]
            gain = sum(max(0,x) for x in estimates) - int(anchor not in core)
            routes.append((gain,len(choices),anchor,choices))
    passed = sorted(routes,key=lambda x:(-x[0],-x[1],x[2]))[:8]
    return [patch for _,_,_,choices in passed for _,patch in choices], [(a,len(c),g) for g,_,a,c in passed]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--puzzles',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--limit',type=int,default=32)
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    programs,credits = archived('submission.csv'),archived('origins.csv')
    puzzles = read_puzzles(args.puzzles)
    eligible = [p for p in puzzles if 26<=len(p.targets)<=34 and p.limit*2 < 3*max(p.targets)]
    rows = sorted(eligible,key=lambda p:hashlib.sha256(('ceiling-anchor-1'+p.id).encode()).digest())[:args.limit]
    wins = {};report = {}
    for p in rows:
        tape = tuple(map(tuple,json.loads(programs[p.id]['program'])))
        graph = active_graph(p,first_recipes(p,tape))
        paths,anchors = anchor_routes(p,graph)
        if paths:
            stats,best = compile_selection(p,tape,graph,paths,False)
        else:
            stats,best = {},tape
        report[p.id] = dict(before=len(tape),after=len(best),anchors=anchors,choices=len(paths),solver=stats)
        if len(best)<len(tape):
            assert check(p,best)==len(best)
            wins[p.id]=best
            print(p.id,len(tape),len(best),flush=True)
    write_submission(args.output/'wins.csv',[p for p in rows if p.id in wins],wins)
    with (args.output/'origins.csv').open('w',encoding='utf8',newline='') as file:
        out=csv.writer(file);out.writerow(['id','upstream_source'])
        out.writerows((i,credits[i]['upstream_source']) for i in sorted(wins))
    payload=dict(base=BASE,eligible=len(eligible),rows=report)
    (args.output/'results.json.gz').write_bytes(gzip.compress(json.dumps(payload,separators=(',',':')).encode(),mtime=0))
    print('cases',len(rows),'joint candidates',sum(bool(r['anchors']) for r in report.values()),'saved',sum(r['before']-r['after'] for r in report.values()),flush=True)


if __name__=='__main__':
    main()
