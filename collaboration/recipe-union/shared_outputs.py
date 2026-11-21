"""Resynthesize shared output values from two parents inside a smaller conditional puzzle."""
from collections import Counter
from dataclasses import replace
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT),str(ROOT/'collaboration/retained-pool'),str(ROOT/'collaboration/register-search')]
from elf import check
from graph import active_graph,compile_graph,first_recipes
from neutral_lead import solve
from interior_bands import compile_on_parent
from solvers.gpu.gpu_join import cut_many
from cut_parents import fingerprint,signature


def neighborhoods(g):
    ancestors = {}
    for v,(_,a,b) in g.items():
        ancestors[v] = ancestors.get(a,set())|ancestors.get(b,set())|{v}
    return ancestors


def required(graph, outputs, available):
    pending = list(outputs)
    needed = set()
    while pending:
        v = pending.pop()
        if v not in available and v not in needed:
            needed.add(v)
            pending.extend(graph[v][1:])
    return {v:e for v,e in graph.items() if v in needed}


def proposals(p,base,donor):
    anc,alt = neighborhoods(base),neighborhoods(donor)
    uses = Counter(x for _,a,b in base.values() for x in set((a,b)))
    common = base.keys() & donor.keys()
    score = {}
    goals = set(p.targets)
    for v in common:
        # Detect disagreement below an otherwise identical junction, too.
        difference = len(anc[v]^alt[v]) + 2*(signature(base[v])!=signature(donor[v]))
        if difference>=2:
            score[v] = min(difference,40)*(1+min(uses[v],3)+2*(v in goals))
    group_set = set()
    for v in sorted(score,key=lambda x:(-score[x],x))[:16]:
        others = sorted((u for u in score if u!=v and u not in anc[v] and v not in anc[u]),
                        key=lambda u:(-len(anc[u]&anc[v])-len(alt[u]&alt[v]),-score[u],u))
        for n in (1,2,4,7):
            group = tuple(sorted([v,*others[:n-1]]))
            group_set.add(group)
    choices = []
    for group in sorted(group_set):
        keep,free = cut_many(p,base,set(group))
        safe = free.keys()|set(p.seeds)
        ops = base.keys()-keep.keys()
        if len(ops)<4:
            continue
        left = required(base,group,safe)
        right = required(donor,group,safe)
        boundary = {x for g in (left,right) for _,a,b in g.values() for x in (a,b) if x in safe}
        if len(boundary)>p.registers or not boundary or max(len(left),len(right))>120:
            continue
        if fingerprint(left)==fingerprint(right):
            continue
        # Include safe inputs used in a discarded alternative from either parent.
        hits = Counter(x for g in (base,donor) for v in left.keys()|right.keys() if v in g
                       for x in set(g[v][1:]) if x in safe and x not in boundary)
        extras = sorted(safe-boundary,key=lambda x:(-hits[x],x not in p.seeds,x))
        seeds = tuple(sorted(boundary))+tuple(extras[:p.registers-len(boundary)])
        diff = len(fingerprint(left)^fingerprint(right))
        rank = (min(len(left),len(right))-len(ops),-min(30,diff),len(boundary),group)
        choices.append((rank,group,keep,left,right,seeds,ops))
    return sorted(choices,key=lambda c:c[0])


def work(task):
    p,parent,donors,engine,rounds = task
    base = active_graph(p,first_recipes(p,parent))
    rows = []
    candidates = []
    for name,tape in donors:
        donor = active_graph(p,first_recipes(p,tape))
        pair = proposals(p,base,donor)
        rows.append(dict(name=name,choices=len(pair)))
        for choice in pair[:5]:
            candidates.append((choice,name))
    row = dict(before=len(parent),donors=rows,starts=[])
    used = []
    best = parent
    for (rank,group,keep,left,right,seeds,ops),name in sorted(candidates,key=lambda v:(v[0][0],v[1])):
        if any(len(ops&previous)*3>len(ops|previous)*2 for previous in used):
            continue
        inner = replace(p,seeds=seeds,targets=group)
        a = compile_graph(inner,left,attempts=4)
        b = compile_graph(inner,right,attempts=4)
        if a is None or b is None or a==b:
            continue
        seed = 943609+int(p.id[-4:])
        if not used:
            ctrl = solve(engine,p,[parent],seed,rounds)
            row['control'] = len(ctrl)
            if len(ctrl)<len(best):
                best = ctrl
                row['winner'] = 'control'
        used.append(ops)
        info = dict(donor=name,outputs=group,inputs=len(seeds),removed=len(ops),
                    parent_inner=len(a),donor_inner=len(b),variants=[])
        searched = solve(engine,inner,sorted((a,b),key=len),seed,rounds)
        for kind,child in [('base',a),('donor',b),('mix',searched)]:
            delta = first_recipes(inner,child)
            whole = compile_on_parent(p,parent,delta|keep)
            if whole is None:
                whole = compile_on_parent(p,parent,keep|delta)
            length = len(whole) if whole is not None else None
            info['variants'].append(dict(source=kind,inner=len(child),whole=length))
            if whole is not None and len(whole)<len(best):
                best = whole
                row['winner'] = name if kind!='base' else 'base reconstruction'
        row['starts'].append(info)
        if len(used)==3:
            break
    check(p,best)
    row['after']=len(best)
    return p.id,best,row
