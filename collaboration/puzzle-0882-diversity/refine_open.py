"""Resume the unresolved parts of the 22-instruction search for puzzle 882."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import NamedTemporaryFile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from elf import check, read_puzzles, sha256, write_submission
from tiny import encode


def store(path, record):
    with NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        tmp.write((json.dumps(record, separators=(',', ':')) + '\n').encode())
    Path(tmp.name).replace(path)


def search(puzzle, binary, first, second, third, budget, thirds=24):
    values = [puzzle.limit, len(puzzle.seeds), len(puzzle.targets), 10, budget,
              *puzzle.seeds, *puzzle.targets]
    result = subprocess.run(
        [str(binary), 'star', str(first), '24', str(second), '32', str(third), str(thirds)],
        input=' '.join(map(str, values)) + '\n', text=True, capture_output=True, check=True,
        env={**os.environ, 'SANTA_GROUP_WIDTH': '16'},
        creationflags=getattr(subprocess, 'BELOW_NORMAL_PRIORITY_CLASS', 0))
    lines = result.stdout.splitlines()
    status, *fields = lines[0].split()
    metrics = list(map(int, fields))
    if (status not in ('UNSAT', 'UNKNOWN', 'FOUND') or len(metrics) != 7
            or len(lines) != 1 + (status == 'FOUND') or not 0 <= metrics[0] <= budget
            or (status == 'UNKNOWN' and metrics[0] != budget)):
        raise ValueError(f'Invalid native decision for {(first, second, third)}')
    row = dict(status=status, metrics=metrics, budget=budget,
               stdout_sha256=hashlib.sha256(result.stdout.encode()).hexdigest())
    if status == 'FOUND':
        values = list(map(int, lines[1].split()))
        if tuple(values[:len(puzzle.seeds)]) != puzzle.seeds:
            raise ValueError('Changed seeds')
        tape = encode(puzzle, values[len(puzzle.seeds):])
        if check(puzzle, tape) > 22:
            raise ValueError('Invalid witness')
        row['program'] = tape
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('puzzles', 'binary', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--budget', type=int, default=20000000)
    parser.add_argument('--retry-only', action='store_true',
                        help='Only retry existing UNKNOWN cells below the new budget')
    args = parser.parse_args()
    if min(args.jobs, args.budget) < 1:
        parser.error('jobs and budget must be positive')
    args.out.mkdir(parents=True, exist_ok=True)
    binary = args.binary.resolve(strict=True)
    grid = HERE / 'h10-first-grid.json.gz'
    parent = json.loads(gzip.decompress(grid.read_bytes()))
    assert sha256(args.puzzles) == parent['puzzles_sha256']
    assert (parent['shards'], parent['subshards'], parent['group_width']) == (24, 32, 16)
    puzzle = next(p for p in read_puzzles(args.puzzles) if p.id == 'scored_0882')
    full = parent['instances'][puzzle.id]
    cells = {(r['first'], r['second']): r for r in full['branches']}
    assert set(cells) == {(i, j) for i in range(24) for j in range(32)}
    assert len(cells) == full['finished'] == len(full['branches'])
    assert set(r['status'] for r in cells.values()) == {'UNSAT', 'UNKNOWN'}
    closed = json.loads((HERE / 'h10-cell-11-4.json').read_bytes())
    assert closed['decision'] == 'UNSAT' and closed['complete_thirds'] == 24
    assert closed['official_sha256'] == parent['puzzles_sha256']
    closed_key = (closed['first'], closed['second'])
    assert cells[closed_key]['status'] == 'UNKNOWN'
    context = dict(grid_sha256=sha256(grid), official_sha256=sha256(args.puzzles),
                   binary_sha256=sha256(binary), thirds=24, width=16)
    pending = []
    for (i, j), record in sorted(cells.items()):
        if record['status'] != 'UNKNOWN' or (i, j) == closed_key:
            continue
        for k in range(24):
            key = [i, j, k]
            path = args.out / f'{i:02}-{j:02}-{k:02}.json'
            if args.retry_only and not path.exists():
                continue
            if path.exists():
                old = json.loads(path.read_bytes())
                if old['context'] != context or old['coordinates'] != key:
                    raise ValueError(f'Changed task at {path}')
                if old['status'] == 'FOUND':
                    assert check(puzzle, old['program']) <= 22
                    write_submission(args.out / 'witness.csv', [puzzle], {puzzle.id:old['program']})
                    print(f'Existing witness at {path}', flush=True)
                    return
                if old['status'] == 'UNSAT' or old['budget'] >= args.budget:
                    continue
            pending.append((key, path))
    with ThreadPoolExecutor(args.jobs) as pool:
        jobs = {pool.submit(search, puzzle, binary, *key, args.budget): (key, path)
                for key, path in pending}
        found = False
        for task in as_completed(jobs):
            if task.cancelled():
                continue
            key, path = jobs[task]
            row = task.result()
            store(path, dict(context=context, coordinates=key, **row))
            if row['status'] == 'FOUND' and not found:
                write_submission(args.out / 'witness.csv', [puzzle], {puzzle.id:row['program']})
                found = True
                for other in jobs:
                    other.cancel()
            print(*key, row['status'], row['metrics'][0], flush=True)


if __name__ == '__main__':
    main()
