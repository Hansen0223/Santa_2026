"""Cache successful pair audits for the exact puzzle input and executable that ran them."""
import json
import subprocess
import tempfile
import time
from hashlib import sha256
from pathlib import Path

AUDIT_DIR = Path(__file__).resolve().parents[1] / "work" / "proofs" / "audit-cache"


def native_input(puzzle, helpers=0, node_limit=0):
    return (
        f"{puzzle.limit} {len(puzzle.seeds)} {len(puzzle.targets)} {helpers} {node_limit}\n"
        + " ".join(map(str, puzzle.seeds + puzzle.targets))
        + "\n"
    )


def ensure_audit(binary, puzzle, refresh=False, quiet=False):
    binary = Path(binary).resolve()
    binary_digest = sha256(binary.read_bytes()).hexdigest()
    payload = native_input(puzzle)
    key = {"id": puzzle.id, "input_sha256": sha256(payload.encode()).hexdigest(),
           "binary_sha256": binary_digest, "status": "OK"}
    folder = AUDIT_DIR / binary_digest
    path = folder / f"{puzzle.id}.json"
    if not refresh:
        try:
            record = json.loads(path.read_bytes())
        except (FileNotFoundError, ValueError):
            record = None
        if isinstance(record, dict) and all(record.get(k) == v for k, v in key.items()):
            if not quiet:
                print(f"audit {puzzle.id}: cached", flush=True)
            return record

    start = time.monotonic()
    result = subprocess.run([str(binary), "--audit-pairs"], input=payload, text=True,
                            capture_output=True, check=True)
    if result.stdout.strip() != "OK":
        raise ValueError(f"{puzzle.id}: pair coverage audit failed: {result.stdout.strip()[:80]}")
    record = {**key, "seconds": round(time.monotonic() - start, 1)}
    folder.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=folder, delete=False, mode="w", encoding="utf8") as f:
        temporary = Path(f.name)
        try:
            json.dump(record, f, indent=2)
            f.write("\n")
        except BaseException:
            f.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    if not quiet:
        print(f"audit {puzzle.id}: ran {record['seconds']} s, cached", flush=True)
    return record
