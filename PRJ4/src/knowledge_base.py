"""Forward-chaining first-order-logic knowledge base for Minesweeper."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable


Cell = tuple[int, int]
AGENT_UNKNOWN = -1
AGENT_FLAGGED = -2


@dataclass(frozen=True, order=True)
class Constraint:
    """A set of cells containing exactly ``count`` mines."""

    cells: frozenset[Cell]
    count: int


class MinesweeperKnowledgeBase:
    """Stores predicate facts and derives new safe/mine facts to a fixpoint."""

    def __init__(self, rows: int, cols: int, total_mines: int) -> None:
        self.rows = rows
        self.cols = cols
        self.total_mines = total_mines
        self.max_model_cells = 18
        self.max_model_solutions = 50000
        self.cells: set[Cell] = {(r, c) for r in range(rows) for c in range(cols)}
        self.neighbor: set[tuple[Cell, Cell]] = set()
        self.neighbors: dict[Cell, set[Cell]] = {}
        self._init_neighbors()
        self.reset_dynamic_facts()

    def reset_dynamic_facts(self) -> None:
        self.revealed: set[Cell] = set()
        self.hidden: set[Cell] = set(self.cells)
        self.flagged: set[Cell] = set()
        self.safe: set[Cell] = set()
        self.mine: set[Cell] = set()
        self.clue: dict[Cell, int] = {}
        self.constraints: set[Constraint] = set()
        self.inconsistencies: list[str] = []

    def sync_from_agent_board(self, agent_board: dict[Cell, int]) -> None:
        self.reset_dynamic_facts()
        for cell in self.cells:
            value = agent_board.get(cell, AGENT_UNKNOWN)
            if value == AGENT_FLAGGED:
                self.flagged.add(cell)
                self.mine.add(cell)
                self.hidden.discard(cell)
            elif value == AGENT_UNKNOWN:
                self.hidden.add(cell)
            elif 0 <= value <= 8:
                self.revealed.add(cell)
                self.safe.add(cell)
                self.hidden.discard(cell)
                self.clue[cell] = value
            else:
                self.inconsistencies.append(f"invalid agent value {value} for {cell}")

    def infer(self) -> tuple[set[Cell], set[Cell]]:
        """Return actionable safe and mine cells inferred by repeated rules."""
        changed = True
        iterations = 0
        max_iterations = max(8, self.rows * self.cols * 2)

        while changed and iterations < max_iterations:
            iterations += 1
            changed = False

            if self._apply_global_rules():
                changed = True

            constraints = self._normalized_constraints(
                list(self._base_constraints()) + list(self.constraints)
            )
            for constraint in constraints:
                if self._apply_direct_constraint(constraint):
                    changed = True

            constraints = self._normalized_constraints(
                list(self._base_constraints()) + list(self.constraints)
            )
            if self._derive_subset_constraints(constraints):
                changed = True
            elif self._derive_model_based_facts(constraints):
                changed = True

        if iterations >= max_iterations:
            self.inconsistencies.append("inference stopped at iteration limit")

        actionable_safe = self.safe & self.hidden - self.flagged - self.mine
        actionable_mines = self.mine & self.hidden - self.flagged
        return actionable_safe, actionable_mines

    def fact_summary(self) -> dict[str, int]:
        return {
            "cells": len(self.cells),
            "neighbor": len(self.neighbor),
            "revealed": len(self.revealed),
            "hidden": len(self.hidden),
            "flagged": len(self.flagged),
            "safe": len(self.safe),
            "mine": len(self.mine),
            "clue": len(self.clue),
            "constraints": len(self.constraints),
        }

    def facts_as_strings(self) -> list[str]:
        facts: list[str] = []
        for r, c in sorted(self.revealed):
            facts.append(f"revealed({r},{c})")
        for r, c in sorted(self.hidden):
            facts.append(f"hidden({r},{c})")
        for r, c in sorted(self.flagged):
            facts.append(f"flagged({r},{c})")
        for r, c in sorted(self.safe):
            facts.append(f"safe({r},{c})")
        for r, c in sorted(self.mine):
            facts.append(f"mine({r},{c})")
        for (r, c), number in sorted(self.clue.items()):
            facts.append(f"clue({r},{c},{number})")
        return facts

    def estimate_mine_probabilities(self) -> dict[Cell, float]:
        """Estimate probabilities for guesses without changing facts."""
        unknown = self.hidden - self.mine - self.safe - self.flagged
        if not unknown:
            return {}

        remaining = max(0, self.total_mines - len(self.mine | self.flagged))
        global_probability = remaining / len(unknown) if unknown else 1.0
        buckets: dict[Cell, list[float]] = {cell: [global_probability] for cell in unknown}

        for constraint in self._normalized_constraints(
            list(self._base_constraints()) + list(self.constraints)
        ):
            if not constraint.cells:
                continue
            probability = constraint.count / len(constraint.cells)
            for cell in constraint.cells:
                if cell in buckets:
                    buckets[cell].append(probability)

        return {
            cell: min(1.0, max(0.0, sum(values) / len(values)))
            for cell, values in buckets.items()
        }

    def choose_safest_guess(self) -> Cell | None:
        probabilities = self.estimate_mine_probabilities()
        if not probabilities:
            return None

        def score(cell: Cell) -> tuple[float, int, int, int]:
            revealed_neighbors = len(self.neighbors[cell] & self.revealed)
            r, c = cell
            return (probabilities[cell], -revealed_neighbors, r, c)

        return min(probabilities, key=score)

    def _init_neighbors(self) -> None:
        for cell in self.cells:
            r, c = cell
            local: set[Cell] = set()
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    neighbor = (r + dr, c + dc)
                    if neighbor in self.cells:
                        local.add(neighbor)
                        self.neighbor.add((cell, neighbor))
            self.neighbors[cell] = local

    def _base_constraints(self) -> Iterable[Constraint]:
        for cell, number in self.clue.items():
            known_mines = self.neighbors[cell] & (self.mine | self.flagged)
            unknown_neighbors = (
                self.neighbors[cell] & self.hidden - self.safe - self.mine - self.flagged
            )
            remaining = number - len(known_mines)
            yield Constraint(frozenset(unknown_neighbors), remaining)

    def _normalized_constraints(
        self, constraints: Iterable[Constraint]
    ) -> list[Constraint]:
        normalized: set[Constraint] = set()
        known_mines = self.mine | self.flagged
        known_safe = self.safe | self.revealed
        for constraint in constraints:
            cells = set(constraint.cells)
            count = constraint.count
            count -= len(cells & known_mines)
            cells -= known_mines
            cells -= known_safe

            if count < 0:
                self.inconsistencies.append(
                    f"constraint has negative remaining mines: {constraint}"
                )
                continue
            if count > len(cells):
                self.inconsistencies.append(
                    f"constraint requires too many mines: {constraint}"
                )
                continue
            if cells:
                normalized.add(Constraint(frozenset(cells), count))
            elif count != 0:
                self.inconsistencies.append(f"empty inconsistent constraint: {constraint}")
        return sorted(normalized, key=lambda item: (len(item.cells), item.count, item.cells))

    def _apply_direct_constraint(self, constraint: Constraint) -> bool:
        changed = False
        if constraint.count == 0:
            for cell in constraint.cells:
                changed |= self._mark_safe(cell)
        elif constraint.count == len(constraint.cells):
            for cell in constraint.cells:
                changed |= self._mark_mine(cell)
        return changed

    def _derive_subset_constraints(self, constraints: list[Constraint]) -> bool:
        changed = False
        for smaller, larger in combinations(constraints, 2):
            if not smaller.cells or smaller.cells == larger.cells:
                continue

            first, second = smaller, larger
            if len(first.cells) > len(second.cells):
                first, second = second, first
            if not first.cells < second.cells:
                continue

            difference = second.cells - first.cells
            difference_count = second.count - first.count
            if difference_count < 0 or difference_count > len(difference):
                continue
            derived = Constraint(frozenset(difference), difference_count)
            if derived not in self.constraints:
                self.constraints.add(derived)
                changed = True
        return changed

    def _derive_model_based_facts(self, constraints: list[Constraint]) -> bool:
        changed = False
        for component_cells, component_constraints in self._constraint_components(
            constraints
        ):
            if len(component_cells) > self.max_model_cells:
                continue
            solutions = self._enumerate_component_solutions(
                component_cells, component_constraints
            )
            if not solutions:
                continue

            for cell in component_cells:
                mine_count = sum(1 for solution in solutions if cell in solution)
                if mine_count == 0:
                    changed |= self._mark_safe(cell)
                elif mine_count == len(solutions):
                    changed |= self._mark_mine(cell)
        return changed

    def _constraint_components(
        self, constraints: list[Constraint]
    ) -> list[tuple[set[Cell], list[Constraint]]]:
        useful = [constraint for constraint in constraints if constraint.cells]
        adjacency: dict[Cell, set[Cell]] = {}
        for constraint in useful:
            cells = set(constraint.cells)
            for cell in cells:
                adjacency.setdefault(cell, set()).update(cells - {cell})

        components: list[tuple[set[Cell], list[Constraint]]] = []
        seen: set[Cell] = set()
        for start in sorted(adjacency):
            if start in seen:
                continue
            stack = [start]
            cells: set[Cell] = set()
            while stack:
                cell = stack.pop()
                if cell in seen:
                    continue
                seen.add(cell)
                cells.add(cell)
                stack.extend(adjacency.get(cell, set()) - seen)
            component_constraints = [
                constraint for constraint in useful if constraint.cells & cells
            ]
            components.append((cells, component_constraints))
        return components

    def _enumerate_component_solutions(
        self, cells: set[Cell], constraints: list[Constraint]
    ) -> list[frozenset[Cell]]:
        ordered_cells = sorted(
            cells,
            key=lambda cell: (
                -sum(1 for constraint in constraints if cell in constraint.cells),
                cell[0],
                cell[1],
            ),
        )
        index = {cell: i for i, cell in enumerate(ordered_cells)}
        indexed_constraints = [
            (tuple(index[cell] for cell in constraint.cells), constraint.count)
            for constraint in constraints
        ]
        assignments = [-1] * len(ordered_cells)
        solutions: list[frozenset[Cell]] = []

        def is_consistent_partial() -> bool:
            for indices, required in indexed_constraints:
                assigned_mines = sum(1 for i in indices if assignments[i] == 1)
                unknown = sum(1 for i in indices if assignments[i] == -1)
                if assigned_mines > required:
                    return False
                if assigned_mines + unknown < required:
                    return False
            return True

        def backtrack(position: int) -> None:
            if len(solutions) >= self.max_model_solutions:
                return
            if position == len(ordered_cells):
                if all(
                    sum(1 for i in indices if assignments[i] == 1) == required
                    for indices, required in indexed_constraints
                ):
                    solutions.append(
                        frozenset(
                            cell
                            for cell, i in index.items()
                            if assignments[i] == 1
                        )
                    )
                return

            cell_index = position
            for value in (0, 1):
                assignments[cell_index] = value
                if is_consistent_partial():
                    backtrack(position + 1)
                assignments[cell_index] = -1

        backtrack(0)
        if len(solutions) >= self.max_model_solutions:
            return []
        return solutions

    def _apply_global_rules(self) -> bool:
        unknown = self.hidden - self.safe - self.mine - self.flagged
        remaining = self.total_mines - len(self.mine | self.flagged)
        changed = False
        if remaining < 0:
            self.inconsistencies.append("more mines flagged than total mines")
            return False
        if not unknown:
            return False
        if remaining == 0:
            for cell in unknown:
                changed |= self._mark_safe(cell)
        elif remaining == len(unknown):
            for cell in unknown:
                changed |= self._mark_mine(cell)
        return changed

    def _mark_safe(self, cell: Cell) -> bool:
        if cell in self.mine or cell in self.flagged:
            self.inconsistencies.append(f"cell inferred both safe and mine: {cell}")
            return False
        if cell in self.safe:
            return False
        self.safe.add(cell)
        return True

    def _mark_mine(self, cell: Cell) -> bool:
        if cell in self.safe or cell in self.revealed:
            self.inconsistencies.append(f"revealed/safe cell inferred as mine: {cell}")
            return False
        if cell in self.mine:
            return False
        self.mine.add(cell)
        return True
