"""Resynthesize additive multi-output regions by sharing signed pairs of boundary values."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
from itertools import combinations
import json
from pathlib import Path

from interior_bands import compile_on_parent
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes


def regions(graph, targets):
    # Connect an addition or subtraction to its operands only when they are additive too.
    add={v for v,e in graph.items() if e[0] in "+-"}
    edges=defaultdict(set)
    users=defaultdict(set)
    for v,(_,a,b) in graph.items():
        for operand in {a,b}:
            users[operand].add(v)
            if v in add and operand in add:
                edges[v].add(operand)
                edges[operand].add(v)
    seen=set()
    for v in graph:
        if v not in add or v in seen:
            continue
        group={v}
        stack=[v]
        while stack:
            x=stack.pop()
            for y in edges[x]-group:
                group.add(y)
                stack.append(y)
        seen.update(group)
        outputs=sorted(x for x in group if x in targets or users[x]-group)
        if 2<=len(outputs)<=15 and 4<=len(group)<=42:
            forms={}
            for x, (op,a,b) in graph.items():
                if x not in group:
                    continue
                terms=Counter(forms.get(a,{a:1}))
                for atom,n in forms.get(b,{b:1}).items():
                    terms[atom]+=(1 if op=="+" else -1)*n
                forms[x]={atom:n for atom,n in terms.items() if n}
            if all(sum(abs(n) for n in forms[x].values())<=24 for x in outputs):
                yield group,outputs,{x:forms[x] for x in outputs}


def word(form):
    return [v if n>0 else -v for v,n in sorted(form.items()) for _ in range(abs(n))]


def pairing(a,b,cap):
    total=a+b
    if not total or abs(total)>cap:
        return None
    if total<0:
        a,b=-a,-b
    if a>0 and b>0:
        return total,("+",min(a,b),max(a,b))
    return total,("-",max(a,b),-min(a,b))


def finish(terms,limit,prefer):
    path={}
    while len(terms)>1:
        options=[]
        for i,j in combinations(range(len(terms)),2):
            a,b=terms[i],terms[j]
            result=pairing(a,b,limit)
            if not result:
                continue
            v,e=result
            if abs(v) in (abs(a),abs(b)):
                continue
            rank=(v<0,abs(v) if prefer else -abs(v),i,j)
            options.append((rank,v,e,i,j))
        if not options:
            return None
        _,v,e,i,j=min(options)
        path.setdefault(abs(v),e)
        terms=[a for k,a in enumerate(terms) if k not in (i,j)]+[v]
    return path


def compress(p,forms):
    terms={root:word(form) for root,form in forms.items()}
    recipes={}
    saved=0
    for _ in range(24):
        owners=defaultdict(set)
        pair_edges={}
        for root,t in terms.items():
            for a,b in combinations(t,2):
                result=pairing(a,b,p.limit)
                if result is None:
                    continue
                v,e=result
                if abs(v) in (abs(a),abs(b)) or abs(v) in p.seeds:
                    continue
                pair=tuple(sorted((a,b) if v>0 else (-a,-b)))
                owners[pair].add(root)
                pair_edges[pair]=(abs(v),e)
        eligible=[pair for pair,support in owners.items() if len(support)>=2]
        if not eligible:
            break
        a,b=min(eligible,key=lambda q:(-len(owners[q]),pair_edges[q][0] not in recipes,abs(sum(q)),q))
        v,e=pair_edges[a,b]
        recipes.setdefault(v,e)
        for root in owners[a,b]:
            t=terms[root]
            for sign in (1,-1):
                x,y=sign*a,sign*b
                multiplicity=min(t.count(x),t.count(y)) if x!=y else t.count(x)//2
                for _ in range(multiplicity):
                    t.remove(x)
                    t.remove(y)
                    t.append(sign*v)
                    saved+=1
    return terms,recipes,saved


def work(task):
    p,parent=task
    graph=active_graph(p,first_recipes(p,parent))
    best=parent
    rows=[]
    for group,outputs,forms in regions(graph,set(p.targets)):
        for label,prepared in (("direct",({v:word(w) for v,w in forms.items()},{},0)),("shared",compress(p,forms))):
            terms,common,merged_pairs=prepared
            for prefer in (False,True):
                local=dict(common)
                for root in outputs:
                    path=finish(terms[root],p.limit,prefer)
                    if path is None:
                        break
                    local.update(path)
                else:
                    candidate=compile_on_parent(p,parent,graph|local)
                    info=dict(size=len(group),outputs=len(outputs),method=label,merges=merged_pairs,
                              physical=len(candidate) if candidate is not None else None)
                    rows.append(info)
                    if candidate is not None and len(candidate)<len(best):
                        best=candidate
    check(p,best)
    return p.id,best,dict(before=len(parent),after=len(best),trials=rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ("puzzles","parent","out"):
        parser.add_argument("--"+key,type=Path,required=True)
    for key,n in (("count",140),("offset",0),("jobs",8)):
        parser.add_argument("--"+key,type=int,default=n)
    args=parser.parse_args()
    puzzles=read_puzzles(args.puzzles)
    bank=read_submission(args.parent)
    ordered=sorted((p for p in puzzles if len(bank[p.id])>=32),
                   key=lambda p:hashlib.sha256(("linear-overlap-"+p.id).encode()).digest())
    tasks=[(p,bank[p.id]) for p in ordered[args.offset:args.offset+args.count]]
    rows,wins={},{}
    with ProcessPoolExecutor(args.jobs) as pool:
        for i,tape,record in pool.map(work,tasks,chunksize=2):
            rows[i]=record
            if len(tape)<len(bank[i]):
                wins[i]=tape
    args.out.mkdir(parents=True,exist_ok=True)
    write_submission(args.out/"wins.csv",[p for p in puzzles if p.id in wins],wins)
    data=dict(parent_sha256=sha256(args.parent),eligible=len(ordered),settings={k:v for k,v in vars(args).items() if isinstance(v,int)},rows=rows)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(data,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-len(tape) for i,tape in wins.items()))


if __name__=="__main__":
    main()
