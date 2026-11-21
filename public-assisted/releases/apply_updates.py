"""Apply credited, hash-pinned row improvements to an existing Santa 2026 submission."""
import argparse
import ast
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import sys
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from elf import read_puzzles, read_submission, sha256, write_submission


def read_rows(source, archives):
    if 'notebook' in source:
        raw = (archives / source['notebook']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != source['notebook_sha256']:
            raise ValueError('Unexpected notebook source')
        cell = json.loads(raw)['cells'][source['cell']]
        if cell['cell_type'] != 'code':
            raise ValueError('Expected a code cell containing program literals')
        statements = ast.parse(''.join(cell['source'])).body
        assignments = [stmt.value for stmt in statements if isinstance(stmt, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == source['variable'] for t in stmt.targets)]
        if len(assignments) != 1:
            raise ValueError('Expected one assignment of the program table')
        values = ast.literal_eval(assignments[0])
        if 'encoding' in source:
            if source['encoding'] != 'base64-zlib-json' or not isinstance(values, str):
                raise ValueError('Unrecognized notebook program encoding')
            data = base64.b64decode(''.join(values.split()), validate=True)
            values = json.loads(zlib.decompress(data))
        return {i: tuple(map(tuple, tape)) for i, tape in values.items()}
    if 'archive' in source:
        path = archives / source['archive']
        if sha256(path) != source['archive_sha256']:
            raise ValueError(f'{path.name}: unexpected archive hash')
        with zipfile.ZipFile(path) as archive:
            raw = archive.read(source['member'])
    elif 'output_csv' in source:
        raw = (archives / source['output_csv']).read_bytes()
    elif 'revision' in source:
        raw = subprocess.check_output(['git', 'show', source['revision'] + ':' + source['path']], cwd=ROOT)
    else:
        raw = (ROOT / source['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != source['csv_sha256']:
        raise ValueError('Unexpected program source')
    rows = {}
    for r in csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))):
        if r['id'] in rows:
            raise ValueError(f"Duplicate row {r['id']}")
        rows[r['id']] = tuple(map(tuple, json.loads(r['program'])))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('puzzles', 'parent', 'manifest', 'archives', 'out'):
        parser.add_argument('--' + key, required=True, type=Path)
    args = parser.parse_args()
    spec = json.loads(args.manifest.read_bytes())
    if sha256(args.parent) != spec['parent_sha256'] or sha256(args.puzzles) != spec['puzzles_sha256']:
        raise ValueError('Input puzzle set or parent submission differs from the manifest')
    programs = read_submission(args.parent)
    for source in spec['sources']:
        rows = read_rows(source, args.archives)
        for i, (old, new) in source['improvements'].items():
            replacement = rows[i]
            if len(programs[i]) != old or len(replacement) != new or new >= old:
                raise ValueError(f'Invalid improvement for {i}')
            programs[i] = replacement
    # Validate the expected bytes before replacing an existing deliverable.
    args.out.mkdir(exist_ok=True, parents=True)
    with tempfile.TemporaryDirectory(dir=args.out) as temporary:
        candidate = Path(temporary) / 'submission.csv'
        score = write_submission(candidate, read_puzzles(args.puzzles), programs)
        if score != spec['instructions'] or sha256(candidate) != spec['sha256']:
            raise ValueError('Assembled submission differs from the release receipt')
        candidate.replace(args.out / 'submission.csv')
        receipt = Path(temporary) / 'result.json'
        receipt.write_bytes((json.dumps(spec, indent=2, ensure_ascii=False) + '\n').encode())
        receipt.replace(args.out / 'result.json')
    print(score, spec['sha256'])


if __name__ == '__main__':
    main()
