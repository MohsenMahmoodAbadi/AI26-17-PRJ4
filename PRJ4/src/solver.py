"""Automatic Minesweeper solver built on the logical knowledge base."""

from __future__ import annotations

from dataclasses import dataclass
import time

import pygame

from src.knowledge_base import AGENT_FLAGGED, AGENT_UNKNOWN, Cell, MinesweeperKnowledgeBase
from src.minesweeper import FLAGGED, HIDDEN, MINE, REVEALED, MineSweeper


@dataclass
class SolverResult:
    victory: bool
    lost: bool
    stopped: bool
    steps: int
    deterministic_moves: int
    guesses: int
    revealed: int
    flagged: int
    progress: float


class LogicalMinesweeperAgent:
    """Keeps a shadow board, synchronizes a KB, and plays deterministic moves."""

    def __init__(
        self,
        game: MineSweeper,
        allow_guess: bool = True,
        render: bool = True,
        delay: float = 0.0,
        verbose: bool = True,
        max_steps: int | None = None,
    ) -> None:
        self.game = game
        self.allow_guess = allow_guess
        self.render_enabled = render
        self.delay = delay
        self.verbose = verbose
        self.max_steps = max_steps or max(16, game.rows * game.cols * 4)
        self.agent_board: dict[Cell, int] = {
            (r, c): AGENT_UNKNOWN for r in range(game.rows) for c in range(game.cols)
        }
        self.kb = MinesweeperKnowledgeBase(game.rows, game.cols, game.total_mines)
        self.steps = 0
        self.deterministic_moves = 0
        self.guesses = 0

    def run(self) -> SolverResult:
        start = self.game.get_start_pos()
        self._log(f"Starting at guaranteed safe position: {start}")
        self._reveal(start, reason="initial safe cell")
        self._sync_from_environment()
        self._render()

        stopped = False
        while not self.game.game_over and self.steps < self.max_steps:
            self.steps += 1
            self._pump_events()
            self._sync_from_environment()
            self.kb.sync_from_agent_board(self.agent_board)
            safe_cells, mine_cells = self.kb.infer()

            acted = False
            for cell in sorted(mine_cells):
                if self._flag(cell, reason="deterministic mine inference"):
                    self.deterministic_moves += 1
                    acted = True

            for cell in sorted(safe_cells):
                if self.game.game_over:
                    break
                if self._reveal(cell, reason="deterministic safe inference"):
                    self.deterministic_moves += 1
                    acted = True

            if acted:
                self._render()
                continue

            self._sync_from_environment()
            self.kb.sync_from_agent_board(self.agent_board)
            self.kb.infer()
            guess = self.kb.choose_safest_guess()
            if self.allow_guess and guess is not None:
                probabilities = self.kb.estimate_mine_probabilities()
                probability = probabilities.get(guess, 1.0)
                self.guesses += 1
                self._log(
                    f"No deterministic move; guessing {guess} "
                    f"(estimated mine risk {probability:.2%})"
                )
                self._reveal(guess, reason="guess")
                self._render()
            else:
                self._log("No deterministic move remains; stopping without guessing.")
                stopped = True
                break

        if self.steps >= self.max_steps and not self.game.game_over:
            self._log(f"Stopped after reaching max_steps={self.max_steps}.")
            stopped = True

        self._sync_from_environment()
        return SolverResult(
            victory=self.game.victory,
            lost=self.game.game_over and not self.game.victory,
            stopped=stopped,
            steps=self.steps,
            deterministic_moves=self.deterministic_moves,
            guesses=self.guesses,
            revealed=self.game.revealed_count,
            flagged=self.game.flags_placed,
            progress=self.game.progress,
        )

    def _reveal(self, cell: Cell, reason: str) -> bool:
        r, c = cell
        if self.agent_board.get(cell) != AGENT_UNKNOWN:
            return False
        if self.game.visibility_at(r, c) != HIDDEN:
            self._sync_cell_from_environment(cell)
            return False

        value = self.game.reveal(r, c)
        if value is None:
            self._sync_cell_from_environment(cell)
            return False
        if value == MINE:
            self.agent_board[cell] = MINE
            self._log(f"Revealed mine at {cell} by {reason}.")
        else:
            self.agent_board[cell] = value
            self._log(f"Revealed {cell} = {value} by {reason}.")
        return True

    def _flag(self, cell: Cell, reason: str) -> bool:
        r, c = cell
        if self.agent_board.get(cell) == AGENT_FLAGGED:
            return False
        if self.game.visibility_at(r, c) == FLAGGED:
            self.agent_board[cell] = AGENT_FLAGGED
            return False
        if self.game.visibility_at(r, c) != HIDDEN:
            self._sync_cell_from_environment(cell)
            return False

        changed = self.game.flag(r, c)
        if changed:
            self.agent_board[cell] = AGENT_FLAGGED
            self._log(f"Flagged {cell} by {reason}.")
        return changed

    def _sync_from_environment(self) -> None:
        for r in range(self.game.rows):
            for c in range(self.game.cols):
                self._sync_cell_from_environment((r, c))

    def _sync_cell_from_environment(self, cell: Cell) -> None:
        r, c = cell
        visibility = self.game.visibility_at(r, c)
        if visibility == REVEALED:
            value = self.game.get_clue(r, c)
            self.agent_board[cell] = value
        elif visibility == FLAGGED:
            self.agent_board[cell] = AGENT_FLAGGED
        elif self.agent_board.get(cell) not in (AGENT_FLAGGED, MINE):
            self.agent_board[cell] = AGENT_UNKNOWN

    def _render(self) -> None:
        if not self.render_enabled:
            return
        self.game.render()
        if self.delay > 0:
            time.sleep(self.delay)

    def _pump_events(self) -> None:
        if not self.game.enable_gui:
            return
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.render_enabled = False
                self.game.enable_gui = False

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)
