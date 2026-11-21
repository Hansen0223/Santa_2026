"""Eliminate subsets of repeated computations while retaining the other physical copies."""
import argparse
from collections import defaultdict
from dataclasses import replace
from itertools import combinations
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from elf import check, read_puzzles, read_submission, replay, write_submission
from graph import _allocate


def occurrence_graph(puzzle, tape):
    count = len(tape)
    registers = [None] * puzzle.registers
    values = defaultdict(list)
    for index, value in enumerate(puzzle.seeds):
        registers[index] = count + index
        values[value].append(count + index)
    recipes = {}
    for node, (instruction, step) in enumerate(zip(tape, replay(puzzle, tape))):
        op, left, right, destination = instruction
        recipes[node] = (op, registers[left], registers[right])
        registers[destination] = node
        values[step[0]].append(node)
    targets = [values[v][0] for v in puzzle.targets]
    duplicates = [(node, copies[0]) for copies in values.values() for node in copies[1:] if node < count]
    return recipes, targets, duplicates


def collapse(recipes, targets, aliases):
    needed = set()
    stack = [aliases.get(v, v) for v in targets]
    while stack:
        node = stack.pop()
        if node in recipes and node not in needed:
            needed.add(node)
            stack.extend(aliases.get(v, v) for v in recipes[node][1:])
    return {node: (op, aliases.get(a,a), aliases.get(b,b))
            for node, (op,a,b) in recipes.items() if node in needed}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for key in ('puzzles','parents','output'):
        cli.add_argument('--'+key,required=True,type=Path)
    cli.add_argument('--id',required=True)
    args = cli.parse_args()
    puzzle = next(p for p in read_puzzles(args.puzzles) if p.id==args.id)
    tape = read_submission(args.parents)[puzzle.id]
    raw, targets, copies = occurrence_graph(puzzle,tape)
    if len(copies)>14:
        raise ValueError('select a program with at most fourteen redundant computations')
    seeds = tuple(range(len(tape),len(tape)+len(puzzle.seeds)))
    synthetic = replace(puzzle,seeds=seeds,targets=tuple(targets))
    best = tape
    for size in reversed(range(1,len(copies)+1)):
        for removed in combinations(copies,size):
            graph = collapse(raw,targets,dict(removed))
            if len(graph)>=len(best):
                continue
            candidate = _allocate(synthetic,graph,False,0,fixed_order=True)
            if candidate:
                check(puzzle,candidate)
                best = candidate
                print('chronological',len(best),flush=True)
    winners = {puzzle.id:best} if len(best)<len(tape) else {}
    write_submission(args.output,[puzzle] if winners else [],winners)
    print(puzzle.id,len(tape),len(best),len(copies),flush=True)


if __name__ == '__main__':
    main()
