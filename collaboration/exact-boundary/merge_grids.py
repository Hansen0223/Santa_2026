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
from elf import check,read_puzzles,sha256
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


def child_check(row,puzzle,official,moduli,parents,helpers):
    coords = tuple(row["coords"])
    fields = dict(puzzle=puzzle.id,official=official,engine=ENGINE,group_width=16,helpers=helpers,moduli=moduli)
    if (any(row.get(k)!=v for k,v in fields.items()) or len(coords)!=3 or
            coords[:2] not in parents or not 0<=coords[2]<moduli[2]):
        raise ValueError(f"Unexpected child coordinates {coords}")
    if row["status"] not in ("UNSAT","UNKNOWN","FOUND") or len(row["metrics"])!=7:
        raise ValueError(f"Malformed child decision {coords}")
    nodes = row["metrics"][0]
    if not 0<=nodes<=row["budget"] or row["status"]=="UNKNOWN" and nodes!=row["budget"]:
        raise ValueError(f"Invalid node count for {coords}")
    if row["status"]=="FOUND" and check(puzzle,row["program"])>len(set(puzzle.targets)-set(puzzle.seeds))+helpers:
        raise ValueError(f"Invalid witness for {coords}")
    return coords


def summarize(puzzle,official,grid,children):
    verify_grid(puzzle,grid,official)
    head = grid["rows"][0]
    n,m,z = head["moduli"]
    cells = {(r["coords"][0],r["coords"][1]):r for r in grid["rows"]}
    if z!=1 or len(cells)!=n*m:
        raise ValueError("Expected a complete two-level parent grid")
    pending = {key for key,row in cells.items() if row["status"]=="UNKNOWN"}
    parts = children[0]["moduli"][2] if children else 1
    grouped = {}
    for row in children:
        k = child_check(row,puzzle,official,[n,m,parts],pending,head["helpers"])
        if k in grouped:
            raise ValueError(f"Duplicate child {k}")
        grouped[k] = row
    closed = {key for key in pending if all(grouped.get((*key,j),{}).get("status")=="UNSAT" for j in range(parts))}
    return sorted(closed), sorted(pending-closed)


def verify_refinement(puzzle, grid, refined, official, parent_digest):
    helpers = grid["rows"][0]["helpers"]
    children = refined["children"]
    if (refined["puzzle"] != puzzle.id or refined["helpers"] != helpers
            or refined["parent_sha256"] != parent_digest or refined["parts"] < 2
            or not children or children[0]["moduli"][2] != refined["parts"]):
        raise ValueError("Refinement does not match the parent grid")
    closed, remaining = summarize(puzzle, official, grid, children)
    if ([list(cell) for cell in closed] != refined["closed"]
            or [list(cell) for cell in remaining] != refined["remaining"]):
        raise ValueError("Refinement coverage does not match the recorded decision")
    if not remaining:
        return len(set(puzzle.targets) - set(puzzle.seeds)) + helpers + 1
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("puzzles","prior","grids","receipt"):
        parser.add_argument("--"+field,type=Path,required=True)
    parser.add_argument("--base",required=True)
    parser.add_argument("--refined",type=Path,help="Third-axis exclusion for a grid in --grids")
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
    sources = {}
    parent_source = a.grids.resolve().relative_to(HERE).as_posix()
    for grid in archive["grids"]:
        pid = grid["puzzle"]
        result = verify_grid(puzzles[pid],grid,official)
        if result is not None and result > completed.get(pid, 0):
            completed[pid] = result
            sources[pid] = parent_source
    if a.refined:
        refined = json.loads(gzip.decompress(a.refined.read_bytes()))
        pid = refined["puzzle"]
        parents = [g for g in archive["grids"] if g["puzzle"] == pid
                   and g["rows"][0]["helpers"] == refined["helpers"]]
        if len(parents) != 1:
            raise ValueError("Expected exactly one parent grid for the refinement")
        result = verify_refinement(puzzles[pid], parents[0], refined, official, sha256(a.grids))
        if result is not None and result > completed.get(pid, 0):
            completed[pid] = result
            sources[pid] = a.refined.resolve().relative_to(HERE).as_posix()
    changed = {}
    for pid,n in completed.items():
        row = by_id[pid]
        old = int(row["certified_lower"])
        assert n<=int(row["best_verified_upper"])
        if n>old:
            changed[pid] = n-old
            row.update(local_lower=str(n),certified_lower=str(n),winning_lower_source=sources[pid])
    new_total = prior["certified_lower"]+sum(changed.values())
    assert new_total==sum(int(r["certified_lower"]) for r in rows)
    deps = dict(prior["dependencies"])
    for path in filter(None, (a.prior, a.grids, a.refined)):
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
