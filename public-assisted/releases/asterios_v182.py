"""Combine Asterios v182 and the two pinned repository submissions, replaying all 1,000 programs."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'public-assisted/pardheev'))
from combine import baseline, decode
from elf import read_puzzles, read_submission, write_submission

REVISION = 'ae39b6649552d80b12aa2f04f2703f4c81ddc383'
ARCHIVE_SHA256 = '7f84082b9272fb51ee4564713d10c541b5f0d92655562728f42a1ebba9bb391a'
SOURCE = 'https://www.kaggle.com/datasets/asteriospanoras/santa-2026-elf-programs-and-experiments/versions/182'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--puzzles', required=True, type=Path)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if hashlib.sha256(args.archive.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        parser.error('Download the pinned original v182 ZIP.')
    with zipfile.ZipFile(args.archive) as archive:
        release = decode(archive.read('best_programs.csv'))
    banks = {'independent': baseline('submission.csv', REVISION),
             'public-assisted': baseline('public-assisted/submission.csv', REVISION),
             'asterios-v182': release}
    puzzles = read_puzzles(args.puzzles)
    ids = {p.id for p in puzzles}
    if any(set(rows) != ids for rows in banks.values()) or len(ids) != 1000:
        raise ValueError('Puzzle coverage differs from the official set.')
    origin = {p.id: min(banks, key=lambda k: len(banks[k][p.id])) for p in puzzles}
    winners = {i: banks[source][i] for i, source in origin.items()}
    for key, program in read_submission(HERE / 'v182-search-wins.csv').items():
        if len(program) < len(winners[key]):
            winners[key] = program
            origin[key] = 'local-search'
    path = args.out / 'submission.csv'
    steps = write_submission(path, puzzles, winners)
    receipt = dict(instructions=steps, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                   puzzles_sha256=hashlib.sha256(args.puzzles.read_bytes()).hexdigest(),
                   archive=SOURCE, archive_sha256=ARCHIVE_SHA256, revision=REVISION,
                   input_steps={k: sum(map(len, rows.values())) for k, rows in banks.items()},
                   selected=dict(Counter(origin.values())),
                   repository_improvements={i: [source, len(release[i]), len(winners[i])]
                                            for i, source in origin.items() if len(winners[i]) < len(release[i])})
    (args.out / 'result.json').write_bytes((json.dumps(receipt, indent=2) + '\n').encode())
    print(steps, receipt['sha256'], receipt['input_steps'], receipt['selected'])


if __name__ == '__main__':
    main()
