"""Search bounded regions shared by two or more downstream arithmetic values."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
from itertools import combinations
import json
from pathlib import Path
import subprocess

from helper_triangles import removable_together
from interior_bands import compile_on_parent, solve
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes
from solvers.proofs.exact_boundary import generate
from solvers.graphs.corpus_prefix import arithmetic_edges


def cuts(puzzle, graph, deep=False):
    users = defaultdict(set)
    ancestors = {v:set() for v in puzzle.seeds}
    for out, (_, a, b) in graph.items():
        ancestors[out] = {a,b} | ancestors[a] | ancestors[b]
        for v in {a,b}:
            users[v].add(out)
    wanted = set(puzzle.targets)
    uses = Counter({v:len(u) for v,u in users.items()}) + Counter(wanted)
    groups = set()
    for v in graph.keys() - wanted:
        outgoing = sorted(users[v])
        if 2 <= len(outgoing) <= 8:
            groups.add(tuple(outgoing))
            if len(outgoing) > 2:
                groups.update(combinations(outgoing,2))
    if deep:
        immediate = groups
        groups = set()
        for v in graph.keys() - wanted:
            children = sorted(users[v])
            if not 2 <= len(children) <= 8:
                continue
            for a,b in combinations(children,2):
                left = {a} | users[a]
                right = {b} | users[b]
                if len(left)*len(right)>100:
                    continue
                for x in left:
                    for y in right:
                        if x!=y and x not in ancestors[y] and y not in ancestors[x]:
                            group=tuple(sorted((x,y)))
                            if group not in immediate:
                                groups.add(group)
    options = []
    for group in sorted(groups):
        roots = set(group)
        removed = removable_together(graph,uses,roots)
        if not 2 <= len(removed) <= 4:
            continue
        if any(ancestors[r] & (roots-{r}) for r in roots):
            continue
        affected = removed | roots
        live = {v for r in affected for v in graph[r][1:] if v not in affected}
        if not live or len(live) > 18 or any(ancestors[v] & roots for v in live):
            continue
        safe = {v for v in (set(puzzle.seeds) | graph.keys()) - affected if not ancestors[v] & roots}
        rank = (-len(roots & wanted), -len(removed), len(live), group)
        options.append((rank,group,removed,live,safe))
    return sorted(options)


def anchor_sets(puzzle, graph, roots, live, safe, widths, deep=False):
    usage = Counter(source for _,a,b in graph.values() for source in {a,b})
    ranked = sorted(safe-live,key=lambda v:(v not in puzzle.seeds,-usage[v],v.bit_length(),v))
    near = sorted(safe-live,key=lambda v:(min(abs(v-x) for x in roots).bit_length(),-usage[v],v))
    for extra,width in zip((ranked,near),widths):
        yield tuple(sorted(live | set(extra[:max(0,width-len(live))])))
    if deep:
        targets=set(roots)
        close={}
        for a in safe-live:
            votes=0
            for b in live:
                votes+=sum(result in targets for result,_ in arithmetic_edges(a,b,puzzle.limit))
            close[a]=votes
        if any(close.values()):
            favored=sorted(close,key=lambda v:(-close[v],-usage[v],v))
            yield tuple(sorted(live | set(favored[:max(0,widths[-1]-len(live))])))


def work(task):
    puzzle, parent, engine, count, budget, widths, deep, polish = task
    graph = active_graph(puzzle,first_recipes(puzzle,parent))
    candidates = cuts(puzzle,graph,deep)
    frequency=Counter(v for _,a,b in graph.values() for v in {a,b})
    rows, seen, inputs = [], set(), []
    for _,roots,removed,live,safe in candidates[:count]:
        for seeds in anchor_sets(puzzle,graph,roots,live,safe,widths,deep):
            key = (roots,seeds,len(removed))
            if key in seen:
                continue
            seen.add(key)
            row=dict(roots=roots, seeds=seeds, removed=sorted(removed))
            values = (len(inputs),puzzle.limit,len(seeds),len(roots),
                      min(3,len(removed)) if polish else len(removed)-1,budget,*seeds,*roots)
            if polish:
                excluded=min(removed,key=lambda v:(-frequency[v],v))
                values+= (excluded,)
                row["excluded"]=excluded
            rows.append(row)
            inputs.append(" ".join(map(str,values)))
    best = parent
    alternate={}
    if inputs:
        proc = subprocess.run([str(engine), *(["--exclude"] if polish else [])],input="\n".join(inputs)+"\n",text=True,capture_output=True,check=True,
                              creationflags=getattr(subprocess,"BELOW_NORMAL_PRIORITY_CLASS",0))
        output = proc.stdout.splitlines()
        if len(output) != len(rows):
            raise ValueError("Incomplete batch response")
        for i,(line,row) in enumerate(zip(output,rows)):
            identifier,status,nodes,terminal,*values = line.split()
            if int(identifier) != i or status not in ("FOUND","UNKNOWN","UNSAT"):
                raise ValueError("Invalid batch response")
            row.update(status=status,nodes=int(nodes),terminal=int(terminal))
            if status != "FOUND":
                continue
            sequence = tuple(map(int,values))
            row["sequence"] = sequence
            patch = generate(row["seeds"],puzzle.limit,sequence,row["roots"])
            maximum = len(row["roots"])+len(row["removed"])-int(not polish)
            if len(patch)>maximum or row.get("excluded") in patch:
                raise ValueError("Witness fails the conditional search budget")
            kept = {v:e for v,e in graph.items() if v not in row["removed"]}
            tape = compile_on_parent(puzzle,parent,kept | patch)
            row["physical"] = len(tape) if tape is not None else None
            if tape is not None:
                best = min((best,tape),key=len)
                if polish and len(tape)<=len(parent)+1 and tape!=parent:
                    alternate[tape]=i
    record=dict(before=len(parent),eligible=len(candidates),rows=rows)
    if alternate:
        seed=904321+int(puzzle.id[-4:])
        control=solve(polish,puzzle,[parent],seed,500)
        record["control"]=len(control)
        best=min((best,control),key=len)
        for start in sorted(alternate,key=lambda t:(len(t),alternate[t]))[:2]:
            candidate=solve(polish,puzzle,[start,parent],seed,500)
            rows[alternate[start]]["polished"]=len(candidate)
            best=min((best,candidate),key=len)
    record["after"]=check(puzzle,best)
    return puzzle.id,best,record


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("puzzles","parent","engine","out"):
        cli.add_argument("--"+name,type=Path,required=True)
    for name,default in (("count",50),("cuts",5),("budget",3500),("jobs",8)):
        cli.add_argument("--"+name,type=int,default=default)
    cli.add_argument("--widths",type=int,nargs=2,default=(9,15))
    cli.add_argument("--deep",action="store_true")
    cli.add_argument("--polish",type=Path)
    a = cli.parse_args()
    puzzles = read_puzzles(a.puzzles)
    bank = read_submission(a.parent)
    chosen = sorted((p for p in puzzles if 30 <= len(bank[p.id]) <= 190),
                    key=lambda p:hashlib.sha256(("fanout-exact-"+p.id).encode()).digest())[:a.count]
    tasks = [(p,bank[p.id],a.engine.resolve(),a.cuts,a.budget,a.widths,a.deep,a.polish) for p in chosen]
    rows,wins = {},{}
    with ThreadPoolExecutor(a.jobs) as pool:
        for i,tape,row in pool.map(work,tasks):
            rows[i] = row
            if len(tape)<len(bank[i]):
                wins[i] = tape
                print(i,len(bank[i]),len(tape),flush=True)
    a.out.mkdir(exist_ok=True,parents=True)
    write_submission(a.out/"wins.csv",[p for p in puzzles if p.id in wins],wins)
    report = dict(parent_sha256=sha256(a.parent),engine_sha256=sha256(a.engine),widths=a.widths,
                  budget=a.budget,cuts=a.cuts,rows=rows,deep=a.deep)
    if a.polish:
        report["polish_sha256"]=sha256(a.polish)
        report["rounds"]=500
    (a.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(report,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-len(t) for i,t in wins.items()),
          Counter(r["status"] for p in rows.values() for r in p["rows"]),flush=True)


if __name__ == "__main__":
    main()
