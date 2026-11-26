"""Transfer additive fragments after scaling every value by the same factor."""
import argparse
from collections import Counter,defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
from math import gcd
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/"collaboration/register-search")]
from interior_bands import compile_on_parent,solve
from elf import check,read_puzzles,read_submission,sha256,write_submission
from graph import active_graph,first_recipes


def ratio(a,b):
    divisor=gcd(a,b)
    return a//divisor,b//divisor


def templates(graphs):
    index=defaultdict(dict)
    for identifier,graph in graphs.items():
        for value,(outer,a,b) in graph.items():
            if outer not in "+-":
                continue
            for middle in {a,b} & graph.keys():
                inner,c,d=graph[middle]
                if inner not in "+-":
                    continue
                leaves=sorted(({a,b}-{middle}) | {c,d})
                if len(leaves)<2 or value in leaves:
                    continue
                divisor=gcd(value,a,b,c,d)
                fragment=(
                    (middle//divisor,inner,c//divisor,d//divisor),
                    (value//divisor,outer,a//divisor,b//divisor),
                )
                requirements=tuple(v//divisor for v in leaves)
                for leaf in requirements:
                    index[ratio(fragment[-1][0],leaf)].setdefault(fragment,(requirements,identifier,divisor))
    return index


def matching(puzzle, graph, index, count):
    seeds=set(puzzle.seeds)
    targets=set(puzzle.targets)
    known=seeds|graph.keys()
    uses=Counter(u for _,a,b in graph.values() for u in {a,b})
    roots=sorted(graph,key=lambda v:(v not in targets,-uses[v],v))[:count]
    ordered=sorted(known)
    seen=set()
    for value in roots:
        for anchor in ordered:
            for fragment,(leaves,donor,source_scale) in index.get(ratio(value,anchor),{}).items():
                scaled_value=fragment[-1][0]
                if value%scaled_value:
                    continue
                scale=value//scaled_value
                if scale==source_scale:
                    continue
                middle=fragment[0][0]*scale
                if middle in known or middle>puzzle.limit or any(leaf*scale not in known for leaf in leaves):
                    continue
                patch={v*scale:(op,a*scale,b*scale) for v,op,a,b in fragment}
                signature=frozenset(patch.items())
                if signature not in seen:
                    seen.add(signature)
                    yield patch,donor,scale,source_scale,value


def translated_templates(graphs):
    index=defaultdict(dict)
    for identifier,graph in graphs.items():
        for value,(outer,a,b) in graph.items():
            if outer not in "+-":
                continue
            for middle in {a,b} & graph.keys():
                inner,c,d=graph[middle]
                if inner not in "+-":
                    continue
                leaves=tuple(sorted(({a,b}-{middle}) | {c,d}))
                if len(leaves)<2 or value in leaves:
                    continue
                weight=2 if inner=="+" else 0
                wa,wb=(weight if a==middle else 1),(weight if b==middle else 1)
                coefficient=wa+wb if outer=="+" else wa-wb
                if not coefficient:
                    continue
                fragment=((middle,inner,c,d),(value,outer,a,b))
                for leaf in leaves:
                    key=(coefficient,value-coefficient*leaf)
                    index[key].setdefault(fragment,(leaves,leaf,identifier,weight))
    return index


def matching_translated(puzzle,graph,index,count):
    known=set(puzzle.seeds)|graph.keys()
    targets=set(puzzle.targets)
    uses=Counter(u for _,a,b in graph.values() for u in {a,b})
    roots=sorted(graph,key=lambda v:(v not in targets,-uses[v],v))[:count]
    seen=set()
    for value in roots:
        for anchor in sorted(known):
            for coeff in (-1,1,3,4):
                for fragment,(leaves,leaf,donor,weight) in index.get((coeff,value-coeff*anchor),{}).items():
                    shift=anchor-leaf
                    middle,inner,c,d=fragment[0]
                    new_middle=middle+weight*shift
                    if not shift or not 0<new_middle<=puzzle.limit or new_middle in known:
                        continue
                    if any(l+shift not in known for l in leaves):
                        continue
                    _,outer,a,b=fragment[1]
                    a=new_middle if a==middle else a+shift
                    b=new_middle if b==middle else b+shift
                    patch={new_middle:(inner,c+shift,d+shift),value:(outer,a,b)}
                    key=frozenset(patch.items())
                    if key not in seen:
                        seen.add(key)
                        yield patch,donor,shift,0,value


def degree(op,left,right):
    if op=="*":
        return left+right
    if op=="/":
        return left-right
    return left if left==right else None


def scale_key(value,leaf,power):
    if power>0:
        a,b=ratio(value,leaf**power)
    else:
        a,b=value*leaf**(-power),1
    return power,a,b


def homogeneous_templates(graphs):
    index=defaultdict(dict)
    for identifier,graph in graphs.items():
        for value,(outer,a,b) in graph.items():
            for middle in {a,b} & graph.keys():
                inner,c,d=graph[middle]
                if inner in "+-" and outer in "+-":
                    continue
                leaves=tuple(sorted(({a,b}-{middle}) | {c,d}))
                if len(leaves)<2 or value in leaves:
                    continue
                fragment=((middle,inner,c,d),(value,outer,a,b))
                mobile_leaves=tuple(x for x in leaves if x>16)
                for mobile in dict.fromkeys((leaves,mobile_leaves)):
                    if not mobile:
                        continue
                    internal=degree(inner,int(c in mobile),int(d in mobile))
                    if internal is None:
                        continue
                    output=degree(outer,internal if a==middle else int(a in mobile),
                                  internal if b==middle else int(b in mobile))
                    if output is None or output==0:
                        continue
                    for leaf in mobile:
                        key=scale_key(value,leaf,output)
                        signature=fragment,mobile
                        index[key].setdefault(signature,(leaves,leaf,identifier,internal))
    return index


def matching_homogeneous(puzzle,graph,index,count):
    known=set(puzzle.seeds)|graph.keys()
    weights=Counter(u for _,a,b in graph.values() for u in {a,b})
    targets=set(puzzle.targets)
    roots=sorted(graph,key=lambda v:(v not in targets,-weights[v],v))[:count]
    ordered=sorted(known)
    powers=sorted({key[0] for key in index})
    seen=set()
    for value in roots:
        for anchor in ordered:
            for power in powers:
                for (fragment,mobile),(leaves,leaf,donor,middle_degree) in index.get(scale_key(value,anchor,power),{}).items():
                    numerator,denominator=ratio(anchor,leaf)
                    if numerator==denominator:
                        continue
                    mapped={}
                    for x in leaves:
                        y,remainder=divmod(x*numerator,denominator) if x in mobile else (x,0)
                        if remainder or y not in known:
                            break
                        mapped[x]=y
                    else:
                        middle,inner,c,d=fragment[0]
                        num,den=(numerator,denominator) if middle_degree>=0 else (denominator,numerator)
                        exponent=abs(middle_degree)
                        result,rem=divmod(middle*num**exponent,den**exponent)
                        if rem or not 0<result<=puzzle.limit or result in known:
                            continue
                        mapped[middle]=result
                        _,outer,a,b=fragment[1]
                        patch={result:(inner,mapped[c],mapped[d]),value:(outer,mapped[a],mapped[b])}
                        key=frozenset(patch.items())
                        if key not in seen:
                            seen.add(key)
                            yield patch,donor,numerator,denominator,value


MATCHERS={"scale":matching,"translate":matching_translated,"homogeneous":matching_homogeneous}
TRAINERS={"scale":templates,"translate":translated_templates,"homogeneous":homogeneous_templates}


def transform_details(mode,scale,source_scale):
    if mode=="translate":
        return {"shift":scale}
    if mode=="homogeneous":
        return {"scale_ratio":[scale,source_scale]}
    return {"scale":scale,"source_scale":source_scale}


def work(item):
    p,parent,engine,roots,rounds,mode = item
    graph=active_graph(p,first_recipes(p,parent))
    matches=0
    accepted=[]
    best=parent
    match=MATCHERS[mode]
    for patch,donor,scale,source_scale,value in match(p,graph,TEMPLATES,roots):
        matches+=1
        try:
            candidate=active_graph(p,graph|patch)
        except (KeyError,ValueError):
            continue
        if not patch.keys()<=candidate.keys() or len(candidate)>len(parent)+1:
            continue
        accepted.append((len(candidate),value,scale,donor,source_scale,candidate))
    row=dict(before=len(parent),matches=matches,accepted=len(accepted),starts=[])
    seen=set()
    for _,value,scale,donor,source_scale,candidate in sorted(accepted,key=lambda x:x[:4]):
        if value in seen:
            continue
        result=compile_on_parent(p,parent,candidate)
        if result is None:
            continue
        seen.add(value)
        seed=854177+int(p.id[-4:])
        if "control" not in row:
            control=solve(engine,p,[parent],seed,rounds)
            row["control"]=len(control)
            best=min((best,control),key=len)
        refined=solve(engine,p,[result,parent],seed,rounds)
        best=min((best,result,refined),key=len)
        transform=transform_details(mode,scale,source_scale)
        row["starts"].append(dict(root=value,donor=donor,raw=len(result),after=len(refined),**transform))
        if len(seen)==2:
            break
    row["after"]=check(p,best)
    return p.id,best,row


def initialize(index):
    global TEMPLATES
    TEMPLATES=index


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("puzzles","parent","engine","out"):
        parser.add_argument("--"+name,type=Path,required=True)
    for name,n in (("count",120),("training",360),("roots",48),("rounds",450),("jobs",5)):
        parser.add_argument("--"+name,type=int,default=n)
    transform=parser.add_mutually_exclusive_group()
    transform.add_argument("--translate",action="store_true",help="Shift the donor inputs instead of scaling them")
    transform.add_argument("--homogeneous",action="store_true",help="Scale mixed multiplication and division fragments")
    args=parser.parse_args()
    puzzles=read_puzzles(args.puzzles)
    parent_digest=sha256(args.parent)
    parent=read_submission(args.parent)
    if sha256(args.parent)!=parent_digest:
        raise ValueError("Parent changed while loading")
    order=sorted(puzzles,key=lambda p:hashlib.sha256(("scalable-fragments-"+p.id).encode()).digest())
    training=order[:args.training]
    mode="homogeneous" if args.homogeneous else "translate" if args.translate else "scale"
    train=TRAINERS[mode]
    index=train({p.id:active_graph(p,first_recipes(p,parent[p.id])) for p in training})
    selected=[p for p in order[args.training:] if 35<=len(parent[p.id])<=230][:args.count]
    tasks=[(p,parent[p.id],args.engine,args.roots,args.rounds,mode) for p in selected]
    rows,wins={},{}
    with ProcessPoolExecutor(args.jobs,initializer=initialize,initargs=(index,)) as pool:
        for pid,tape,row in pool.map(work,tasks):
            rows[pid]=row
            if row["after"]<row["before"]:
                wins[pid]=tape
                print(pid,row["before"],row["after"],flush=True)
    args.out.mkdir(parents=True,exist_ok=True)
    write_submission(args.out/"wins.csv",[p for p in puzzles if p.id in wins],wins)
    record=dict(parent_sha256=parent_digest,puzzles_sha256=sha256(args.puzzles),engine_sha256=sha256(args.engine),
                training=[p.id for p in training],index_buckets=len(index),mode=mode,
                settings={k:v for k,v in vars(args).items() if isinstance(v,int)},rows=rows)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(record,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-rows[i]["after"] for i in wins))


if __name__=="__main__":
    main()
