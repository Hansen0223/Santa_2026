"""Replace a small connected region by a shared value and new formulas for its outgoing uses."""
import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
import gzip
import hashlib
import json
from math import isqrt
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from elf import check, read_puzzles, read_submission, write_submission
from graph import active_graph, compile_graph, first_recipes
from solvers.gpu.gpu_schedule import schedule_like


def inverse(target, known, limit):
    if target > known:
        yield target - known, ('+', target - known, known)
    if target + known <= limit:
        yield target + known, ('-', target + known, known)
    if known > target:
        yield known - target, ('-', known, known - target)
    if target % known == 0:
        yield target // known, ('*', target // known, known)
    if target * known <= limit:
        yield target * known, ('/', target * known, known)
    if known % target == 0:
        yield known // target, ('/', known, known // target)


def search(job):
    puzzle, program, max_cuts = job
    graph = active_graph(puzzle, first_recipes(puzzle, program))
    bits = {v: 1 << k for k, v in enumerate(graph)}
    ancestors = dict.fromkeys(puzzle.seeds, 0)
    users = defaultdict(set)
    for v, (_, a, b) in graph.items():
        ancestors[v] = bits[v] | ancestors[a] | ancestors[b]
        users[a].add(v)
        users[b].add(v)
    targets = set(puzzle.targets)
    regions = set()
    for v in graph.keys() - targets:
        if not users[v] or len(users[v]) > 5:
            continue
        regions.add(frozenset([v]))
        for child in users[v] - targets:
            regions.add(frozenset([v, child]))
        if len(users[v]) <= 3 and not users[v] & targets:
            regions.add(frozenset({v} | users[v]))

    def outgoing(region):
        return set.union(*(users[v] for v in region)) - region

    def rank(region):
        ports = outgoing(region)
        return abs(3 - len(ports)), -len(region), tuple(sorted(region))

    @lru_cache(maxsize=None)
    def alternatives(value):
        return [(hub, known, recipe) for known in ancestors
                for hub, recipe in inverse(value, known, puzzle.limit) if hub != value]

    best = program
    tested = joined = graphs = 0
    for region in sorted(regions, key=rank):
        ports = outgoing(region)
        if not 2 <= len(ports) <= 5:
            continue
        cut_mask = sum(bits[v] for v in region)
        fixed = {v for v, mask in ancestors.items() if not mask & cut_mask}
        required = set()
        pending = list(targets & graph.keys())
        while pending:
            v = pending.pop()
            if v in required:
                continue
            required.add(v)
            if v not in ports:
                pending.extend(x for x in graph[v][1:] if x in graph)
        ports &= required
        if len(ports) < 2:
            continue
        must = sum(bits[v] for v in required)
        if must.bit_count() >= len(best):
            continue
        if max_cuts and tested >= max_cuts:
            break
        tested += 1
        options = {}
        direct = {}
        for v in sorted(ports):
            via = defaultdict(list)
            free = []
            for h, a, rec in alternatives(v):
                if a not in fixed or h in required and h not in fixed:
                    continue
                mask = ancestors[a] & ~must
                via[h].append((mask, rec))
                if h in fixed:
                    free.append((mask | (ancestors[h] & ~must), rec))
            root = isqrt(v)
            if root * root == v and root != v:
                via[root].append((0, ('*', root, root)))
            if v % 2 == 0:
                via[v // 2].append((0, ('+', v // 2, v // 2)))
            options[v] = via
            direct[v] = free
        needed = [set(options[v]) for v in ports if not direct[v]]
        if needed:
            hubs = set.intersection(*needed)
        else:
            hubs = set.union(*(set(opts) for opts in options.values()))
        for h in sorted(hubs):
            if h in required and h not in fixed or h in ports:
                continue
            if sum(h in opts for opts in options.values()) < 2:
                continue
            if h in fixed:
                makers = [(ancestors[h] & ~must, None)]
            else:
                makers = [( (ancestors[a] | ancestors[b]) & ~must, rec)
                          for b, a, rec in alternatives(h) if a in fixed and b in fixed]
            if not makers:
                continue
            joined += 1
            choices = [options[v].get(h, []) + direct[v] for v in sorted(ports)]
            if any(not choices_for_v for choices_for_v in choices):
                continue
            choices.append(makers)
            # Keep alternative dependency sets when they can share intermediate instructions.
            beam = [(0, ())]
            allowance = len(best) - must.bit_count() - int(h not in fixed) - 1
            for group in choices:
                next_states = {}
                for mask, recipes in beam:
                    for extra, recipe in group:
                        merged = mask | extra
                        if merged.bit_count() <= allowance and merged not in next_states:
                            next_states[merged] = recipes + (recipe,)
                if not next_states:
                    beam = []
                    break
                beam = sorted(next_states.items(), key=lambda pair: pair[0].bit_count())[:8]
            if not beam:
                continue
            _, recipes = beam[0]
            changed = dict(graph)
            for v, rec in zip(sorted(ports), recipes):
                changed[v] = rec
            if recipes[-1] is not None:
                changed[h] = recipes[-1]
            graphs += 1
            candidate = compile_graph(puzzle, changed, attempts=6)
            if candidate is None:
                candidate = schedule_like(puzzle, program, changed)
            if candidate is not None and len(candidate) < len(best):
                check(puzzle, candidate)
                best = candidate
    return puzzle.id, best, dict(cuts=tested, shared_values=joined, attempted_graphs=graphs,
                                 before=len(program), after=len(best))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--puzzles', required=True, type=Path)
    parser.add_argument('--parent', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--count', type=int, default=24)
    parser.add_argument('--max-cuts', type=int, default=32, help='0 searches every eligible cut')
    parser.add_argument('--jobs', type=int, default=6)
    parser.add_argument('--ids', type=Path, help='one puzzle ID per line; overrides count')
    args = parser.parse_args()
    puzzles = read_puzzles(args.puzzles)
    parent = read_submission(args.parent)
    if args.ids:
        selected = set(args.ids.read_text().split())
        group = [p for p in puzzles if p.id in selected]
        if len(group) != len(selected):
            raise ValueError('Unknown puzzle ID')
    else:
        eligible = [p for p in puzzles if 45 <= len(parent[p.id]) <= 230]
        group = sorted(eligible, key=lambda p: hashlib.sha256(p.id.encode()).digest())[:args.count]
    args.out.mkdir(exist_ok=True, parents=True)
    rows = {}
    winners = {}
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        for i, tape, record in pool.map(search, [(p, parent[p.id], args.max_cuts) for p in group]):
            rows[i] = record
            if record['after'] < record['before']:
                winners[i] = tape
    write_submission(args.out/'wins.csv', [p for p in puzzles if p.id in winners], winners)
    report = dict(parent_sha256=hashlib.sha256(args.parent.read_bytes()).hexdigest(),
                  max_cuts=args.max_cuts, tested=len(rows), saved=sum(r['before']-r['after'] for r in rows.values()),
                  rows=rows)
    (args.out/'results.json.gz').write_bytes(gzip.compress(json.dumps(report, separators=(',', ':')).encode(), mtime=0))
    print(len(rows), len(winners), report['saved'], flush=True)


if __name__ == '__main__':
    main()
