"""Rebuild addition/subtraction regions by synthesizing the transposed signed linear map."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from elf import check, read_puzzles, read_submission, write_submission
from graph import active_graph, compile_graph, first_recipes
from solvers.gpu.gpu_schedule import schedule_like


def signed_pair(a, b):
    pair = tuple(sorted((a, b), key=lambda x: (abs(x), x)))
    if pair[-1] < 0:
        return (-pair[0], -pair[1]), -1
    return pair, 1


class SumCircuit:
    def __init__(self, inputs):
        self.inputs = inputs
        self.gates = []
        self.lookup = {}

    def add(self, a, b):
        if not a or not b or a == -b:
            return a + b
        key, sign = signed_pair(a, b)
        if key not in self.lookup:
            self.gates.append(key)
            self.lookup[key] = self.inputs + len(self.gates)
        return sign * self.lookup[key]

    def outputs(self, rows):
        terms = []
        for row in rows:
            vector = []
            for index, coefficient in sorted(row.items()):
                power, n = index + 1, abs(coefficient)
                while n:
                    if n % 2:
                        digit = 2 - n % 4
                        vector.append(power * digit * (1 if coefficient > 0 else -1))
                        n -= digit
                    n //= 2
                    if n:
                        power = self.add(power, power)
            terms.append(vector)
        while True:
            counts = Counter()
            for vector in terms:
                counts.update({signed_pair(a,b)[0] for a,b in itertools.combinations(vector,2) if a != -b})
            if not counts or max(counts.values()) < 2:
                break
            (a,b), _ = min(counts.items(),key=lambda item:(-item[1], item[0]))
            value = self.add(a,b)
            for vector in terms:
                for sign in (1,-1):
                    x,y=sign*a,sign*b
                    while x in vector and y in vector and (x!=y or vector.count(x)>=2):
                        vector.remove(x)
                        vector.remove(y)
                        vector.append(sign*value)
        results=[]
        for vector in terms:
            vector.sort(key=lambda x:(abs(x),x))
            while len(vector)>1:
                a,b=vector.pop(0),vector.pop(0)
                value=self.add(a,b)
                if value:
                    vector.append(value)
            results.append(vector[0] if vector else 0)
        return results


class BoundedSum:
    def __init__(self, free, limit):
        self.free = free
        self.limit = limit
        self.graph = {}

    def known(self, v):
        return v == 0 or abs(v) in self.free or abs(v) in self.graph

    def total(self, values):
        final = sum(values)
        if abs(final)>self.limit:
            raise OverflowError
        if self.known(final):
            return final
        counts = Counter(values)
        work = []
        for n in sorted({abs(v) for v in values if v}):
            count=counts[n]-counts[-n]
            work.extend([n if count>0 else -n]*abs(count))
        while len(work)>1:
            options=((not self.known(a+b), bool(a*b>0), abs(a+b), i, j)
                     for i,a in enumerate(work) for j,b in enumerate(work[:i])
                     if abs(a+b)<=self.limit)
            best=min(options,default=None)
            if best is None:
                raise OverflowError
            _,_,_,i,j=best
            a,b=work.pop(i),work.pop(j)
            s=a+b
            if not self.known(s):
                x,y=sorted((abs(a),abs(b)),reverse=True)
                self.graph[abs(s)]=('+' if a*b>0 else '-',x,y)
            if s:
                work.append(s)
        return final


def synthesize(puzzle, graph, region, ports, transposed):
    atoms=sorted({u for v in region for u in graph[v][1:] if u not in region})
    if len(atoms)<2:
        return None
    positions={v:i for i,v in enumerate(atoms)}
    forms={v:{k:1} for v,k in positions.items()}
    for v,(op,a,b) in graph.items():
        if v not in region:
            continue
        row=Counter(forms[a])
        for k,coef in forms[b].items():
            row[k]+=coef if op=='+' else -coef
        forms[v]={k:c for k,c in row.items() if c}
        if len(forms[v])>24 or any(abs(c)>1024 for c in forms[v].values()):
            return None
    rows=[forms[v] for v in ports]
    if sum(len(row) for row in rows)>180:
        return None
    blocked=set(region)
    for v,(_,a,b) in graph.items():
        if a in blocked or b in blocked:
            blocked.add(v)
    emit=BoundedSum(set(puzzle.seeds)|(graph.keys()-blocked),puzzle.limit)
    if transposed:
        columns=[{} for _ in atoms]
        for j,row in enumerate(rows):
            for i,c in row.items():
                columns[i][j]=c
        dual=SumCircuit(len(ports))
        endpoints=dual.outputs(columns)
        incoming=defaultdict(list)
        for x,endpoint in zip(atoms,endpoints):
            if endpoint:
                incoming[abs(endpoint)].append(x if endpoint>0 else -x)
        for j in range(len(dual.gates)-1,-1,-1):
            value=emit.total(incoming.pop(dual.inputs+j+1,[]))
            if value:
                for port in dual.gates[j]:
                    incoming[abs(port)].append(value if port>0 else -value)
        got=[emit.total(incoming[j+1]) for j in range(len(ports))]
    else:
        circuit=SumCircuit(len(atoms))
        endpoints=circuit.outputs(rows)
        values=[0]+atoms
        def signed(i):return values[abs(i)] if i>=0 else -values[-i]
        for a,b in circuit.gates:
            values.append(emit.total([signed(a),signed(b)]))
        got=[signed(i) for i in endpoints]
    if got!=ports:
        raise ValueError('Linear map reconstruction failed')
    return emit.graph


def regions(puzzle, graph):
    linear={v for v,rec in graph.items() if rec[0] in '+-'}
    adj=defaultdict(set)
    users=defaultdict(set)
    for v,(_,x,y) in graph.items():
        for a in {x,y}:
            users[a].add(v)
            if a in linear and v in linear:
                adj[v].add(a)
                adj[a].add(v)
    candidates=set()
    unseen=set(linear)
    order={v:k for k,v in enumerate(graph)}
    while unseen:
        root=min(unseen)
        component={root}
        stack=[root]
        unseen.remove(root)
        while stack:
            fresh=adj[stack.pop()]&unseen
            unseen-=fresh
            component|=fresh
            stack.extend(fresh)
        if len(component)<4:
            continue
        seq=sorted(component,key=order.get)
        if len(seq)<=44:
            candidates.add(frozenset(seq))
        for size in (8,16,28):
            if len(seq)>size:
                candidates.update(frozenset(seq[i:i+size]) for i in range(0,len(seq)-3,max(1,size//2)))
    choices=[]
    for region in candidates:
        ports=sorted(v for v in region if v in puzzle.targets or users[v]-region)
        if len(ports)>=2 and len(region)-len(ports)>=2:
            choices.append((region,ports))
    return sorted(choices,key=lambda x:(-(len(x[0])-len(x[1])),tuple(sorted(x[0]))))


def search(job):
    puzzle,tape,limit=job
    g=active_graph(puzzle,first_recipes(puzzle,tape))
    best_by_mode=[]
    winners=[]
    region_list=regions(puzzle,g)[:limit]
    for transpose in (False,True):
        best=tape
        stats=Counter()
        for reg,ports in region_list:
            try:
                fragment=synthesize(puzzle,g,reg,ports,transpose)
            except OverflowError:
                continue
            if fragment is None:
                continue
            stats['built']+=1
            proposal=g|fragment
            try:
                reachable=active_graph(puzzle,proposal)
            except (KeyError,ValueError):
                continue
            stats['acyclic']+=1
            if len(reachable)>=len(best):
                continue
            candidate=compile_graph(puzzle,reachable,attempts=5)
            if candidate is None:
                candidate=schedule_like(puzzle,tape,reachable)
            if candidate and len(candidate)<len(best):
                check(puzzle,candidate)
                best=candidate
        winners.append(best)
        best_by_mode.append(dict(stats,steps=len(best)))
    return puzzle.id,min(winners,key=len),dict(before=len(tape),regions=len(region_list),
                                              forward=best_by_mode[0],transposed=best_by_mode[1])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('puzzles','parent','out'):
        ap.add_argument('--'+key,required=True,type=Path)
    ap.add_argument('--count',type=int,default=48)
    ap.add_argument('--offset',type=int,default=0)
    ap.add_argument('--regions',type=int,default=12)
    ap.add_argument('--jobs',type=int,default=8)
    args=ap.parse_args()
    puzzles=read_puzzles(args.puzzles)
    parent_hash=hashlib.sha256(args.parent.read_bytes()).hexdigest()
    parent=read_submission(args.parent)
    eligible=sorted((p for p in puzzles if len(parent[p.id])>=35),
                    key=lambda p:hashlib.sha256(('dual-'+p.id).encode()).digest())
    group=eligible[args.offset:args.offset+args.count]
    rows,wins={},{}
    with ProcessPoolExecutor(args.jobs) as pool:
        for i,t,rec in pool.map(search,[(p,parent[p.id],args.regions) for p in group]):
            rows[i]=rec
            if len(t)<len(parent[i]):
                wins[i]=t
    args.out.mkdir(exist_ok=True,parents=True)
    write_submission(args.out/'wins.csv',[p for p in puzzles if p.id in wins],wins)
    result=dict(parent_sha256=parent_hash,regions_per_puzzle=args.regions,rows=rows)
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(result,separators=(',',':')).encode(),mtime=0))
    print(len(rows),'puzzles',sum(len(parent[i])-len(t) for i,t in wins.items()),'steps saved')


if __name__=='__main__':
    main()
