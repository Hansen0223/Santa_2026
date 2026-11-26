"""Combine two programs by minimum cut on the private values used by shared outputs."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'collaboration/retained-pool'))
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, compile_graph, first_recipes
from neutral_lead import solve
from solvers.gpu.gpu_schedule import schedule_like


def signature(recipe):
    op,a,b = recipe
    return (op,min(a,b),max(a,b)) if op in '+*' else recipe


def pieces(graph, anchors):
    """Return private descendants and the boundary required by each output."""
    interior, inputs = {},{}
    for v,(_,a,b) in graph.items():
        nodes,ends = set(),set()
        for x in (a,b):
            if x in anchors:
                ends.add(x)
            elif x in graph:
                nodes.add(x)
                nodes.update(interior[x])
                ends.update(inputs[x])
        interior[v],inputs[v] = nodes,ends
    return {v:(interior[v],inputs[v]) for v in anchors}


def assignment(anchors, parts, order):
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import breadth_first_order, maximum_flow
    ids = {v:n for n,v in enumerate(sorted(anchors),2)}
    arcs = Counter()
    bound = 1 + sum(len(values) for part in parts for values,_ in part.values())
    index = len(ids)+2
    for side,part in enumerate(parts):
        owners = defaultdict(list)
        for v,(values,needed) in part.items():
            if any(order[dep]>=order[v] for dep in needed):
                # Left nodes lie on the source side. Forbid this side if it would
                # reverse an anchor dependency in the chosen topological order.
                arcs[(ids[v],1) if side==0 else (0,ids[v])] += bound
            for x in values:
                owners[x].append(ids[v])
        for group in owners.values():
            j = index
            index += 1
            arcs[(j,1) if side==0 else (0,j)] += 1
            for i in group:
                arcs[(i,j) if side==0 else (j,i)] += bound
    if arcs:
        ij = list(arcs)
        network = coo_matrix((list(arcs.values()),tuple(zip(*ij))),shape=(index,index),dtype='int64').tocsr()
        flow = maximum_flow(network,0,1)
        residual = network-flow.flow
        residual.eliminate_zeros()
        reachable = set(breadth_first_order(residual,0,return_predecessors=False))
        cost = int(flow.flow_value)
    else:
        reachable,cost = {0},0
    return {v:int(i not in reachable) for v,i in ids.items()},cost


def materialize(p, graphs, choice):
    # Keep occurrences from both parents until their operands have been emitted.
    # The first completed occurrence of each number is then safe to reuse.
    result = {}
    seen = set()
    for target in p.targets:
        if target not in choice:
            continue
        stack = [(target,choice[target],False)]
        while stack:
            v,side,done = stack.pop()
            side = choice.get(v,side)
            if v in p.seeds or (v,side) in seen:
                continue
            op,a,b = graphs[side][v]
            if done:
                seen.add((v,side))
                result.setdefault(v,(op,a,b))
            else:
                stack.extend([(v,side,True),(a,side,False),(b,side,False)])
    return active_graph(p,result)


def interleaved_orders(anchors, parts, positions):
    """Add anchor orders that can switch between the two parent dependencies."""
    for weight in (1,2,3):
        visited={}
        remaining=set(anchors)
        while remaining:
            ready={}
            for v in remaining:
                permitted=sum(needed<=visited.keys() for _,needed in (part[v] for part in parts))
                if permitted:
                    ready[v]=permitted
            if not ready:
                raise ValueError("No feasible anchor can extend the order")
            v=min(ready,key=lambda v:(-ready[v],
                      weight*positions[0][v]+(4-weight)*positions[1][v],v))
            visited[v]=len(visited)
            remaining.remove(v)
        yield visited


def hybrids(p,base,donor,interleave=False):
    graphs = base,donor
    common = base.keys() & donor.keys()
    goals = set(p.targets)-set(p.seeds)
    uses = Counter(x for g in graphs for _,a,b in g.values() for x in {a,b})
    positions = [{v:i for i,v in enumerate(g)} for g in graphs]
    modes = [('targets',goals),('reused',goals|{v for v in common if uses[v]>=4}),('all',common)]
    seen = set()
    for label,anchors in modes:
        if frozenset(anchors) in seen:
            continue
        seen.add(frozenset(anchors))
        parts = [pieces(g,anchors) for g in graphs]
        orders = list(positions)
        if interleave:
            orders.extend(interleaved_orders(anchors,parts,positions))
        seen_orders=set()
        for side,order in enumerate(orders):
            key=tuple(sorted(anchors,key=order.__getitem__))
            if key in seen_orders and side>=len(positions):
                continue
            seen_orders.add(key)
            selected,cost = assignment(anchors,parts,order)
            g = materialize(p,graphs,selected)
            yield g,dict(boundary=label,order=side,anchors=len(anchors),donor_choices=sum(selected.values()),
                         private_cost=cost,graph=len(g))


def fingerprint(g):
    return frozenset((v,signature(e)) for v,e in g.items())


def work(task):
    p,parent,donors,engine,rounds,*order_modes = task
    base = active_graph(p,first_recipes(p,parent))
    base_edges = fingerprint(base)
    candidates = {}
    report = dict(before=len(parent),pairs=[],starts=[])
    for name,tape in donors:
        graph = active_graph(p,first_recipes(p,tape))
        donor_edges = fingerprint(graph)
        row = dict(donor=name,length=len(tape),cuts=[])
        for g,stats in hybrids(p,base,graph,any(order_modes)):
            key = fingerprint(g)
            stats['mixed'] = bool(key-base_edges and key-donor_edges)
            row['cuts'].append(stats)
            if stats['mixed'] and len(g)<=len(parent)+3:
                candidates.setdefault(key,(g,name,stats['boundary'],stats['order']))
        report['pairs'].append(row)
    best = parent
    seen = []
    warm = []
    for key,(g,name,mode,side) in sorted(candidates.items(),key=lambda item:len(item[1][0])):
        if any(len(key^s)<3 for s in seen):
            continue
        tape = compile_graph(p,g,attempts=5)
        if tape is None or len(tape)>len(g):
            alt = schedule_like(p,parent,g)
            if alt is not None and (tape is None or len(alt)<len(tape)):
                tape = alt
        if tape is None or len(tape)>len(parent)+3:
            continue
        seen.append(key)
        warm.append((tape,name,mode,side))
        if len(warm)==3:
            break
    if warm:
        seed = 830009+int(p.id[-4:])
        control = solve(engine,p,[parent],seed,rounds) if rounds else parent
        best = min((parent,control),key=len)
        report['control'] = len(control)
        if len(control)<len(parent):
            report['winner'] = 'control'
        for tape,name,mode,side in warm:
            searched = solve(engine,p,[tape],seed,rounds) if rounds else tape
            candidate = min((tape,searched),key=len)
            report['starts'].append(dict(donor=name,boundary=mode,order=side,physical=len(tape),searched=len(searched)))
            if len(candidate)<len(best):
                best = candidate
                report['winner'] = name
    check(p,best)
    report['after'] = len(best)
    return p.id,best,report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('puzzles','parent','engine','out'):
        parser.add_argument('--'+flag,type=Path,required=True)
    parser.add_argument('--donors',type=Path,nargs='+',required=True)
    for name,n in [('count',90),('offset',0),('jobs',6),('pairs',3),('rounds',350)]:
        parser.add_argument('--'+name,type=int,default=n)
    parser.add_argument('--method',choices=('cut','shared-outputs'),default='cut')
    parser.add_argument("--interleave-orders",action="store_true")
    parser.add_argument("--rank-divergence",action="store_true")
    parser.add_argument("--max-gap",type=int)
    args = parser.parse_args()
    if args.interleave_orders and args.method!="cut":
        parser.error("--interleave-orders requires --method cut")
    puzzles = read_puzzles(args.puzzles)
    parent_digest=sha256(args.parent)
    bank = read_submission(args.parent)
    if sha256(args.parent)!=parent_digest:
        raise ValueError('Parent changed while loading')
    donors = {path.name:read_submission(path) for path in args.donors}
    if len(donors)!=len(args.donors):
        raise ValueError('Donors need distinct file names')
    worker = work
    salt = 'cutmix1-'
    if args.method=='shared-outputs':
        from shared_outputs import work as worker
        salt = 'shared-outputs1-'
    jobs = []
    priorities = {}
    for p in sorted(puzzles,key=lambda x:hashlib.sha256((salt+x.id).encode()).digest()):
        parent = bank[p.id]
        if len(parent)<20:
            continue
        base = fingerprint(first_recipes(p,parent))
        options = {}
        for name,source in donors.items():
            tape = source.get(p.id)
            if tape is None or tape==parent or len(tape)>len(parent)*1.45+12:
                continue
            if args.max_gap is not None and len(tape)-len(parent)>args.max_gap:
                continue
            edges = fingerprint(first_recipes(p,tape))
            diff = len(edges^base)
            if diff>=3:
                rank = (1+max(0,len(tape)-len(parent)))/min(150,diff)**.65
                options.setdefault(edges,(rank,name,tape))
        if options:
            best = sorted(options.values(),key=lambda t:(t[0],t[1]))[:args.pairs]
            priorities[p.id]=best[0][0]
            job=(p,parent,[(n,t) for _,n,t in best],args.engine,args.rounds)
            jobs.append((*job, True) if args.interleave_orders else job)
    if args.rank_divergence:
        jobs.sort(key=lambda task:(priorities[task[0].id],task[0].id))
    wins,rows = {},{}
    with ProcessPoolExecutor(args.jobs) as pool:
        for i,t,row in pool.map(worker,jobs[args.offset:args.offset+args.count]):
            rows[i] = row
            if len(t)<len(bank[i]):
                wins[i] = t
    args.out.mkdir(exist_ok=True,parents=True)
    write_submission(args.out/'wins.csv',[p for p in puzzles if p.id in wins],wins)
    record = dict(method=args.method,eligible=len(jobs),parent_sha256=parent_digest,engine_sha256=sha256(args.engine),
                  donors={f.name:sha256(f) for f in args.donors},
                  settings={k:v for k,v in vars(args).items() if isinstance(v,int)},rows=rows)
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(record,separators=(',',':')).encode(),mtime=0))
    print(len(rows),len(wins),sum(len(bank[i])-len(t) for i,t in wins.items()))


if __name__=='__main__':
    main()
