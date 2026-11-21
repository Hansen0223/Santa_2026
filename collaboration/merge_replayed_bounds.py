"""Add fully replayed external decisions to a previously verified per-puzzle table."""
import argparse
import csv
import io
import json
from pathlib import Path

from merge_arithmetic_bounds import FIELDS, projection, sha
from merge_conditioned_bounds import committed, parse

HERE = Path(__file__).resolve().parent
BATCHES = {
    '8d4b4df': (
        '8b7e582859b0d73471ee8a8540706020ee7796c8',
        'evidence/combined-membership.json',
        'evidence/8d4b4df-replayed.json',
        'evidence/combined-membership-8d4b4df.json',
    ),
    '62e194b': (
        '8a031bccb43aebab5cd5889c0c61b02f4224d539',
        'evidence/combined-membership-8d4b4df.json',
        'evidence/62e194b-replayed.json',
        'evidence/combined-62e194b.json',
    ),
    '1875a66': (
        'c982b1668fafb6a127a19fa14f7d1c42418ab7a3',
        'evidence/combined-62e194b.json',
        'evidence/1875a66-replayed.json',
        'evidence/combined-1875a66.json',
    ),
}


def load_replay(path):
    replay = json.loads(path.read_bytes())
    if 'commit' not in replay:
        return replay
    # replay_increment.py checks every shard before recording a digest per decision.
    revision = replay['commit']
    assert sha(committed(revision, 'exact_helpers.cpp')) == replay['native_source_sha256']
    rows = replay['rows']
    assert len(rows) == replay['decisions'] == len({row['id'] for row in rows})
    for row in rows:
        name = f"proofs_ext/decisions.d/{row['id']}_h{row['helpers']}.json"
        raw = committed(revision, name)
        claim = json.loads(raw)
        assert sha(raw) == row['receipt_sha256']
        assert (claim['id'], claim['helpers'], claim['lower_bound']) == (row['id'], row['helpers'], row['lower'])
        assert len(claim['shard_nodes']) == row['shards'] and sum(claim['shard_nodes']) == row['nodes']
    assert sum(r['nodes'] for r in rows) == replay['nodes']
    assert sum(r['shards'] for r in rows) == replay['shards']
    return dict(upstream=revision, official_sha256=replay['puzzles_sha256'],
                external_bounds_sha256=sha(committed(revision, 'proofs_ext/bounds.csv')),
                rows={row['id']: row['lower'] for row in rows}, checked_digest_receipts=True)


def verified_bounds(replay, prior):
    revision = replay['upstream']
    old_csv = committed(prior['upstream'], 'proofs_ext/bounds.csv')
    new_csv = committed(revision, 'proofs_ext/bounds.csv')
    assert sha(old_csv) == prior['external_bounds_sha256']
    assert sha(new_csv) == replay['external_bounds_sha256']
    previous, current = [
        {r['id']: int(r['certified_lower']) for r in parse(raw)}
        for raw in (old_csv, new_csv)
    ]
    assert previous.keys() == current.keys() and len(current) == 1000
    changed = {i: n for i, n in current.items() if n != previous[i]}
    assert changed == replay['rows'] and all(n > previous[i] for i, n in changed.items())
    if replay.get('checked_digest_receipts'):
        return previous, changed
    decisions = replay['decisions']
    assert set(r['id'] for r in decisions) == changed.keys()
    assert len(decisions) == replay['shards'] and sum(r['nodes'] for r in decisions) == replay['nodes']
    for i, n in changed.items():
        shards = sorted((r for r in decisions if r['id'] == i), key=lambda r: r['shard'])
        budget = shards[0]['budget']
        claim = json.loads(committed(revision, f'proofs_ext/decisions.d/{i}_h{budget}.json'))
        assert claim['id'] == i and claim['helpers'] == budget and claim['lower_bound'] == n
        assert list(range(len(shards))) == [r['shard'] for r in shards]
        assert all(r['status'] == 'UNSAT' and r['budget'] == budget and r['shards'] == len(shards) for r in shards)
        assert [r['nodes'] for r in shards] == claim['shard_nodes']
        assert sum(r['terminal_candidates'] for r in shards) == claim['terminal_candidates']
    return previous, changed


def build(batch='1875a66'):
    base, parent, external, _ = BATCHES[batch]
    prior = json.loads((HERE/parent).read_bytes())
    replay = load_replay(HERE/external)
    assert replay['official_sha256'] == prior['official_sha256']
    raw = committed(base, 'collaboration/puzzle-bounds.csv')
    rows = parse(raw)
    assert projection(rows) == prior['lower_projection_sha256']
    previous, changed = verified_bounds(replay, prior)
    strict = {}
    for row in rows:
        i = row['id']
        assert int(row['external_lower']) == previous[i]
        if i not in changed:
            continue
        bound = changed[i]
        old = int(row['certified_lower'])
        assert bound <= int(row['best_verified_upper'])
        row['external_lower'] = str(bound)
        if bound > old:
            row.update(certified_lower=str(bound), winning_lower_source='proofs_ext')
            strict[i] = bound - old
    deps = dict(prior['dependencies'])
    for path in (parent, external):
        deps[path] = sha((HERE/path).read_bytes())
    total = sum(int(row['certified_lower']) for row in rows)
    assert total == prior['certified_lower'] + sum(strict.values())
    receipt = dict(upstream=replay['upstream'], official_sha256=prior['official_sha256'],
                   external_bounds_sha256=replay['external_bounds_sha256'], local_manifest_sha256=prior['local_manifest_sha256'],
                   base_commit=base, base_table_sha256=sha(raw), previous_certified_lower=prior['certified_lower'],
                   parent_lower_projection_sha256=prior['lower_projection_sha256'],
                   certified_lower=total, external_claims=len(changed), gains=strict,
                   lower_projection_sha256=projection(rows), dependencies=deps)
    return rows, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', choices=BATCHES, default='1875a66')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    proved, receipt = build(args.batch)
    result = HERE/BATCHES[args.batch][3]
    table = HERE/'puzzle-bounds.csv'
    live = parse(table.read_bytes())
    assert [r['id'] for r in live] == [r['id'] for r in proved]
    if args.write:
        assert projection(live) in (receipt['parent_lower_projection_sha256'], receipt['lower_projection_sha256'])
        for row, claim in zip(live, proved):
            row.update({k: claim[k] for k in FIELDS})
            gap = int(row['best_verified_upper']) - int(row['certified_lower'])
            assert gap >= 0
            row.update(gap=gap, tight=int(gap == 0))
        buf = io.StringIO(newline='')
        writer = csv.DictWriter(buf, fieldnames=list(live[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(live)
        table.write_bytes(buf.getvalue().encode())
        result.write_bytes((json.dumps(receipt, indent=2)+'\n').encode())
    else:
        batches = list(BATCHES)
        position = batches.index(args.batch)
        if position + 1 < len(batches) and projection(live) != receipt['lower_projection_sha256']:
            next_base = BATCHES[batches[position + 1]][0]
            live = parse(committed(next_base, 'collaboration/puzzle-bounds.csv'))
        assert projection(live) == receipt['lower_projection_sha256']
        assert json.loads(result.read_bytes()) == receipt
    print(receipt['certified_lower'], receipt['external_claims'], receipt['gains'])


if __name__ == '__main__':
    main()
