"""Search with temporary starting values taken from another historical program."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
import io
import json
from pathlib import Path
import subprocess

import compare as borrowed

FROZEN="aacd89c"
HISTORY=[("8bde969","public-assisted/"),("8a031bc","public-assisted/"),
         ("138be6d","public-assisted/"),("2488949","public-assisted/"),
         ("1fb2d8c","public-assisted/"),(FROZEN,"")]


def table(ref,name):
    raw=subprocess.check_output(["git","show",ref+":"+name],cwd=borrowed.ROOT)
    return {r["id"]:r for r in csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))}


def tape(r):
    return tuple(map(tuple,json.loads(r["program"])))


def choose(p,original,parents):
    known=set(p.seeds)|set(original)
    goals=set(p.targets)
    frequency=Counter(v for _,_,graph in parents for v in graph if v not in known)
    options=[]
    for source,credit,graph in parents:
        users=Counter(v for _,a,b in graph.values() for v in {a,b})
        plans={}
        costs={}
        for v,(_,a,b) in graph.items():
            if v in known:
                costs[v]=frozenset()
            else:
                costs[v]=costs.get(a,frozenset())|costs.get(b,frozenset())|{v}
            if v in known or len(costs[v])>10 or users[v]<2:
                continue
            direct=sum(1 for t in goals if t in graph and v in graph[t][1:])
            plans[v]=users[v]+3*direct+2*min(4,frequency[v]-1)
        chosen=[];spent=set()
        while len(chosen)<4:
            rem=[v for v in plans if v not in chosen and len(spent|costs[v])<=17]
            if not rem:break
            v=max(rem,key=lambda x:(plans[x]/(1+len(costs[x]-spent)),plans[x],-x))
            chosen.append(v);spent.update(costs[v])
        if len(chosen)>=2:
            strength=sum(plans[v] for v in chosen)/(2+len(spent))
            options.append((strength,source,credit,graph,chosen))
    return max(options,key=lambda v:(v[0],v[1])) if options else None


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--puzzles",type=Path,required=True);cli.add_argument("--exe",type=Path,required=True)
    cli.add_argument("--out",type=Path,required=True);cli.add_argument("--jobs",type=int,default=6)
    args=cli.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    base=table(FROZEN,"public-assisted/submission.csv")
    basecredit=table(FROZEN,"public-assisted/origins.csv")
    donors=[(rev+"/"+pre,table(rev,pre+"submission.csv"),table(rev,pre+"origins.csv")) for rev,pre in HISTORY]
    ps=borrowed.read_puzzles(args.puzzles);pm={p.id:p for p in ps};cases=[]
    for p in sorted(ps,key=lambda q:borrowed.digest(["recovered-hubs-1",q.id])):
        if not 6<=len(p.targets)<=40 or len(p.seeds)+4>p.registers:continue
        initial=tape(base[p.id])
        if not 60<=len(initial)<=235:continue
        original=borrowed.active_graph(p,borrowed.first_recipes(p,initial))
        graphs=[];seen={frozenset(original.items())}
        for source,tab,ledger in donors:
            t=tape(tab[p.id]);graph=borrowed.active_graph(p,borrowed.first_recipes(p,t))
            key=frozenset(graph.items())
            if key not in seen:
                seen.add(key);graphs.append((source,ledger[p.id].get("upstream_source") or "Generated from official inputs",graph))
        candidate=choose(p,original,graphs)
        if candidate:
            cases.append((p,initial,original,candidate))
            if len(cases)==48:break
    design=dict(base=FROZEN,donors=HISTORY,development=[p.id for p,*_ in cases[:16]],holdout=[p.id for p,*_ in cases[16:]],rounds=400)
    (args.out/"design.json").write_bytes((json.dumps(design,indent=2)+"\n").encode())
    def run(case):
        p,initial,original,(_,source,credit,other,chosen)=case
        _,flat=borrowed.initial_values(p,original)
        support=borrowed.active_graph(p,other,chosen)
        anchors={h:other[h] for h in chosen}
        result=dict(id=p.id,initial=len(initial),source=source,source_credit=credit,chosen=chosen,
                    initial_sha256=borrowed.digest(initial),support_steps=len(support),arms={})
        for label,values,store in [("direct",{},{}),("fresh",flat,{}),("historical",anchors,support)]:
            arm="fresh" if values else "ordinary"
            _,_,row=borrowed.trial((p,initial,arm,[],values,args.exe.resolve()),seed_label="recovered-hubs-1",rounds=400,donor_prefix=store)
            result["arms"][label]=row
        return result
    summary={}
    for phase,group in [("development",cases[:16]),("holdout",cases[16:])]:
        with ThreadPoolExecutor(args.jobs) as pool: rows=list(pool.map(run,group))
        total=Counter();wins={};ledger=[];beats=[]
        for row in rows:
            i=row["id"];base_len=row["initial"];arms=row["arms"];winner=min(arms,key=lambda k:arms[k]["score"])
            for name,z in arms.items():total[name]+=base_len-z["score"]
            if arms["historical"]["score"]<min(arms["fresh"]["score"],arms["direct"]["score"]):beats.append(i)
            if arms[winner]["score"]<base_len:
                t=tuple(map(tuple,arms[winner]["program"]));assert borrowed.check(pm[i],t)==arms[winner]["score"];wins[i]=t
                cr=basecredit[i].get("upstream_source") or "Generated from official inputs"
                if winner=="historical":cr+="; "+row["source"]+" "+row["source_credit"]
                ledger.append((i,cr))
        borrowed.write_submission(args.out/(phase+".csv"),[pm[i] for i in sorted(wins)],wins)
        with (args.out/(phase+".origins.csv")).open("w",encoding="utf8",newline="") as fh:
            writer=csv.writer(fh);writer.writerow(["id","upstream_source"]);writer.writerows(ledger)
        summary[phase]=dict(cases=len(group),savings=dict(total),better_than_controls=beats,wins={i:len(t) for i,t in wins.items()})
        borrowed.save(args.out/(phase+".json.gz"),rows);borrowed.save(args.out/"summary.json",summary);print(phase,summary[phase],flush=True)


if __name__=="__main__":
    main()
