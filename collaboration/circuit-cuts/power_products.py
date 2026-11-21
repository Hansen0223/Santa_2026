"""Rewrite several product and quotient outputs as signed exponent vectors over their inputs."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'collaboration/structure-controls/ruler'))
from elf import check,read_puzzles,read_submission,sha256,write_submission
from graph import active_graph,first_recipes
from selector import compile_selection


def difference(left, right, sign):
    result = left.copy()
    for x,n in right.items():
        result[x] = result.get(x,0)+sign*n
        if not result[x]:
            del result[x]
    return result


def expressions(p,graph,allowed):
    vectors,removed = {},set()
    for v,(op,a,b) in graph.items():
        if v in allowed and op in '*/':
            left = vectors.get(a,{a:1})
            right = vectors.get(b,{b:1})
            value = difference(left,right,1 if op=='*' else -1)
            if value and sum(map(abs,value.values()))<=22:
                vectors[v] = value
                removed.add(v)
    # Every edge read by an unchanged instruction remains an output of this pass.
    outputs = (set(p.targets)|{x for v,(_,a,b) in graph.items() if v not in removed for x in (a,b)}) & removed
    return {v:vectors[v] for v in sorted(outputs)}


def size(v):
    return sum(map(abs,v.values()))


def reuse_outputs(forms):
    ordered = sorted(forms,key=lambda v:(size(forms[v]),v))
    result = {}
    for j,v in enumerate(ordered):
        best = forms[v]
        for other in ordered[:j]:
            for sign in (1,-1):
                rem = difference(forms[v],forms[other],-sign)
                rem = difference(rem,{other:1},sign)
                if size(rem)<size(best):
                    best = rem
        result[v] = best
    return result


def merge(a,b,limit):
    if a*b>0:
        k = abs(a*b)
        if k>limit:
            return None
        return (k if a>0 else -k),('*',min(abs(a),abs(b)),max(abs(a),abs(b)))
    u,w = (a,-b) if a>0 else (b,-a)
    if u>=w and u%w==0:
        return u//w,('/',u,w)
    if w>u and w%u==0:
        return -(w//u),('/',w,u)
    return None


def pair_counts(terms,p):
    counts = Counter(terms)
    keys = sorted(counts)
    for j,b in enumerate(keys):
        for a in keys[:j+1]:
            freq = counts[a]//2 if a==b else min(counts[a],counts[b])
            if freq and a!=-b:
                m = merge(a,b,p.limit)
                if m and abs(m[0]) not in (abs(a),abs(b)):
                    yield a,b,m,freq


def synthesize(p,forms,original,relate):
    if relate:
        forms = reuse_outputs(forms)
    groups = {v:[k if n>0 else -k for k,n in form.items() for _ in range(abs(n))]
              for v,form in forms.items()}
    roots = original.keys()|set(p.seeds)
    menu = defaultdict(set)
    def record(m):
        token,recipe = m
        if abs(token) not in p.seeds and abs(token) not in recipe[1:]:
            menu[abs(token)].add(recipe)

    # A positive pair and the same negative pair can share one physical product.
    for _ in range(24):
        freq = Counter()
        for terms in groups.values():
            for a,b,(k,recipe),n in pair_counts(terms,p):
                freq[abs(k),recipe] += n
        if not freq:
            break
        (v,recipe),n = max(freq.items(),key=lambda item:(item[1]+int(item[0][0] in roots),
                                                           item[1],-item[0][0],item[0][1]))
        if n<2:
            break
        for terms in groups.values():
            for a,b,(k,r),count in list(pair_counts(terms,p)):
                if r!=recipe or abs(k)!=v:
                    continue
                for _ in range(count):
                    if a not in terms or b not in terms or a==b and terms.count(a)<2:
                        break
                    terms.remove(a); terms.remove(b); terms.append(k)
                    record((k,r))
    hits = 0
    for target,terms in groups.items():
        while len(terms)>1:
            if any(-x in terms for x in terms):
                x = next(x for x in terms if -x in terms)
                terms.remove(x);terms.remove(-x)
                continue
            choices = list(pair_counts(terms,p))
            if not choices:
                break
            a,b,m,_ = min(choices,key=lambda q:(abs(q[2][0]) not in roots and abs(q[2][0]) not in menu,
                                                q[2][1][0]!='/',abs(q[2][0]),q[0],q[1]))
            record(m)
            terms.remove(a);terms.remove(b);terms.append(m[0])
        hits += terms==[target]
    return menu,hits


def work(task):
    p,parent = task
    g = active_graph(p,first_recipes(p,parent))
    order = list(g)
    scopes = [order] + [order[k*len(order)//4:(k+2)*len(order)//4] for k in range(3)]
    edges = defaultdict(set)
    details = []
    for scope in scopes:
        forms = expressions(p,g,set(scope))
        if len(forms)<2:
            continue
        for mode in (False,True):
            recipes,hits = synthesize(p,forms,g,mode)
            for v,rs in recipes.items():
                edges[v].update(rs)
            details.append(dict(outputs=len(forms),related=mode,folded=hits))
    def same(v,r):
        old = g.get(v)
        if old is None:
            return False
        return old==r or r[0]=='*' and old==(r[0],r[2],r[1])
    extra = [{v:r} for v in sorted(edges) for r in sorted(edges[v]) if not same(v,r)]
    result,child = compile_selection(p,parent,g,extra,False) if extra else ({},parent)
    check(p,child)
    return p.id,child,dict(before=len(parent),after=len(child),new=len(set(edges)-g.keys()),
                           alternatives=len(extra),runs=details,selection=result)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for n in ('parent','puzzles','out'):
        ap.add_argument('--'+n,required=True,type=Path)
    for n,k in [('count',60),('jobs',6),('offset',0)]:
        ap.add_argument('--'+n,type=int,default=k)
    args=ap.parse_args()
    ps=read_puzzles(args.puzzles);bank=read_submission(args.parent)
    eligible=sorted((p for p in ps if sum(t[0] in '*/' for t in bank[p.id])>=12),
                    key=lambda p:hashlib.sha256(('exponent2-'+p.id).encode()).digest())
    jobs=[(p,bank[p.id]) for p in eligible[args.offset:args.offset+args.count]]
    wins,rows = {},{}
    with ProcessPoolExecutor(args.jobs) as pool:
        for i,t,row in pool.map(work,jobs):
            rows[i]=row
            if len(t)<len(bank[i]):
                wins[i]=t
    args.out.mkdir(exist_ok=True,parents=True)
    write_submission(args.out/'wins.csv',[p for p in ps if p.id in wins],wins)
    record=dict(eligible=len(eligible),parent_sha256=sha256(args.parent),rows=rows,
                settings={k:v for k,v in vars(args).items() if isinstance(v,int)})
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(record,separators=(',',':')).encode(),mtime=0))
    print(len(rows),len(wins),sum(len(bank[i])-len(t) for i,t in wins.items()))


if __name__=='__main__':
    main()
