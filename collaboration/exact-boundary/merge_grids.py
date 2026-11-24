"""Validate coverage of archived dense-search grids and merge completed exclusions."""
import argparse
import csv
import gzip
from io import StringIO
from itertools import product
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT/"collaboration"
sys.path[:0] = [str(ROOT),str(HERE)]
from elf import read_puzzles,sha256
from merge_arithmetic_bounds import FIELDS,projection,sha
from merge_conditioned_bounds import parse

ENGINE = "71dca8b89c358900e7312c23768d1dfcd13f2e8e6473850f82a7a3c3c999ec28"


def verify_grid(puzzle, archive, official):
    rows = archive["rows"]
    if not rows:
        raise ValueError("Grid is empty.")
    first = rows[0]
    expected = {name:first[name] for name in ("puzzle","helpers","moduli","group_width","engine","official")}
    assert first["puzzle"]==puzzle.id and first["official"]==official
    assert first["group_width"]==16 and first["engine"]==ENGINE and puzzle.limit<=2_000_000
    assert first["helpers"]>=5 and len(first["moduli"])==3 and min(first["moduli"])>=1
    cells = set(product(*(range(n) for n in first["moduli"])))
    seen = set()
    statuses = set()
    for row in rows:
        assert all(row[name]==value for name,value in expected.items())
        coord = tuple(row["coords"])
        assert coord in cells and coord not in seen
        assert row["status"] in ("UNSAT","UNKNOWN") and len(row["metrics"])==7
        assert 0<=row["metrics"][0]<=row["budget"]
        seen.add(coord)
        statuses.add(row["status"])
    if seen==cells and statuses=={"UNSAT"}:
        return len(set(puzzle.targets)-set(puzzle.seeds))+first["helpers"]+1
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("puzzles","prior","grids","receipt"):
        parser.add_argument("--"+field,type=Path,required=True)
    parser.add_argument("--base",required=True)
    parser.add_argument("--write",action="store_true")
    a = parser.parse_args()
    official = sha256(a.puzzles)
    puzzles = {p.id:p for p in read_puzzles(a.puzzles)}
    prior = json.loads(a.prior.read_bytes())
    assert official==prior["official_sha256"]
    base = subprocess.check_output(["git","rev-parse",a.base],cwd=ROOT,text=True).strip()
    raw = subprocess.check_output(["git","show",base+":collaboration/puzzle-bounds.csv"],cwd=ROOT)
    rows = parse(raw)
    assert projection(rows)==prior["lower_projection_sha256"]
    by_id = {r["id"]:r for r in rows}
    archive = json.loads(gzip.decompress(a.grids.read_bytes()))
    completed = {}
    for grid in archive["grids"]:
        pid = grid["puzzle"]
        result = verify_grid(puzzles[pid],grid,official)
        if result is not None:
            completed[pid] = max(result,completed.get(pid,0))
    changed = {}
    source = a.grids.resolve().relative_to(HERE).as_posix()
    for pid,n in completed.items():
        row = by_id[pid]
        old = int(row["certified_lower"])
        assert n<=int(row["best_verified_upper"])
        if n>old:
            changed[pid] = n-old
            row.update(local_lower=str(n),certified_lower=str(n),winning_lower_source=source)
    new_total = prior["certified_lower"]+sum(changed.values())
    assert new_total==sum(int(r["certified_lower"]) for r in rows)
    deps = dict(prior["dependencies"])
    for path in (a.prior,a.grids):
        deps[path.resolve().relative_to(HERE).as_posix()] = sha256(path)
    receipt = dict(prior,base_commit=base,base_table_sha256=sha(raw),previous_certified_lower=prior["certified_lower"],
                   parent_lower_projection_sha256=prior["lower_projection_sha256"],certified_lower=new_total,
                   gains=changed,external_claims=0,lower_projection_sha256=projection(rows),dependencies=deps)
    receipt.pop("proof_id",None)
    receipt["proof_ids"] = sorted(changed)
    table = HERE/"puzzle-bounds.csv"
    live = parse(table.read_bytes())
    assert list(by_id)==[r["id"] for r in live]
    if a.write:
        assert projection(live) in (prior["lower_projection_sha256"],receipt["lower_projection_sha256"])
        for row in live:
            row.update({k:by_id[row["id"]][k] for k in FIELDS})
            gap = int(row["best_verified_upper"])-int(row["certified_lower"])
            assert gap>=0
            row.update(gap=gap,tight=int(gap==0))
        stream = StringIO(newline="")
        writer = csv.DictWriter(stream,fieldnames=list(live[0]),lineterminator="\n")
        writer.writeheader()
        writer.writerows(live)
        table.write_bytes(stream.getvalue().encode())
        a.receipt.write_bytes((json.dumps(receipt,indent=2)+"\n").encode())
    else:
        assert projection(live)==receipt["lower_projection_sha256"]
        assert json.loads(a.receipt.read_bytes())==receipt
    print(new_total,changed)


if __name__=="__main__":
    if not __debug__:
        raise SystemExit("Run without -O to enable proof checks")
    main()
