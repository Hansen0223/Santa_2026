"""Assemble a ready-to-submit table using Pardheev's version 1 release and credited local programs."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from elf import read_puzzles, read_submission, write_submission

BASE = '8038039'
URL = 'https://www.kaggle.com/datasets/pardheev/santa-2026-elf-calculator-132997/versions/1'
ARCHIVE_HASH = '668f99e60746e4ea2b46c64584af96bb34884612f4445b9e756be950d77685c4'


def decode(data):
    rows = {}
    for row in csv.DictReader(io.StringIO(data.decode('utf-8-sig'))):
        if row['id'] in rows:
            raise ValueError(f"duplicate puzzle {row['id']}")
        rows[row['id']] = tuple(map(tuple, json.loads(row['program'])))
    return rows


def baseline(name, revision=BASE):
    return decode(subprocess.check_output(['git', 'show', f'{revision}:{name}'], cwd=ROOT))


def donor(archive):
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_HASH:
        raise ValueError('Expected the original, pinned version 1 archive.')
    with zipfile.ZipFile(archive) as source:
        rows = decode(source.read('submission.csv'))
    if len(rows) != 1000 or sum(map(len, rows.values())) != 132997:
        raise ValueError('unexpected release contents')
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--puzzles', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--base', default=BASE)
    parser.add_argument('--improvements', type=Path, nargs='*', default=[])
    args = parser.parse_args()
    args.out.mkdir(exist_ok=True, parents=True)
    puzzles = read_puzzles(args.puzzles)
    local = baseline('public-assisted/submission.csv', args.base)
    release = donor(args.archive)
    if set(release) != {p.id for p in puzzles} or set(local) != set(release):
        raise ValueError('unexpected puzzle ids')
    shortest = local.copy()
    selected = {i: 'base' for i in local}
    inputs = [('pardheev-v1', release)]
    inputs.extend((f.name, read_submission(f)) for f in args.improvements)
    for name, programs in inputs:
        for i, program in programs.items():
            if len(program) < len(shortest[i]):
                shortest[i], selected[i] = program, name
    path = args.out / 'submission.csv'
    score = write_submission(path, puzzles, shortest)
    result = dict(base=args.base, release=URL, archive_sha256=ARCHIVE_HASH, instructions=score,
                  sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  sources={k:sum(s == k for s in selected.values()) for k in sorted(set(selected.values()))},
                  from_base=sum(map(len, local.values())) - score,
                  changed={i:[len(local[i]),len(shortest[i]),s] for i,s in selected.items() if s != 'base'})
    (args.out/'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
    print(score, result['sources'], result['sha256'])


if __name__ == '__main__':
    main()