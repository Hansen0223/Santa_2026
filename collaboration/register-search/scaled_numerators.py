"""Try constructing a scaled numerator and divide exactly at the end."""
import argparse
from bisect import bisect_left
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
from itertools import combinations_with_replacement
import json
from pathlib import Path

from interior_bands import compile_on_parent
from quotient_chains import private_cone
from two_sided_chains import reverse_steps
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes
from solvers.graphs.corpus_prefix import arithmetic_edges


def variants(puzzle, root, ready, maximum, denominators):
    pool = sorted(ready)
    forward = {}
    for a,b in combinations_with_replacement(pool,2):
        for v, edge in arithmetic_edges(a,b,puzzle.limit):
            if v not in ready:
                forward.setdefault(v,edge)
    residues = {}
    for modulus in pool:
        if modulus < 2:
            continue
        table = defaultdict(list)
        for offset in pool:
            table[offset % modulus].append(offset)
        residues[modulus] = table
    reachable = sorted(ready | forward.keys())

    def near(value):
        i = bisect_left(reachable,value)
        return min(abs(value-reachable[j]) for j in (i-1,i) if 0 <= j < len(reachable))

    def lookup(value, extra):
        if value in ready:
            yield {}
        elif value in forward:
            yield {value:forward[value]}
        elif extra:
            for known in pool:
                for v,edge in reverse_steps(value,known,puzzle.limit):
                    if v != value and v in forward:
                        yield {v:forward[v],value:edge}
                        return

    found = {False:{}, True:{}}
    for d in denominators:
        numerator = root*d
        if numerator > puzzle.limit:
            continue
        pending = []
        output = found[d!=1]
        suffix = {} if d==1 else {root:("/",numerator,d)}
        room = maximum - len(suffix)
        if room <= 0:
            continue

        def insert(prefix, quotient_value, extra=False):
            reserved = prefix.keys() | suffix.keys()
            if quotient_value in reserved:
                return
            for tail in lookup(quotient_value,extra):
                if tail.keys() & reserved:
                    continue
                patch = prefix | suffix | tail
                if len(patch) <= maximum:
                    output.setdefault(frozenset(patch.items()),patch)

        insert({},numerator,extra=room>=2)
        for radix, table in residues.items():
            q,r = divmod(numerator,radix)
            if not r and q >= 1:
                prefix = {} if numerator in ready else {numerator:("*",q,radix)}
                if q != numerator:
                    if q in forward or q in ready:
                        insert(prefix,q)
                    elif room >= 3 and q != root:
                        pending.append((near(q),q,prefix))
            if room < 2:
                continue
            for sign in (1,-1):
                for offset in table.get((sign*r)%radix,()):
                    middle = numerator - sign*offset
                    if not 1 <= middle <= puzzle.limit:
                        continue
                    q = middle//radix
                    if q < 1 or q in (numerator,root) or middle == root and d!=1:
                        continue
                    prefix = {numerator:("+" if sign>0 else "-",middle,offset)}
                    if middle not in ready:
                        prefix[middle] = ("*",q,radix)
                    # A retained product only needs the final offset.
                    actual = q if middle not in ready else middle
                    if actual in ready or actual in forward:
                        insert(prefix,actual)
                    elif room >= len(prefix)+2:
                        pending.append((near(actual),actual,prefix))
        for _,q,prefix in sorted(pending,key=lambda t:(t[0],len(t[2]),t[1]))[:12]:
            insert(prefix,q,extra=True)
    return {g:sorted(paths.values(),key=lambda p:(len(p),tuple(sorted(p.items()))))[:12]
            for g,paths in found.items()}


def work(job):
    p,parent,roots,width = job
    graph = active_graph(p,first_recipes(p,parent))
    uses = Counter(set(p.targets))
    for _,a,b in graph.values():
        uses.update({a,b})
    cuts = []
    for v in graph:
        if uses[v]>2 or v.bit_length()<19:
            continue
        cone = private_cone(graph,uses,v)
        if 4<=len(cone)<=12:
            cuts.append((-len(cone),-v.bit_length(),v,cone))
    best = parent
    records = []
    for _,_,root,cut in sorted(cuts)[:roots]:
        fixed = {v:e for v,e in graph.items() if v not in cut}
        ready = set(p.seeds)
        for v,(_,a,b) in fixed.items():
            if a in ready and b in ready:
                ready.add(v)
        ds = sorted((v for v in ready if 1<v<=p.limit//root),key=lambda v:(v>128,v.bit_length(),-uses[v],v))[:width]
        options = variants(p,root,ready,len(cut)-1,[1,*ds])
        row = dict(root=root,removed=len(cut),scales=len(ds),trials={})
        for scaled,paths in options.items():
            lengths = []
            for path in paths:
                candidate = compile_on_parent(p,parent,path|fixed)
                if candidate is not None:
                    lengths.append(len(candidate))
                    best = min((best,candidate),key=len)
            row["trials"]["scaled" if scaled else "ordinary"] = dict(paths=len(paths),best=min(lengths,default=None))
        records.append(row)
    return p.id,best,dict(before=len(parent),after=check(p,best),eligible=len(cuts),cuts=records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("puzzles","parent","out"):
        parser.add_argument("--"+name,type=Path,required=True)
    for name,default in (("count",120),("offset",0),("roots",4),("width",14),("jobs",9)):
        parser.add_argument("--"+name,type=int,default=default)
    args = parser.parse_args()
    ps = read_puzzles(args.puzzles)
    parent = read_submission(args.parent)
    selected = sorted((p for p in ps if len(parent[p.id])>=40),
                      key=lambda p:hashlib.sha256(("scaled-numerator-"+p.id).encode()).digest())
    tasks = [(p,parent[p.id],args.roots,args.width) for p in selected[args.offset:args.offset+args.count]]
    rows,wins = {},{}
    with ProcessPoolExecutor(args.jobs) as pool:
        for i,tape,row in pool.map(work,tasks,chunksize=1):
            rows[i] = row
            if len(tape)<len(parent[i]):
                wins[i] = tape
                print(i,len(parent[i]),len(tape),flush=True)
    args.out.mkdir(exist_ok=True,parents=True)
    write_submission(args.out/"wins.csv",[p for p in ps if p.id in wins],wins)
    receipt = dict(parent_sha256=sha256(args.parent),settings={k:v for k,v in vars(args).items() if isinstance(v,int)},rows=rows)
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(receipt,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(len(parent[i])-len(t) for i,t in wins.items()))


if __name__=="__main__":
    main()
