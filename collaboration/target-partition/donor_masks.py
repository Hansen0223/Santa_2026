"""Prioritize target groups that share an intermediate in an alternative program."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from elf import check,read_puzzles,read_submission,sha256,write_submission
from graph import active_graph,first_recipes

SOURCE = 'goodpjw_first_improvement.cpp'
SOURCE_SHA = 'c36dad9b23f91a3588860f64cf63b56469516391b81c67d1c5cea960117f4ecc'


def build_source(archive, out):
    with zipfile.ZipFile(archive) as f:
        raw = f.read(SOURCE)
    if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA:
        raise ValueError('Expected the fixed E-Max AI and GoodPJW source')
    source = raw.decode().replace('\r\n','\n')
    edits = [
        ('struct Puzzle { string id;', 'struct Puzzle { vector<u64> suggested; string id;'),
        ('    return true;\n}\n\n// ---------------------------------------------------------------- constructive builder',
         '    int count; if (!(in >> count) || count < 0 || count > 16) return false;\n'
         '    p.suggested.resize(count); for (auto& m : p.suggested) if (!(in >> m)) return false;\n'
         '    return true;\n}\n\n// ---------------------------------------------------------------- constructive builder'),
        ('            sort(cand.begin(), cand.end());',
         '            for (size_t j = 0; j < P.suggested.size(); ++j) {\n'
         '                u64 m = P.suggested[j];\n'
         '                cand.erase(remove_if(cand.begin(), cand.end(), [m](const auto& x) { return x.second == m; }), cand.end());\n'
         '                cand.push_back({double(j) - double(P.suggested.size()), m});\n'
         '            }\n            sort(cand.begin(), cand.end());')]
    for before,after in edits:
        if source.count(before)!=1:
            raise ValueError('Source changed')
        source = source.replace(before,after)
    out.write_bytes(source.encode())


def groups(p,tape):
    graph = active_graph(p,first_recipes(p,tape))
    targets = list(dict.fromkeys(v for v in p.targets if v not in p.seeds))
    bits = {v:1<<j for j,v in enumerate(targets)}
    for v,(_,a,b) in reversed(graph.items()):
        m = bits.get(v,0)
        bits[a] = bits.get(a,0)|m
        bits[b] = bits.get(b,0)|m
    return Counter(bits[v] for v in graph if 2<=bits[v].bit_count()<=5)


def search(exe,p,tape,masks,seconds):
    header = ['P',p.id,len(p.seeds),*p.seeds,len(p.targets),*p.targets,p.limit,p.registers,len(tape)]
    lines = [' '.join(map(str,header)),*(' '.join(map(str,op)) for op in tape),' '.join(map(str,[len(masks),*masks]))]
    proc = subprocess.run([str(exe),'--time',str(seconds),'--seed',str(87533+int(p.id[-4:])),
                           '--kicks','1000','--kslack','2','--helpers','0','--group','5'],
                          input='\n'.join(lines)+'\n',text=True,capture_output=True,check=True)
    if p.id not in proc.stderr:
        raise ValueError('Solver did not process '+p.id)
    if not proc.stdout.strip():
        return tape
    words = proc.stdout.split()
    candidate = tuple((words[j],*map(int,words[j+1:j+4])) for j in range(4,len(words),4))
    if words[:3]!=['R',p.id,str(len(tape))] or check(p,candidate)!=int(words[3]):
        raise ValueError(p.id)
    return candidate


def work(job):
    p,tape,options,exe,seconds = job
    control = search(exe,p,tape,[],seconds)
    changed = search(exe,p,tape,[m for m,_ in options],seconds)
    return p.id,min((control,changed),key=len),dict(before=len(tape),control=len(control),
              treatment=len(changed),groups=[[m,names] for m,names in options])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    modes=ap.add_subparsers(dest='action',required=True)
    build=modes.add_parser('build-source')
    build.add_argument('archive',type=Path);build.add_argument('out',type=Path)
    run=modes.add_parser('search')
    for n in ('puzzles','parent','exe','out'):
        run.add_argument('--'+n,type=Path,required=True)
    run.add_argument('--donors',nargs='+',type=Path,required=True)
    for key,n in [('count',60),('offset',0),('jobs',6),('seconds',5)]:
        run.add_argument('--'+key,type=int,default=n)
    args=ap.parse_args()
    if args.action=='build-source':
        build_source(args.archive,args.out)
        return
    ps=read_puzzles(args.puzzles);bank=read_submission(args.parent)
    donors={d.name:read_submission(d) for d in args.donors}
    if len(donors)!=len(args.donors):
        raise ValueError('Use distinct donor file names')
    jobs=[]
    for p in sorted(ps,key=lambda p:hashlib.sha256(('mask-transfer-'+p.id).encode()).digest()):
        tape=bank[p.id]
        if len(tape)<30 or len(p.targets)>63:
            continue
        incumbent=groups(p,tape)
        prices=Counter();sources={}
        for name,d in donors.items():
            alt=d.get(p.id)
            if not alt or alt==tape or len(alt)>len(tape)+45:
                continue
            for m,count in groups(p,alt).items():
                if m in incumbent:
                    continue
                prices[m]+=min(count,5)
                sources.setdefault(m,[]).append(name)
        if prices:
            best=sorted(prices,key=lambda m:(-prices[m],m.bit_count(),m))[:6]
            jobs.append((p,tape,[(m,sources[m]) for m in best],args.exe,args.seconds))
    wins,rows={},{}
    with ThreadPoolExecutor(args.jobs) as pool:
        for i,t,row in pool.map(work,jobs[args.offset:args.offset+args.count]):
            rows[i]=row
            if len(t)<len(bank[i]):
                wins[i]=t
    args.out.mkdir(exist_ok=True,parents=True)
    write_submission(args.out/'wins.csv',[p for p in ps if p.id in wins],wins)
    info=dict(eligible=len(jobs),exe_sha256=sha256(args.exe),parent_sha256=sha256(args.parent),
              donors={d.name:sha256(d) for d in args.donors},settings={k:v for k,v in vars(args).items() if isinstance(v,int)},rows=rows)
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(info,separators=(',',':')).encode(),mtime=0))
    print(len(rows),len(wins),sum(len(bank[i])-len(t) for i,t in wins.items()))


if __name__=='__main__':
    main()
