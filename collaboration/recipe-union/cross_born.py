"""Introduce fresh intermediates computed from operands exclusive to separate programs."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
from itertools import combinations
import json
from pathlib import Path
import sys

from full_union import additions, compile_selection
from novelty_portfolio import canonical, solve

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"collaboration/register-search"))
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes
from helper_triangles import removable_together
from quotient_chains import private_cone
from two_sided_chains import reverse_steps
from solvers.graphs.corpus_prefix import arithmetic_edges


def demand(puzzle, old, available):
    targets = set(puzzle.targets)
    consumers = Counter(v for _,a,b in old.values() for v in {a,b})
    uses = consumers + Counter(targets)
    private = {v:private_cone(old,uses,v) for v in old}
    roots = sorted(old, key=lambda v:(v not in targets,-len(private[v]),-consumers[v],v))[:54]
    needed = defaultdict(dict)
    for v in roots:
        for a in sorted(available):
            if a in private[v]:
                continue
            for h,edge in reverse_steps(v,a,puzzle.limit):
                if h not in available and h!=v:
                    needed[h].setdefault(v,edge)
    return needed, uses


def cross_births(puzzle, masks, width):
    values = sorted(masks)
    parents = defaultdict(list)
    for a,b in combinations(values,2):
        if masks[a]&masks[b]:
            continue
        for h,edge in arithmetic_edges(a,b,puzzle.limit):
            if h not in masks and len(parents[h]) < width:
                parents[h].append(edge)
    return parents


def create(puzzle, old, sources, limit, two_steps):
    masks = {v:(1<<len(sources))-1 for v in puzzle.seeds}
    for i,graph in enumerate(sources):
        for v in graph:
            masks[v]=masks.get(v,0)|(1<<i)
    needed,uses=demand(puzzle,old,masks)
    births=cross_births(puzzle,masks,3)
    ranked=[]
    economics={}
    def score(roots):
        key=frozenset(roots)
        if key not in economics:
            economics[key]=len(removable_together(old,uses,key))
        return economics[key]
    for h,roots in needed.items():
        if h not in births:
            continue
        drop=score(roots)
        if drop>=2:
            ranked.append((-drop,-len(roots),h,None,()))
    if two_steps and births:
        economic=[(-score(roots),-len(roots),h) for h,roots in needed.items()
                  if h not in births and len(roots)>=2]
        for drop,negative,h in sorted(economic)[:limit*8]:
            if drop > -3:
                break
            seen=set()
            for a in sorted(masks):
                for m,edge in reverse_steps(h,a,puzzle.limit):
                    if m in births and m not in seen:
                        seen.add(m)
                        ranked.append((drop,negative,h,m,edge))
                if len(seen)>=4:
                    break
    constructions={}
    rewards={}
    for drop,_,h,mid,edge in sorted(ranked,key=lambda x:(x[0],x[1],x[3] is not None,x[2],x[3] or 0))[:limit]:
        if mid is None:
            for route in births[h]:
                constructions[h,route]={h:route}
        else:
            constructions[h,edge]={h:edge}
            for route in births[mid]:
                constructions[mid,route]={mid:route}
        rewards[h]=max(rewards.get(h,0),min(5,-drop))
        for root,route in needed[h].items():
            constructions[root,route]={root:route}
    return list(constructions.values()),rewards,dict(births=len(births),ranked=len(ranked))


def ranked_exchanges(puzzle, old, treatment, rewards, requested):
    targets=set(puzzle.targets)
    uses=Counter(v for _,a,b in old.values() for v in {a,b})+Counter(targets)
    birth=defaultdict(list)
    recipients=defaultdict(set)
    for path in treatment:
        for output,edge in path.items():
            if output in rewards:
                birth[output].append(edge)
            if output in old:
                for operand in set(edge[1:]) & rewards.keys():
                    recipients[operand].add(output)
    proposals=[]
    for h,uses_h in recipients.items():
        removed=removable_together(old,uses,uses_h)
        forbidden=sorted(removed-targets,key=lambda v:(-uses[v],v))
        if not forbidden:
            continue
        edges=[e for e in birth[h] if forbidden[0] not in e[1:]]
        if edges:
            proposals.append((-len(removed),-len(uses_h),h,forbidden[0],edges))
    for _,_,h,omitted,edges in sorted(proposals)[:requested]:
        yield h,omitted,tuple((h,e) for e in edges)


def guided(puzzle, parent, donors, engine, width, two_steps, rounds, requested):
    graphs=[active_graph(puzzle,first_recipes(puzzle,t)) for t in (parent,*donors)]
    old=graphs[0]
    original=first_recipes(puzzle,parent)
    literal=additions(puzzle,[parent,*donors])
    treatment,rewards,counts=create(puzzle,old,graphs,width,two_steps)
    report=dict(before=len(parent),donors=list(map(len,donors)),**counts,exchanges=[])
    best=parent
    ready=[]
    for fresh,omitted,required in ranked_exchanges(puzzle,old,treatment,rewards,requested):
        details,tape=compile_selection(puzzle,parent,original,literal+treatment,False,
            slack=2,required_recipes=required,novelty_weights={fresh:1},forbidden_values=(omitted,))
        details.update(introduced=fresh,omitted=omitted)
        report["exchanges"].append(details)
        if tape is not None:
            result=active_graph(puzzle,first_recipes(puzzle,tape))
            if fresh not in result or omitted in result:
                raise ValueError("A forced replacement changed during scheduling")
            best=min((best,tape),key=len)
            ready.append((tape,details))
    if engine and ready:
        seed=311223+int(puzzle.id[-4:])
        control=solve(engine,puzzle,[parent,*donors[:2]],seed,rounds)
        report["control"]=len(control)
        best=min((best,control),key=len)
        for tape,details in ready:
            refined=solve(engine,puzzle,[tape,parent,*donors[:2]],seed,rounds)
            details["polish"]=len(refined)
            best=min((best,refined),key=len)
    report["after"]=check(puzzle,best)
    return puzzle.id,best,report


def run(job):
    *args, force = job
    if force:
        return guided(*args,force)
    return work(tuple(args))


def work(job):
    puzzle,parent,donors,engine,width,two_steps,rounds=job
    source=[active_graph(puzzle,first_recipes(puzzle,t)) for t in (parent,*donors)]
    old=source[0]
    original=first_recipes(puzzle,parent)
    paths=additions(puzzle,[parent,*donors])
    treatment,rewards,counts=create(puzzle,old,source,width,two_steps)
    best=parent
    row=dict(before=len(parent),donors=list(map(len,donors)),**counts)
    if treatment:
        row["control"], plain=compile_selection(puzzle,parent,original,paths,True)
        row["cross_birth"], cross=compile_selection(puzzle,parent,original,paths+treatment,True)
        best=min((best,plain,cross),key=len)
        if engine and len(best)==len(parent):
            row["novel_model"],candidate=compile_selection(
                puzzle,parent,original,paths+treatment,False,slack=1,novelty_weights=rewards)
            if candidate is not None:
                current=active_graph(puzzle,first_recipes(puzzle,candidate))
                count=len(current.keys()&rewards.keys())
                if count and all(canonical(current)!=canonical(g) for g in source):
                    salt=201953+int(puzzle.id[-4:])
                    first=solve(engine,puzzle,[parent,*donors[:2]],salt,rounds)
                    second=solve(engine,puzzle,[candidate,parent,*donors[:2]],salt,rounds)
                    best=min((best,first,second),key=len)
                    row["polish"]=dict(start=len(candidate),fresh=count,control=len(first),after=len(second))
    row["after"]=check(puzzle,best)
    return puzzle.id,best,row


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ("puzzles","parent","out"):
        parser.add_argument("--"+key,type=Path,required=True)
    parser.add_argument("--engine",type=Path)
    parser.add_argument("--donors",type=Path,nargs="+",required=True)
    parser.add_argument("--two-steps",action="store_true")
    for name,n in (("count",130),("gap",14),("width",42),("jobs",8),("rounds",420),("force",0),("offset",0)):
        parser.add_argument("--"+name,type=int,default=n)
    args=parser.parse_args()
    ps=read_puzzles(args.puzzles)
    bank=read_submission(args.parent)
    donors=[read_submission(d) for d in args.donors]
    ranked=[]
    for p in ps:
        parent=bank[p.id]
        if not 30<=len(parent)<=250:
            continue
        old=active_graph(p,first_recipes(p,parent))
        candidates={}
        for donor in donors:
            tape=donor.get(p.id)
            if tape is None or tape==parent or len(tape)>len(parent)+args.gap:
                continue
            alt=active_graph(p,first_recipes(p,tape))
            distance=len(alt.keys()^old.keys())
            if distance>=5:
                candidates[tape]=distance/(1+max(0,len(tape)-len(parent)))
        if candidates:
            ranked.append((-max(candidates.values())/len(parent),p.id,p,
                           sorted(candidates,key=lambda t:(-candidates[t],len(t),t))[:3]))
    selected=sorted(ranked)[args.offset:args.offset+args.count]
    tasks=[(p,bank[p.id],d,args.engine,args.width,args.two_steps,args.rounds,args.force) for _,_,p,d in selected]
    rows,wins={},{}
    with ProcessPoolExecutor(args.jobs) as pool:
        for i,tape,row in pool.map(run,tasks,chunksize=1):
            rows[i]=row
            if len(tape)<len(bank[i]):
                wins[i]=tape
                print(i,len(bank[i]),len(tape),flush=True)
    args.out.mkdir(exist_ok=True,parents=True)
    write_submission(args.out/"wins.csv",[p for p in ps if p.id in wins],wins)
    record=dict(parent_sha256=sha256(args.parent),eligible=len(ranked),
                donors={p.name:sha256(p) for p in args.donors},
                settings={k:v for k,v in vars(args).items() if isinstance(v,int)},rows=rows)
    if args.engine:
        record["engine_sha256"]=sha256(args.engine)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(record,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-len(t) for i,t in wins.items()),flush=True)


if __name__=="__main__":
    main()
