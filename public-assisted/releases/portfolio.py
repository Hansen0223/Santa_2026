"""Reassemble a portfolio by taking the shortest legal program from pinned sources."""
import argparse
from collections import Counter
import json
from pathlib import Path
import tempfile

from apply_updates import read_rows
from elf import read_puzzles, sha256, write_submission

HERE = Path(__file__).resolve().parent


def combine(sources, archives, puzzle_ids):
    winners, origins = {}, {}
    for source in sources:
        programs = read_rows(source, archives)
        if programs.keys() - puzzle_ids or source['full'] and programs.keys() != puzzle_ids:
            raise ValueError('Unexpected puzzle coverage: ' + source['name'])
        for i, program in programs.items():
            if i not in winners or len(program) < len(winners[i]):
                winners[i], origins[i] = program, source['name']
    if winners.keys() != puzzle_ids:
        raise ValueError('Portfolio contains missing puzzles')
    return winners, origins


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--puzzles', required=True, type=Path)
    parser.add_argument('--archives', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--manifest', type=Path, default=HERE/'portfolio.json')
    args = parser.parse_args()
    recipe = json.loads(args.manifest.read_bytes())
    if sha256(args.puzzles) != recipe['puzzles_sha256']:
        raise ValueError('Unexpected puzzle file')
    puzzles = read_puzzles(args.puzzles)
    programs, origins = combine(recipe['sources'], args.archives, {p.id for p in puzzles})
    args.out.mkdir(exist_ok=True, parents=True)
    with tempfile.TemporaryDirectory(dir=args.out) as temporary:
        temp = Path(temporary)
        path = temp/'submission.csv'
        steps = write_submission(path, puzzles, programs)
        if steps != recipe['instructions'] or sha256(path) != recipe['sha256']:
            raise ValueError('Release does not match its expected submission')
        report = dict(recipe, selected=dict(Counter(origins.values())))
        receipt = temp/'result.json'
        receipt.write_bytes((json.dumps(report,indent=2,ensure_ascii=False)+'\n').encode())
        path.replace(args.out/'submission.csv')
        receipt.replace(args.out/'result.json')
    print(steps, recipe['sha256'])


if __name__ == '__main__':
    main()
