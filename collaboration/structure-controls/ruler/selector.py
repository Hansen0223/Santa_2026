from collections import Counter, defaultdict
from itertools import combinations_with_replacement
from solvers.graphs.corpus_prefix import arithmetic_edges
from solvers.graphs.crossover_lns import load_solver
from elf import check
from graph import active_graph,compile_graph
from solvers.gpu.gpu_schedule import schedule_like

def strong(nodes,edges):
    forward=defaultdict(set);back=defaultdict(set)
    for v in nodes:
        for _,a,b in edges[v]:
            for x in (a,b):
                if x in nodes:forward[x].add(v);back[v].add(x)
    finish=[];seen=set()
    for v in nodes:
        if v in seen:continue
        seen.add(v);stack=[(v,iter(forward[v]))]
        while stack:
            value,children=stack[-1]
            u=next(children,None)
            if u is None:
                finish.append(value);stack.pop()
            elif u not in seen:
                seen.add(u);stack.append((u,iter(forward[u])))
    group={}
    for v in reversed(finish):
        if v in group:continue
        todo=[v];group[v]=v
        while todo:
            for u in back[todo.pop()]:
                if u not in group:group[u]=v;todo.append(u)
    return group

def compile_selection(p,tape,original,supplied,expand,*,omit_old=0,slack=0,hint_graph=None,required_recipes=()):
    cp=load_solver();seeds=set(p.seeds)
    bank=defaultdict(set)
    def canon(e):
        op,a,b=e
        return (op,min(a,b),max(a,b)) if op in '+*' else e
    for v,r in original.items():bank[v].add(canon(r))
    for path in supplied:
        for v,e in path.items():bank[v].add(canon(e))
    vals=set(bank)|seeds
    if expand:
        # Add alternate arithmetic on any supplied new value and any parent value.
        # Leave the definitions of the original parent available in both arms.
        for a,b in combinations_with_replacement(sorted(vals),2):
            for v,r in arithmetic_edges(a,b,p.limit):
                if v in bank and v not in (a,b):bank[v].add(canon(r))
    nodes=set(bank);group=strong(nodes,bank);size=Counter(group.values())
    model=cp.CpModel();pay={v:model.new_bool_var('') for v in sorted(nodes)}
    rank={v:model.new_int_var(0,len(nodes),'') for v in sorted(nodes) if size[group[v]]>1}
    hint=original if hint_graph is None else hint_graph
    positions={v:i for i,v in enumerate(hint)};flags={}
    for v in sorted(nodes):
        choices=[]
        for e in sorted(bank[v]):
            f=pay[v] if len(bank[v])==1 else model.new_bool_var('')
            flags[v,e]=f;choices.append(f)
            for u in set(e[1:])-seeds:
                model.add_implication(f,pay[u])
                if group[v]==group[u]:model.add(rank[u]<rank[v]).only_enforce_if(f)
            if len(bank[v])>1:model.add_hint(f,int(v in hint and canon(hint[v])==e))
        if len(choices)>1:model.add(sum(choices)==pay[v])
        model.add_hint(pay[v],int(v in hint))
        if v in rank:model.add_hint(rank[v],positions.get(v,0))
    for v in set(p.targets)-seeds:model.add(pay[v]==1)
    if required_recipes:
        model.add_bool_or([flags[v,canon(e)] for v,e in required_recipes])
    limit=len(tape)+slack
    if omit_old:
        old=set(original)-set(p.targets)
        model.add(sum(pay[v] for v in old)<=len(old)-omit_old)
    total=sum(pay.values());model.add(total<=limit);model.minimize(total)
    solver=cp.CpSolver();solver.parameters.num_search_workers=1
    solver.parameters.random_seed=619;solver.parameters.max_deterministic_time=.35
    status=solver.solve(model);name=solver.status_name(status)
    r=dict(status=name,values=len(nodes),recipes=len(flags),cyclic_rank_vars=len(rank))
    forced=bool(omit_old or required_recipes)
    best=None if forced else tape
    if status in (cp.OPTIMAL,cp.FEASIBLE):
        select={v:e for (v,e),f in flags.items() if solver.value(f)}
        graph=active_graph(p,select);r['graph']=len(graph)
        if (forced and len(graph)<=limit) or len(graph)<len(tape):
            ts=[schedule_like(p,tape,graph),compile_graph(p,graph,attempts=4,recompute=True,schedule_width=10)]
            ts=[j for j in ts if j and check(p,j)<=(limit if forced else len(tape)-1)]
            if ts:best=min(ts,key=len)
    r['physical']=len(best) if best is not None else None
    return r,best

