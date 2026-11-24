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


def build(puzzles, directory, deep=None, fourth=None, fourth_engine=None):
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
    fine_rows = {}
    refinements = {}
    for f in sorted(deep.glob("*.json")) if deep is not None else ():
        record = json.loads(f.read_bytes())
        parent = tuple(record["parent"])
        key = tuple(record["coordinates"])
        context = record["context"]
        modulus = context["thirds"]
        if (parent not in rows or modulus<=24 or modulus%24 or key[:2]!=parent[:2]
                or not 0<=key[2]<modulus or key[2]%24!=parent[2]
                or context!=dict(expected_context,thirds=modulus) or (modulus,key) in fine_rows):
            raise ValueError(f"Invalid refinement at {f}")
        if (record["status"] not in ("FOUND","UNSAT","UNKNOWN") or len(record["metrics"])!=7
                or not 0<=record["metrics"][0]<=record["budget"]):
            raise ValueError(f"Invalid decision at {f}")
        if record["status"]=="FOUND" and check(p,record["program"])!=22:
            raise ValueError(f"Invalid fine witness at {f}")
        fine_rows[modulus,key] = record
        state = refinements.setdefault((parent,modulus), Counter())
        state[record["status"]] += 1
    effective = {key:row["status"] for key,row in rows.items()}
    for (parent,modulus),states in refinements.items():
        if states["FOUND"]:
            if effective[parent]=="UNSAT":
                raise ValueError(f"Conflicting result for {parent}")
            effective[parent]="FOUND"
        elif states["UNSAT"]==modulus//24:
            if effective[parent]=="UNKNOWN":
                effective[parent]="UNSAT"
                closed_by_cell[parent[:2]]+=1
            elif effective[parent]=="FOUND":
                raise ValueError(f"Conflicting result for {parent}")
    fourth_rows = {}
    fourth_groups = {}
    for f in sorted(fourth.glob("*.json")) if fourth is not None else ():
        row = json.loads(f.read_bytes())
        key = tuple(row["coordinates"])
        parent = key[:3]
        moduli = row["moduli"]
        if (len(key)!=4 or parent not in rows or moduli[:3]!=[24,32,24] or len(moduli)!=4
                or not 0<=key[3]<moduli[3] or row["engine"]!=fourth_engine or (tuple(moduli),key) in fourth_rows):
            raise ValueError(f"Invalid fourth-level partition at {f}")
        lines = row["stdout"].splitlines()
        status,*metrics = lines[0].split()
        if (status not in ("FOUND","UNSAT","UNKNOWN") or len(metrics)!=7
                or not 0<=int(metrics[0])<=row["budget"] or len(lines)!=1+(status=="FOUND")):
            raise ValueError(f"Invalid fourth-level decision at {f}")
        if status=="FOUND":
            from tiny import encode
            values=tuple(map(int,lines[1].split()))
            if values[:len(p.seeds)]!=p.seeds or check(p,encode(p,values[len(p.seeds):]))!=22:
                raise ValueError(f"Invalid fourth-level witness at {f}")
        fourth_rows[tuple(moduli),key] = row
        fourth_groups.setdefault((parent,moduli[3]),Counter())[status] += 1
    for (parent,modulus),states in fourth_groups.items():
        if states["FOUND"]:
            if effective[parent]=="UNSAT":
                raise ValueError(f"Conflicting fourth-level result for {parent}")
            effective[parent]="FOUND"
        elif states["UNSAT"]==modulus:
            if effective[parent]=="UNKNOWN":
                effective[parent]="UNSAT"
                closed_by_cell[parent[:2]]+=1
            elif effective[parent]=="FOUND":
                raise ValueError(f"Conflicting fourth-level result for {parent}")
    counts = Counter(effective.values())
    new = sum(n==24 for n in closed_by_cell.values())
    result = "FOUND" if counts["FOUND"] else "UNSAT" if new==len(pending) else "INCOMPLETE"
    return dict(checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                official_sha256=official, grid_sha256=expected_context["grid_sha256"],
                expected=len(expected),counts=dict(counts),finished=len(rows),
                unresolved=[k for k in sorted(rows) if effective[k]=="UNKNOWN"], unseen=sorted(expected-rows.keys()),
                newly_closed_cells=new,remaining_cells=len(pending)-new,decision=result,
                records=[rows[k] for k in sorted(rows)], fine=[fine_rows[k] for k in sorted(fine_rows)], fourth=[fourth_rows[k] for k in sorted(fourth_rows)])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--puzzles",type=Path,required=True)
    parser.add_argument("--in",dest="directory",type=Path,required=True)
    parser.add_argument("--deep",type=Path)
    parser.add_argument("--fourth",type=Path)
    parser.add_argument("--fourth-binary",type=Path)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    if not args.directory.is_dir():
        parser.error("Input directory does not exist")
    if args.fourth is not None and args.fourth_binary is None:
        parser.error("--fourth requires --fourth-binary")
    binary = sha256(args.fourth_binary) if args.fourth_binary else None
    data=build(args.puzzles,args.directory,args.deep,args.fourth,binary)
    raw=json.dumps(data,separators=(",",":")).encode()
    args.out.write_bytes(gzip.compress(raw,mtime=0))
    print(data["decision"],data["finished"],data["counts"],data["newly_closed_cells"])


if __name__=="__main__":
    main()
