"""Check coverage and assemble proof records for the ten unresolved 882 cells."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]))
from elf import check, read_puzzles, sha256


def build(puzzles, directory):
    grid = HERE / "h10-first-grid.json.gz"
    base = json.loads(gzip.decompress(grid.read_bytes()))
    closed = json.loads((HERE / "h10-cell-11-4.json").read_bytes())
    official = sha256(puzzles)
    if official != base["puzzles_sha256"] or official != closed["official_sha256"]:
        raise ValueError("The puzzle file differs from the fixed inputs")
    p = next(p for p in read_puzzles(puzzles) if p.id == "scored_0882")
    original = base["instances"][p.id]["branches"]
    cells = {(x["first"],x["second"]):x["status"] for x in original}
    if len(original) != len(cells) or cells.keys() != {(i,j) for i in range(24) for j in range(32)}:
        raise ValueError("The base partitions are incomplete")
    closed_cell = closed["first"],closed["second"]
    pending = {cell for cell,status in cells.items() if status=="UNKNOWN"}-{closed_cell}
    if len(pending)!=10 or closed["decision"]!="UNSAT" or closed["complete_thirds"]!=24:
        raise ValueError("Unexpected base proof state")
    expected = {(i,j,k) for i,j in pending for k in range(24)}
    expected_context = dict(grid_sha256=sha256(grid),official_sha256=official,
                            binary_sha256=closed["engine_sha256"],thirds=24,width=16)
    rows = {}
    closed_by_cell = Counter()
    for f in sorted(directory.glob("*.json")):
        row = json.loads(f.read_bytes())
        key = tuple(row["coordinates"])
        status = row["status"]
        if key not in expected or key in rows or row["context"]!=expected_context:
            raise ValueError(f"Invalid coordinates or inputs at {f}")
        if status not in ("FOUND","UNSAT","UNKNOWN"):
            raise ValueError(f"Invalid decision at {f}")
        if len(row["metrics"])!=7 or not 0<=row["metrics"][0]<=row["budget"]:
            raise ValueError(f"Invalid counters at {f}")
        if status=="UNSAT":
            closed_by_cell[key[:2]]+=1
        if status=="FOUND" and check(p,row["program"])!=22:
            raise ValueError(f"Invalid exact witness at {f}")
        rows[key] = row
    counts = Counter(row["status"] for row in rows.values())
    new = sum(n==24 for n in closed_by_cell.values())
    result = "FOUND" if counts["FOUND"] else "UNSAT" if new==len(pending) else "INCOMPLETE"
    return dict(checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                expected=len(expected),counts=dict(counts),finished=len(rows),
                newly_closed_cells=new,remaining_cells=len(pending)-new,decision=result,
                records=[rows[k] for k in sorted(rows)])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--puzzles",type=Path,required=True)
    parser.add_argument("--in",dest="directory",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    if not args.directory.is_dir():
        parser.error("Input directory does not exist")
    data=build(args.puzzles,args.directory)
    raw=json.dumps(data,separators=(",",":")).encode()
    args.out.write_bytes(gzip.compress(raw,mtime=0))
    print(data["decision"],data["finished"],data["counts"],data["newly_closed_cells"])


if __name__=="__main__":
    main()
