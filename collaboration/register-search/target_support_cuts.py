"""Search arithmetic subprograms selected by targets or shared intermediate values."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
from itertools import combinations
from pathlib import Path

from interior_bands import available, run_cuts
from elf import check, read_puzzles, read_submission, sha256, write_submission
from graph import active_graph, first_recipes


def cuts(puzzle, graph, count):
    targets = sorted(set(puzzle.targets) & graph.keys())
    indexed = {v: 1 << j for j, v in enumerate(targets)}
    demand = dict.fromkeys(graph, 0)
    for v in reversed(graph):
        mask = demand[v] | indexed.get(v, 0)
        demand[v] = mask
        for operand in set(graph[v][1:]) & graph.keys():
            demand[operand] |= mask
    weights = Counter(demand.values())
    weights.pop(0, None)
    solo = {bit: weights[bit] for bit in indexed.values()}
    selected = {}

    def offer(group):
        block = frozenset(v for v, mask in demand.items() if mask and not mask & ~group)
        if not 10 <= len(block) <= 105 or block in selected:
            return
        inputs = {operand for v in block for operand in graph[v][1:]} - block
        outputs = block & indexed.keys()
        if not 1 <= len(inputs) <= puzzle.registers - 4 or not 2 <= len(outputs) <= 24:
            return
        best = (len(block) - len(outputs)) / (1 + len(inputs)**.5 + len(outputs)**.5)
        selected[block] = (-best, "target-support", 0, len(block), block, inputs, outputs)

    for seed in indexed.values():
        group = seed
        for _ in range(min(13, len(targets) - 1)):
            # Prefer candidates that unlock work shared with the existing group.
            gains = Counter()
            for mask, size in weights.items():
                outside = mask & ~group
                if outside and outside.bit_count() == 1:
                    gains[outside] += size
            uncovered = [bit for bit in indexed.values() if not group & bit]
            next_bit = max(uncovered, key=lambda bit: (gains[bit] - solo[bit], gains[bit], -bit))
            group |= next_bit
            offer(group)
    chosen = []
    for option in sorted(selected.values(),key=lambda item:(item[0], tuple(sorted(item[5])), tuple(sorted(item[6])))):
        if any(2*len(option[4] & other[4]) > len(option[4] | other[4]) for other in chosen):
            continue
        chosen.append(option)
        if len(chosen) == count:
            break
    return chosen, len(selected)


def pivot_cuts(puzzle, graph, count, merge=False):
    """Grow regions around a computation and close dependencies between their nodes."""
    values = list(graph)
    indices = {v:i for i,v in enumerate(values)}
    parents = [{indices[x] for x in set(graph[v][1:]) if x in indices} for v in values]
    children = [set() for _ in values]
    ancestors = [1 << i for i in range(len(values))]
    descendants = ancestors.copy()
    for i, sources in enumerate(parents):
        for source in sources:
            children[source].add(i)
            ancestors[i] |= ancestors[source]
    for i in reversed(range(len(values))):
        for child in children[i]:
            descendants[i] |= descendants[child]

    def near(pivot, links):
        current = {pivot}
        layers = [current]
        for _ in range(3):
            current = current | {j for i in current for j in links[i]}
            layers.append(current)
        return layers

    targets = set(puzzle.targets)
    choices = {}
    seen = set()
    for pivot,v in enumerate(values):
        if not parents[pivot] or len(children[pivot]) < 2:
            continue
        before = near(pivot, parents)
        after = near(pivot, children)
        for left,right in ((1,3),(2,2),(3,1),(3,3)):
            around=before[left] | after[right]
            x=y=0
            for i in around:
                x |= ancestors[i]
                y |= descendants[i]
            mask = x & y
            if mask in seen or not 9 <= mask.bit_count() <= 75:
                continue
            seen.add(mask)
            locations = [i for i in range(len(values)) if (mask >> i) & 1]
            block = frozenset(values[i] for i in locations)
            ins = {u for node in block for u in graph[node][1:]} - block
            outs = {values[i] for i in locations
                    if values[i] in targets or any(not (mask >> j) & 1 for j in children[i])}
            if not 1 <= len(ins) <= puzzle.registers-4 or not 2 <= len(outs) <= 27:
                continue
            if not outs - targets:
                continue
            size = len(block)
            ratio = (size-len(outs)) / (1 + len(ins)**.5 + len(outs)**.5)
            choices[mask] = (-ratio, "pivot-neighborhood", pivot, size, block, ins, outs)
    if merge:
        ranked = sorted(choices.items(), key=lambda entry: entry[1][:4])[:64]
        choices = {}
        for (left_mask,left_cut),(right_mask,right_cut) in combinations(ranked,2):
            if (left_mask & right_mask) in (left_mask, right_mask):
                continue
            if not (left_cut[6] & right_cut[5] or right_cut[6] & left_cut[5]):
                continue
            ancestors_of_union = descendants_of_union = 0
            pending = left_mask | right_mask
            while pending:
                bit = pending & -pending
                pending ^= bit
                i = bit.bit_length() - 1
                ancestors_of_union |= ancestors[i]
                descendants_of_union |= descendants[i]
            mask = ancestors_of_union & descendants_of_union
            if mask in choices or not 18 <= mask.bit_count() <= 105:
                continue
            loc = [i for i in range(len(values)) if (mask >> i) & 1]
            block = frozenset(values[i] for i in loc)
            ins = {u for node in block for u in graph[node][1:]} - block
            outs = {values[i] for i in loc
                    if values[i] in targets or any(not (mask >> j) & 1 for j in children[i])}
            if not 1 <= len(ins) <= puzzle.registers-3 or not 2 <= len(outs) <= 34:
                continue
            removed_interfaces = len((left_cut[6] | right_cut[6]) - outs)
            if removed_interfaces < 2:
                continue
            score = (len(block) - len(outs) + 2*removed_interfaces) / (1 + len(ins)**.5 + len(outs)**.5)
            choices[mask] = (-score,"merged-pivots",min(left_cut[2],right_cut[2]),len(block),block,ins,outs)

    chosen = []
    for c in sorted(choices.values(),key=lambda item:item[:4]):
        if any(2*len(c[4] & old[4]) > len(c[4] | old[4]) for old in chosen):
            continue
        chosen.append(c)
        if len(chosen)==count:
            break
    return chosen,len(choices)


def joint_inputs(puzzle, graph, block, inputs, outputs, ways):
    """Prioritize extra inputs that together unlock distinct local computations."""
    fallback = available(puzzle, graph, block, inputs, outputs, ways)
    reachable = set(puzzle.seeds)
    for v, (_, a, b) in graph.items():
        if v not in block and a in reachable and b in reachable:
            reachable.add(v)
    menu = {}
    for v in block:
        pairs = {frozenset((a,b)) for a,b in ways[v] if a in reachable and b in reachable}
        if pairs and not any(pair <= inputs for pair in pairs):
            menu[v] = pairs
    extra = set()
    capacity = puzzle.registers - len(inputs)
    while len(extra) < capacity and menu:
        options = defaultdict(set)
        for v, pairs in menu.items():
            for pair in pairs:
                missing = pair - inputs - extra
                if 0 < len(missing) <= capacity - len(extra):
                    options[missing].add(v)
        if not options:
            break

        def rank(pair):
            values = options[pair]
            reward = len(values) + 3 * len(values & outputs)
            return -reward / len(pair), len(pair), tuple(sorted(pair))

        extra.update(min(options, key=rank))
        menu = {v:pairs for v,pairs in menu.items()
                if not any(pair <= inputs | extra for pair in pairs)}
    ordered = (*sorted(inputs), *sorted(extra))
    return (*ordered, *(v for v in fallback if v not in inputs | extra))[:puzzle.registers]


def work(task):
    puzzle, parent, engine, count, rounds, joint, pivot, merge = task
    graph = active_graph(puzzle, first_recipes(puzzle, parent))
    blocks, eligible = (pivot_cuts(puzzle, graph, count, merge)
                        if pivot or merge else cuts(puzzle, graph, count))
    seed = 408683 + int(puzzle.id[-4:])
    pid, tape, result = run_cuts(puzzle, parent, engine, rounds, graph, blocks, seed,
                                 joint_inputs if joint else available)
    result.update(after=len(tape), eligible=eligible,
                  blocks=[dict(targets=sorted(c[6]), inputs=sorted(c[5]), values=sorted(c[4])) for c in blocks])
    return pid, tape, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("puzzles","parent","out","engine"):
        parser.add_argument("--"+key,type=Path,required=True)
    for key,default in (("count",135),("cuts",4),("jobs",7),("rounds",720),("offset",0)):
        parser.add_argument("--"+key,type=int,default=default)
    parser.add_argument("--joint-inputs",action="store_true")
    parser.add_argument("--pivot-cuts",action="store_true",help="Center cuts on shared intermediate values")
    parser.add_argument("--merge-pivots",action="store_true",help="Search linked pivot regions together")
    parser.add_argument("--ids",nargs="+",help="Select specific puzzle IDs in the listed order")
    args = parser.parse_args()
    puzzles = read_puzzles(args.puzzles)
    parents = read_submission(args.parent)
    if args.ids and len(set(args.ids)) != len(args.ids):
        parser.error("Puzzle IDs must be unique")
    indexed = {p.id:p for p in puzzles}
    ranked = sorted((p for p in puzzles if len(p.targets) >= 8),
                    key=lambda p:(-len(parents[p.id]),p.id))
    selected = [indexed[pid] for pid in args.ids] if args.ids else ranked[args.offset:args.offset+args.count]
    configuration = dict(parent_sha256=sha256(args.parent), engine_sha256=sha256(args.engine),
                         puzzles_sha256=sha256(args.puzzles), rounds=args.rounds, cuts=args.cuts)
    if args.joint_inputs:
        configuration["joint_inputs"] = True
    if args.merge_pivots:
        configuration["cut_method"] = "merged-pivots"
    elif args.pivot_cuts:
        configuration["cut_method"] = "pivot-neighborhood"
    args.out.mkdir(parents=True,exist_ok=True)
    checkpoint_dir = args.out / "rows"
    checkpoint_dir.mkdir(exist_ok=True)
    rows, wins = {}, {}

    def collect(pid, tape, record):
        if record["before"] != len(parents[pid]) or record["after"] != check(indexed[pid], tape):
            raise ValueError(f"Invalid checkpoint for {pid}")
        rows[pid] = record
        if record["after"] < record["before"]:
            wins[pid] = tape

    tasks = []
    for puzzle in selected:
        path = checkpoint_dir / f"{puzzle.id}.json"
        if path.exists():
            saved = json.loads(path.read_bytes())
            if saved["configuration"] != configuration:
                raise ValueError(f"Stale checkpoint for {puzzle.id}")
            collect(puzzle.id,tuple(map(tuple,saved["tape"])),saved["record"])
        else:
            tasks.append((puzzle,parents[puzzle.id],args.engine,args.cuts,args.rounds,args.joint_inputs,args.pivot_cuts,args.merge_pivots))
    with ProcessPoolExecutor(args.jobs) as pool:
        for future in as_completed(pool.submit(work, task) for task in tasks):
            pid,tape,record = future.result()
            collect(pid,tape,record)
            path = checkpoint_dir / f"{pid}.json"
            temporary = path.with_suffix(".tmp")
            temporary.write_bytes(json.dumps(dict(configuration=configuration,tape=tape,record=record),
                                             separators=(",",":")).encode())
            temporary.replace(path)
            if pid in wins:
                print(pid,record["before"],record["after"],flush=True)
    write_submission(args.out/"wins.csv",[p for p in puzzles if p.id in wins],wins)
    result = dict(**configuration,rows={p.id:rows[p.id] for p in selected})
    (args.out/"results.json.gz").write_bytes(gzip.compress(json.dumps(result,separators=(",",":")).encode(),mtime=0))
    print(len(rows),len(wins),sum(rows[i]["before"]-rows[i]["after"] for i in wins))


if __name__ == "__main__":
    main()
