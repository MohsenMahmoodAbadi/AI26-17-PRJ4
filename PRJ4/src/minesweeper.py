"""
Minesweeper environment for the PRJ4 first-order-logic solver.

The class intentionally exposes only game-facing actions and observations to
the solver. Test helpers can inspect the generated board through small public
methods, but the automatic agent never relies on hidden mine locations.
"""

from __future__ import annotations

import random
from typing import Iterable

import pygame


CELL_SIZE = 30
HUD_HEIGHT = 40

COLORS = {
    "bg": (190, 190, 190),
    "grid_line": (100, 100, 100),
    "cell_hidden": (160, 160, 160),
    "cell_revealed": (220, 220, 220),
    "text": (0, 0, 0),
    "mine": (0, 0, 0),
    "flag": (255, 0, 0),
    "hud_bg": (30, 30, 30),
    "hud_text": (255, 255, 255),
    "overlay_bg": (0, 0, 0, 200),
    "warning": (255, 50, 50),
}

MINE = -1
HIDDEN = 0
REVEALED = 1
FLAGGED = 2

Cell = tuple[int, int]


class MineSweeper:
    """Configurable Minesweeper board with a guaranteed zero-valued start."""

    def __init__(
        self,
        rows: int,
        cols: int,
        mines: int,
        seed: int | None = None,
        auto_flood_fill: bool = False,
        enable_gui: bool = True,
    ) -> None:
        if rows < 1 or cols < 1:
            raise ValueError("rows and cols must be positive")
        if mines < 0:
            raise ValueError("mines cannot be negative")

        self.rows = rows
        self.cols = cols
        self._start_pos = (rows // 2, cols // 2)
        self._total_mines = mines
        self._seed = seed
        self._auto_flood_fill = auto_flood_fill
        self.enable_gui = enable_gui
        self._rng = random.Random(None if seed is None or seed < 0 else seed)

        safe_zone = set(self._start_safe_zone())
        max_mines = rows * cols - len(safe_zone)
        if mines > max_mines:
            raise ValueError(
                f"too many mines for a guaranteed zero start; maximum is {max_mines}"
            )

        self.width = cols * CELL_SIZE
        self.height = rows * CELL_SIZE + HUD_HEIGHT
        self._grid_values = [[0 for _ in range(cols)] for _ in range(rows)]
        self.grid_visibility = [[HIDDEN for _ in range(cols)] for _ in range(rows)]
        self.game_over = False
        self.victory = False
        self._flags_placed = 0
        self._revealed_count = 0
        self._total_safe_cells = rows * cols - mines

        self.screen: pygame.Surface | None = None
        self.font: pygame.font.Font | None = None
        self.large_font: pygame.font.Font | None = None
        if self.enable_gui:
            pygame.init()
            self.screen = pygame.display.set_mode((self.width, self.height))
            pygame.display.set_caption("Minesweeper FOL Solver")
            self.font = pygame.font.SysFont("Arial", 18, bold=True)
            self.large_font = pygame.font.SysFont("Arial", 32, bold=True)

        self._generate_board()

    @property
    def total_mines(self) -> int:
        return self._total_mines

    @property
    def total_safe_cells(self) -> int:
        return self._total_safe_cells

    @property
    def revealed_count(self) -> int:
        return self._revealed_count

    @property
    def flags_placed(self) -> int:
        return self._flags_placed

    @property
    def progress(self) -> float:
        if self._total_safe_cells == 0:
            return 1.0
        return self._revealed_count / self._total_safe_cells

    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.rows and 0 <= c < self.cols

    def get_start_pos(self) -> Cell:
        return self._start_pos

    def get_neighbors(self, r: int, c: int) -> list[Cell]:
        self._require_in_bounds(r, c)
        neighbors: list[Cell] = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if self.in_bounds(nr, nc):
                    neighbors.append((nr, nc))
        return neighbors

    def get_clue(self, r: int, c: int) -> int:
        self._require_in_bounds(r, c)
        return self._grid_values[r][c]

    def is_mine(self, r: int, c: int) -> bool:
        self._require_in_bounds(r, c)
        return self._grid_values[r][c] == MINE

    def visibility_at(self, r: int, c: int) -> int:
        self._require_in_bounds(r, c)
        return self.grid_visibility[r][c]

    def all_cells(self) -> Iterable[Cell]:
        for r in range(self.rows):
            for c in range(self.cols):
                yield (r, c)

    def reveal(self, r: int, c: int) -> int | None:
        """Reveal a hidden cell and return MINE or its clue value."""
        if self.game_over or not self.in_bounds(r, c):
            return None
        if self.grid_visibility[r][c] != HIDDEN:
            return None

        self.grid_visibility[r][c] = REVEALED
        self._revealed_count += 1
        value = self._grid_values[r][c]

        if value == MINE:
            self.game_over = True
            self.victory = False
            print(f"Game Over! Mine at ({r}, {c})")
            return MINE

        if value == 0 and self._auto_flood_fill:
            self._flood_fill(r, c)

        self._check_victory()
        return value

    def flag(self, r: int, c: int) -> bool:
        """Flag a hidden cell. Returns True only when the board changed."""
        if self.game_over or not self.in_bounds(r, c):
            return False
        if self.grid_visibility[r][c] != HIDDEN:
            return False

        self.grid_visibility[r][c] = FLAGGED
        self._flags_placed += 1
        self._check_victory()
        return True

    def unflag(self, r: int, c: int) -> bool:
        """Remove a flag from a flagged cell."""
        if self.game_over or not self.in_bounds(r, c):
            return False
        if self.grid_visibility[r][c] != FLAGGED:
            return False

        self.grid_visibility[r][c] = HIDDEN
        self._flags_placed -= 1
        return True

    def render_text(self, show_mines: bool = False) -> str:
        """Return a compact ASCII board for CLI runs and tests."""
        lines: list[str] = []
        for r in range(self.rows):
            row: list[str] = []
            for c in range(self.cols):
                vis = self.grid_visibility[r][c]
                val = self._grid_values[r][c]
                if vis == REVEALED:
                    row.append(" " if val == 0 else str(val))
                elif vis == FLAGGED:
                    row.append("F")
                elif show_mines and val == MINE:
                    row.append("*")
                else:
                    row.append(".")
            lines.append(" ".join(row))
        return "\n".join(lines)

    def render(self) -> None:
        if not self.enable_gui:
            print(self.render_text(show_mines=self.game_over))
            return
        if self.screen is None or self.font is None:
            return

        self.screen.fill(COLORS["bg"])
        for r in range(self.rows):
            for c in range(self.cols):
                rect = pygame.Rect(c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                visibility = self.grid_visibility[r][c]
                value = self._grid_values[r][c]

                if visibility == REVEALED:
                    pygame.draw.rect(self.screen, COLORS["cell_revealed"], rect)
                    pygame.draw.rect(self.screen, COLORS["grid_line"], rect, 1)
                    if value == MINE:
                        pygame.draw.circle(self.screen, COLORS["mine"], rect.center, 8)
                    elif value > 0:
                        text = self.font.render(
                            str(value), True, self._get_number_color(value)
                        )
                        self.screen.blit(text, text.get_rect(center=rect.center))
                elif visibility == FLAGGED:
                    pygame.draw.rect(self.screen, COLORS["cell_hidden"], rect)
                    pygame.draw.rect(self.screen, (255, 255, 255), rect, 2)
                    pygame.draw.circle(self.screen, COLORS["flag"], rect.center, 6)
                else:
                    pygame.draw.rect(self.screen, COLORS["cell_hidden"], rect)
                    pygame.draw.rect(self.screen, (240, 240, 240), rect, 2)

        self._draw_hud()
        if self.game_over:
            self._draw_overlay()
        pygame.display.flip()

    def _generate_board(self) -> None:
        safe_zone = set(self._start_safe_zone())
        mines_placed = 0
        while mines_placed < self._total_mines:
            r = self._rng.randint(0, self.rows - 1)
            c = self._rng.randint(0, self.cols - 1)
            if (r, c) in safe_zone or self._grid_values[r][c] == MINE:
                continue
            self._grid_values[r][c] = MINE
            mines_placed += 1

        for r, c in self.all_cells():
            if self._grid_values[r][c] == MINE:
                continue
            self._grid_values[r][c] = sum(
                1 for nr, nc in self.get_neighbors(r, c) if self._grid_values[nr][nc] == MINE
            )

    def _start_safe_zone(self) -> list[Cell]:
        center_r, center_c = self._start_pos
        zone: list[Cell] = []
        for r in range(center_r - 1, center_r + 2):
            for c in range(center_c - 1, center_c + 2):
                if self.in_bounds(r, c):
                    zone.append((r, c))
        return zone

    def _flood_fill(self, r: int, c: int) -> None:
        stack = [(r, c)]
        visited = {(r, c)}
        while stack:
            current_r, current_c = stack.pop()
            for nr, nc in self.get_neighbors(current_r, current_c):
                if (nr, nc) in visited or self.grid_visibility[nr][nc] != HIDDEN:
                    continue
                if self._grid_values[nr][nc] == MINE:
                    continue
                visited.add((nr, nc))
                self.grid_visibility[nr][nc] = REVEALED
                self._revealed_count += 1
                if self._grid_values[nr][nc] == 0:
                    stack.append((nr, nc))
        self._check_victory()

    def _check_victory(self) -> bool:
        if self._revealed_count != self._total_safe_cells:
            return False
        if self._flags_placed != self._total_mines:
            return False
        for r, c in self.all_cells():
            if self._grid_values[r][c] == MINE and self.grid_visibility[r][c] != FLAGGED:
                return False
        self.game_over = True
        self.victory = True
        return True

    def _draw_hud(self) -> None:
        if self.screen is None:
            return
        hud_rect = pygame.Rect(0, self.rows * CELL_SIZE, self.width, HUD_HEIGHT)
        pygame.draw.rect(self.screen, COLORS["hud_bg"], hud_rect)
        pygame.draw.line(
            self.screen,
            (100, 100, 100),
            (0, hud_rect.top),
            (self.width, hud_rect.top),
            2,
        )

        hud_font = pygame.font.Font(None, 20)
        pct = int(self.progress * 100)
        flag_color = (
            COLORS["warning"]
            if self._flags_placed > self._total_mines
            else COLORS["hud_text"]
        )
        progress_text = hud_font.render(f"Progress: {pct}%", True, COLORS["hud_text"])
        flags_text = hud_font.render(
            f"Flags: {self._flags_placed}/{self._total_mines}", True, flag_color
        )
        self.screen.blit(progress_text, (10, hud_rect.centery - 10))
        self.screen.blit(flags_text, (max(10, self.width - 125), hud_rect.centery - 10))

    def _draw_overlay(self) -> None:
        if self.screen is None or self.font is None or self.large_font is None:
            return
        overlay = pygame.Surface((self.width, self.rows * CELL_SIZE), pygame.SRCALPHA)
        overlay.fill(COLORS["overlay_bg"])
        self.screen.blit(overlay, (0, 0))

        panel_width, panel_height = 300, 150
        rect = pygame.Rect(
            (self.width - panel_width) // 2,
            (self.rows * CELL_SIZE - panel_height) // 2,
            panel_width,
            panel_height,
        )
        title = "VICTORY!" if self.victory else "GAME OVER"
        color = (0, 180, 0) if self.victory else (200, 0, 0)
        title_surface = self.large_font.render(title, True, color)
        stats_surface = self.font.render(
            f"Flags Correct: {self._count_correct_flags()}/{self._total_mines}",
            True,
            (255, 255, 255),
        )
        self.screen.blit(
            title_surface, title_surface.get_rect(center=(rect.centerx, rect.top + 40))
        )
        self.screen.blit(
            stats_surface, stats_surface.get_rect(center=(rect.centerx, rect.top + 90))
        )

    def _count_correct_flags(self) -> int:
        return sum(
            1
            for r, c in self.all_cells()
            if self.grid_visibility[r][c] == FLAGGED and self._grid_values[r][c] == MINE
        )

    def _require_in_bounds(self, r: int, c: int) -> None:
        if not self.in_bounds(r, c):
            raise IndexError(f"cell ({r}, {c}) is outside the board")

    @staticmethod
    def _get_number_color(n: int) -> tuple[int, int, int]:
        return {
            1: (0, 0, 255),
            2: (0, 128, 0),
            3: (255, 0, 0),
            4: (0, 0, 128),
            5: (128, 0, 128),
            6: (0, 255, 255),
            7: (128, 0, 0),
            8: (128, 128, 128),
        }.get(n, COLORS["text"])
