"""Optimize with temporary starting values, then pay for their construction in the official puzzle."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import csv
from dataclasses import replace
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from checkpoint import independent_score
from elf import check, read_puzzles, sha256, write_submission
from graph import active_graph, compile_graph, first_recipes
from solvers.graphs.corpus_prefix import arithmetic_edges
from solvers.gpu.pooled_joins import inverse

spec = importlib.util.spec_from_file_location('target_partition', HERE.parent/'target-partition/compare.py')
partition = importlib.util.module_from_spec(spec)
spec.loader.exec_module(partition)
BASE = '8bde969fd6ae4ddc3bf1cbd2065f6cc15c9dce6e'
ARMS = ('ordinary', 'incumbent', 'fresh')
ROUNDS = 240


def digest(value):
    return hashlib.sha256(json.dumps(value, separators=(',', ':')).encode()).hexdigest()


def frozen(path):
    raw = subprocess.check_output(['git', 'show', BASE+':'+path], cwd=ROOT)
    return {r['id']: r for r in csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))}


def initial_values(p, graph):
    seeds = set(p.seeds)
    uses = Counter(v for recipe in graph.values() for v in recipe[1:])
    clos = {v: frozenset() for v in seeds}
    for v, (_, a, b) in graph.items():
        clos[v] = (clos[a] | clos[b]) | {v}
    # Rank single-step access to old values by their possible independent cost.
    depth_order = sorted(graph, key=lambda v: (len(clos[v]), -uses[v], v))
    old = sorted((v for v in graph if v not in p.targets and uses[v] >= 2),
                 key=lambda v: (-(uses[v]-1)*min(10, len(clos[v])), len(clos[v]), v))[:4]
    early = list(dict.fromkeys((*p.seeds, *depth_order[:14])))
    recipes = {}
    for j, a in enumerate(early):
        for b in early[:j+1]:
            for v, recipe in arithmetic_edges(a, b, p.limit):
                if v in graph or v in seeds:
                    continue
                price = 1 + len(clos[a] | clos[b])
                if v not in recipes or (price, recipe) < recipes[v]:
                    recipes[v] = (price, recipe)
    hits = defaultdict(dict)
    for t in graph:
        if len(clos[t]) < 3:
            continue
        for a in (*early, *p.targets):
            if a == t:
                continue
            for v, _ in inverse(t, a, p.limit):
                if v in recipes and v != a and v != t:
                    _, (_, x, y) = recipes[v]
                    if t in clos[x] or t in clos[y] or t in clos.get(a, ()):
                        continue
                    hits[v][t] = max(hits[v].get(t, 0),
                                     1 + min(8, len(clos[t])) + 2*(t in p.targets))
    fresh = sorted(hits, key=lambda v: (-sum(hits[v].values())/recipes[v][0],
                                         -len(hits[v]), recipes[v][0], v))[:4]
    return old, {v: recipes[v][1] for v in fresh}


def trial(job, seed_label='borrow-1', rounds=ROUNDS, donor_prefix=None):
    p, tape, arm, old, fresh, exe = job
    graph = active_graph(p, first_recipes(p, tape))
    seeds = [int(digest([seed_label, p.id, j])[:8], 16) for j in (1, 2)]
    options = [tape]
    if arm == 'ordinary':
        first = partition.run_native(p, tape, exe, seeds[0], rounds)
        restored = first
        used = []
    else:
        anchors = old if arm == 'incumbent' else list(fresh)
        aug = replace(p, seeds=(*p.seeds, *anchors))
        start = compile_graph(aug, graph, recompute=True, schedule_width=3)
        if start is None or len(start) > len(tape):
            start = tape
        first = partition.run_native(aug, start, exe, seeds[0], rounds)
        body = active_graph(aug, first_recipes(aug, first))
        used = sorted(set(anchors) & (set(p.targets) | {v for edge in body.values() for v in edge[1:]}))
        bank = graph | (fresh if arm == 'fresh' else {})
        if donor_prefix:
            prefix = active_graph(p, donor_prefix, used)
            bank = bank | prefix
        else:
            prefix = active_graph(p, bank, used)
        restored_options = []
        for candidate in (bank | body, body | prefix):
            restored_tape = compile_graph(p, candidate, recompute=True, schedule_width=4)
            if restored_tape is not None:
                restored_options.append(restored_tape)
        restored = min(restored_options, key=len, default=tape)
    options.append(restored)
    last = partition.run_native(p, restored if len(restored) <= len(tape)+4 else tape, exe, seeds[1], rounds)
    options.append(last)
    best = min(options, key=len)
    assert check(p, best) == len(best)
    row = dict(before=len(tape), temporary_score=len(first), used=used, restored=len(restored),
               score=len(best), hash=digest(best))
    if len(best) < len(tape):
        row['program'] = best
    return p.id, arm, row


def save(path, obj):
    raw = (json.dumps(obj, separators=(',', ':'))+'\n').encode()
    path.write_bytes(gzip.compress(raw, mtime=0) if path.suffix=='.gz' else raw)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('puzzles', 'out'):
        ap.add_argument('--'+name, type=Path, required=True)
    ap.add_argument('--exe', type=Path)
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--phase', choices=('development', 'holdout', 'expand'), required=True)
    ap.add_argument('--block', type=int, default=0)
    ap.add_argument('--lane', choices=('own','public'), required=True)
    ap.add_argument('--replay-only', action='store_true')
    a = ap.parse_args()
    assert a.jobs > 0 and a.block >= 0
    assert sha256(a.puzzles) == 'b0c70d849eca078a0e1cf9a4f7b47fd40b7435663f6f84de6725f84724500428'
    a.out.mkdir(parents=True, exist_ok=True)
    prefix = '' if a.lane == 'own' else 'public-assisted/'
    programs = {i: tuple(tuple(x) for x in json.loads(row['program'])) for i, row in frozen(prefix+'submission.csv').items()}
    origins = frozen(prefix+'origins.csv')
    ps = read_puzzles(a.puzzles)
    eligible = sorted((p for p in ps if 6 <= len(p.targets) <= 45 and 45 <= len(programs[p.id]) <= 275
                       and len(p.seeds)+4 <= p.registers), key=lambda p: digest(['borrow-1', a.lane, p.id]))
    start, stop = {'development': (0, 12), 'holdout': (12,36), 'expand': (36+a.block*48,84+a.block*48)}[a.phase]
    selected = eligible[start:stop]
    assert selected
    stem = f'{a.lane}-{a.phase}' + (f'-{a.block:02d}' if a.phase=='expand' else '')
    packet = a.out/(stem+'.json.gz')
    if not a.replay_only:
        if a.exe is None:
            ap.error('--exe is required for a new search')
        jobs = []
        records = {}
        for p in selected:
            tape = programs[p.id]
            old, fresh = initial_values(p, active_graph(p, first_recipes(p, tape)))
            jobs.extend((p, tape, arm, old, fresh, a.exe.resolve()) for arm in ARMS)
            records[p.id] = dict(incumbent=old, fresh=fresh, parent=digest(tape), arms={})
        with ThreadPoolExecutor(a.jobs) as pool:
            for i, arm, row in pool.map(trial, jobs):
                records[i]['arms'][arm] = row
        save(packet, records)
    records = json.loads(gzip.decompress(packet.read_bytes()))
    assert records.keys() == {p.id for p in selected}
    wins = {}
    totals = Counter()
    beats = []
    for p in selected:
        tape = programs[p.id]
        r = records[p.id]
        assert r['parent'] == digest(tape) and set(r['arms']) == set(ARMS)
        for name, row in r['arms'].items():
            candidate = tuple(tuple(x) for x in row.get('program', tape))
            assert check(p,candidate) == row['score'] <= len(tape) and digest(candidate) == row['hash']
            totals[name] += len(tape)-len(candidate)
        best = min(r['arms'].values(), key=lambda row: row['score'])
        if best['score'] < r['arms']['ordinary']['score']:
            beats.append(p.id)
        if best['score'] < len(tape):
            wins[p.id] = tuple(tuple(x) for x in best['program'])
    with TemporaryDirectory(dir=a.out) as temp:
        merged = Path(temp)/'full.csv'
        score = write_submission(merged, ps, programs|wins)
        assert score == sum(independent_score(a.puzzles, merged))
    write_submission(a.out/(stem+'.csv'), [p for p in selected if p.id in wins], wins)
    with (a.out/(stem+'.origins.csv')).open('w', encoding='utf8', newline='') as file:
        w = csv.writer(file); w.writerow(('id','source','upstream_source','instructions'))
        for i, tape in sorted(wins.items()):
            credit = origins[i].get('upstream_source') or origins[i]['source']
            w.writerow((i, 'temporary starting values and matched ordinary search',
                        'Local search on '+BASE+' row. Parent credit: '+credit, len(tape)))
    report = dict(eligible=len(eligible), tested=len(selected), improved=len(wins),
                  savings=dict(totals), saved=sum(len(programs[i])-len(t) for i,t in wins.items()),
                  beats_ordinary=beats, score=score)
    save(a.out/(stem+'.json'), report)
    print(stem, report, flush=True)


if __name__ == '__main__':
    main()
