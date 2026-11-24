"""Recheck the saved 882 partition coverage and add its 23-step bound to the ledger."""
import argparse
import csv
import gzip
from io import StringIO
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from summarize_refinement import build

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0,str(ROOT))
from checkpoint import atomic_text
from elf import check, read_puzzles, read_submission, sha256
sys.path.insert(0,str(HERE.parent))
from merge_arithmetic_bounds import projection

PUZZLE = "scored_0882"
CERTIFICATE = HERE / "h10-open-progress.json.gz"
SOURCE = "puzzle-0882-diversity/h10-open-progress.json.gz"
FOURTH_ENGINE = "ce845c41ca35e804bda33825bdfc9978f24a97493b6395e0c1a2fc4f472c3e83"


def verify_coverage(puzzles, certificate):
    record = json.loads(gzip.decompress(certificate.read_bytes()))
    with TemporaryDirectory(dir=certificate.parent) as temporary:
        destinations = {}
        for key in ("records","fine","fourth"):
            directory = Path(temporary) / key
            directory.mkdir()
            destinations[key] = directory
            for i,row in enumerate(record[key]):
                (directory/f"{i:03}.json").write_text(json.dumps(row),encoding="utf8")
        confirmed=build(puzzles,destinations["records"],destinations["fine"],destinations["fourth"],FOURTH_ENGINE)
    if (confirmed["decision"]!="UNSAT" or confirmed["counts"]!={"UNSAT":240}
            or confirmed["newly_closed_cells"]!=10):
        raise ValueError("The 22-step search is incomplete")
    for field in ("decision","official_sha256","grid_sha256","expected","counts","finished","remaining_cells"):
        if confirmed[field]!=record[field]:
            raise ValueError(f"Saved summary mismatch: {field}")
    return confirmed


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--puzzles",type=Path,required=True)
    parser.add_argument("--certificate",type=Path,default=CERTIFICATE)
    parser.add_argument("--verify-only",action="store_true")
    args=parser.parse_args()
    activity=verify_coverage(args.puzzles,args.certificate)
    puzzle=next(p for p in read_puzzles(args.puzzles) if p.id==PUZZLE)
    witness=read_submission(ROOT/"submission.csv")[PUZZLE]
    if len(set(puzzle.targets)-set(puzzle.seeds))!=12 or check(puzzle,witness)!=23:
        raise ValueError("Unexpected arithmetic instance or witness")
    print(PUZZLE,"23 steps",activity["counts"])
    if args.verify_only:
        return

    combined=HERE.parent/"evidence"
    previous=combined/"combined-1875a66.json"
    parent=json.loads(previous.read_bytes())
    table=HERE.parent/"puzzle-bounds.csv"
    with table.open(newline="",encoding="utf8") as stream:
        rows=list(csv.DictReader(stream))
    receipt_path=combined/"combined-882.json"
    before=projection(rows)
    if receipt_path.exists() and before==json.loads(receipt_path.read_bytes())["lower_projection_sha256"]:
        return
    if before!=parent["lower_projection_sha256"] or parent["official_sha256"]!=sha256(args.puzzles):
        raise ValueError("Expected the prior merged bounds table")
    row=next(x for x in rows if x["id"]==PUZZLE)
    if int(row["certified_lower"])!=22 or int(row["best_verified_upper"])!=23:
        raise ValueError("Bound or upper witness changed since the checkpoint")
    row.update(local_lower="23",certified_lower="23",winning_lower_source=SOURCE,gap="0",tight="1")
    lower=sum(int(r["certified_lower"]) for r in rows)
    receipt=dict(parent,previous_certified_lower=parent["certified_lower"],certified_lower=lower,
                 parent_lower_projection_sha256=before,lower_projection_sha256=projection(rows),
                 gains={PUZZLE:1},proof_id=PUZZLE)
    receipt["dependencies"]={**parent["dependencies"],SOURCE:sha256(args.certificate),
                            "evidence/combined-1875a66.json":sha256(previous)}
    out=StringIO(newline="")
    writer=csv.DictWriter(out,fieldnames=list(rows[0]),lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    atomic_text(receipt_path,json.dumps(receipt,indent=2)+"\n")
    atomic_text(table,out.getvalue())
    print(lower,sum(int(r["tight"]) for r in rows))


if __name__=="__main__":
    main()
