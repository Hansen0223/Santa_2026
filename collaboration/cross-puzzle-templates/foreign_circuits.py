"""Transfer grounded arithmetic fragments from other puzzles that share actual intermediate values."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
from math import log2
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'collaboration/retained-pool'))
sys.path.insert(0,str(ROOT/'collaboration/structure-controls/ruler'))
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, compile_graph, first_recipes
from neutral_lead import solve
from selector import compile_selection
from solvers.gpu.pooled_joins import inverse


def canonical(r):
    op,a,b = r
    return (op,min(a,b),max(a,b)) if op in '+*' else r


def choose_donors(puzzles, graphs, count):
    index = defaultdict(list)
    for p in puzzles:
        for v in graphs[p.id]:
            index[v].append(p.id)
    donors = {}
    for p in puzzles:
        rank = Counter()
        graph = graphs[p.id]
        goals = set(p.targets)
        uses = Counter(x for _,a,b in graph.values() for x in {a,b})
        for v in graph:
            ids = index[v]
            if not 1<len(ids)<=len(puzzles)//3:
                continue
            weight = (1+log2(len(puzzles)/len(ids))) * (1+min(uses[v],4)+2*(v in goals))
            for i in ids:
                if i!=p.id:
                    rank[i] += weight
        donors[p.id] = [i for i,_ in sorted(rank.items(),key=lambda e:(-e[1],e[0]))[:count]]
    return donors


def offers(p,base,donors):
    known = set(p.seeds) | base.keys()
    goals = set(p.targets)
    all_plans = []
    for name,donor in donors:
        price = {v:{} for v in known}
        # Donor seeds absent from the recipient may themselves be cheap to build.
        roots = {x for _,a,b in donor.values() for x in (a,b) if x not in donor and x not in known}
        for value in sorted(roots):
            if value>p.limit:
                continue
            for a in sorted(known):
                match = next((r for b,r in inverse(value,a,p.limit) if b in known and value not in r[1:]),None)
                if match is not None:
                    price[value] = {value:match}
                    break
        for v,recipe in donor.items():
            op,a,b = recipe
            if v>p.limit or a not in price or b not in price:
                continue
            if a>p.limit or b>p.limit:
                continue
            plan = price[a] | price[b] | {v:recipe}
            if len(plan)>9:
                continue
            if v not in known:
                price[v] = plan
                continue
            if v not in base or canonical(base[v])==canonical(recipe):
                continue
            try:
                live = active_graph(p,base|plan)
            except (KeyError,ValueError):
                continue
            edits = {u:r for u,r in plan.items() if u in live and (u not in base or canonical(base[u])!=canonical(r))}
            if v in edits and len(live)<=len(base)+3:
                all_plans.append((len(live)-len(base),v not in goals,name,v,edits))
    records = sorted(all_plans,key=lambda x:(x[:2],-len(x[4]),x[2:4]))
    selected = []
    seen = set()
    for cost,_,name,v,plan in records:
        key = frozenset((u,canonical(r)) for u,r in plan.items())
        if key not in seen:
            selected.append((cost,name,v,plan))
            seen.add(key)
            if len(selected)==60:
                break
    return selected


def work(task):
    p,tape,base,donors,engine,rounds = task
    choices = offers(p,base,donors)
    row = dict(before=len(tape),donors=[name for name,_ in donors],fragments=len(choices))
    best = tape
    if choices:
        seed = 381641 + int(p.id[-4:])
        control = solve(engine,p,[tape],seed,rounds)
        best = min((best,control),key=len)
        new = set()
        for _,_,_,branch in choices:
            new.update(branch.keys()-base.keys())
        row.update(control=len(control),foreign_values=len(new))
        stats,joined = compile_selection(p,tape,base,[q[3] for q in choices],False)
        starts = []
        relevant = []
        for loss,name,root,patch in choices:
            if relevant and (loss>2 or len(relevant)>=2):
                break
            if root in {v for n,v in relevant}:
                continue
            candidate = compile_graph(p,base|patch,attempts=3)
            if candidate is not None and len(candidate)<=len(tape)+2 and candidate!=tape:
                starts.append(candidate)
                relevant.append((name,root))
        if joined!=tape:
            starts.insert(0,joined)
        row.update(selected=stats['physical'],warm_starts=relevant,polished=[])
        for t in starts:
            it = solve(engine,p,[t],seed,rounds)
            row['polished'].append([len(t),len(it)])
            best = min((best,t,it),key=len)
    check(p,best)
    row['final'] = len(best)
    return p.id,best,row


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for key in ('puzzles','parent','engine','out'):
        ap.add_argument('--'+key,type=Path,required=True)
    for key,n in [('count',80),('offset',0),('jobs',6),('donors',12),('rounds',460)]:
        ap.add_argument('--'+key,type=int,default=n)
    args=ap.parse_args()
    ps = read_puzzles(args.puzzles)
    bank = read_submission(args.parent)
    graphs = {p.id:active_graph(p,first_recipes(p,bank[p.id])) for p in ps}
    donors = choose_donors(ps,graphs,args.donors)
    eligible = sorted((p for p in ps if len(bank[p.id])>=25 and donors[p.id]),
                      key=lambda p:hashlib.sha256(('foreign-ground1-'+p.id).encode()).digest())
    group = eligible[args.offset:args.offset+args.count]
    tasks = [(p,bank[p.id],graphs[p.id],[(i,graphs[i]) for i in donors[p.id]],args.engine,args.rounds) for p in group]
    rows,wins = {},{}
    with ProcessPoolExecutor(args.jobs) as ex:
        for i,t,row in ex.map(work,tasks):
            rows[i]=row
            if len(t)<len(bank[i]):
                wins[i]=t
    args.out.mkdir(exist_ok=True,parents=True)
    write_submission(args.out/'wins.csv',[p for p in ps if p.id in wins],wins)
    info=dict(parent_sha256=sha256(args.parent),engine_sha256=sha256(args.engine),
              settings={k:v for k,v in vars(args).items() if isinstance(v,int)},rows=rows)
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(info,separators=(',',':')).encode(),mtime=0))
    print(len(rows),len(wins),sum(len(bank[i])-len(t) for i,t in wins.items()),flush=True)


if __name__=='__main__':
    main()
