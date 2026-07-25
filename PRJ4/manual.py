from __future__ import annotations

import argparse
import os
import sys


os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from src.minesweeper import CELL_SIZE, FLAGGED, HIDDEN, MineSweeper


class ManualController:
    def __init__(
        self,
        rows: int = 15,
        cols: int = 15,
        mines: int = 35,
        seed: int | None = 2,
        auto_flood_fill: bool = True,
    ) -> None:
        self.rows = rows
        self.cols = cols
        self.mines = mines
        self.seed = seed
        self.auto_flood_fill = auto_flood_fill
        self.clock = pygame.time.Clock()
        self.game: MineSweeper
        self.reset()

    def reset(self) -> None:
        self.game = MineSweeper(
            rows=self.rows,
            cols=self.cols,
            mines=self.mines,
            seed=self.seed,
            auto_flood_fill=self.auto_flood_fill,
            enable_gui=True,
        )

    def run(self) -> None:
        print("Starting manual game.")
        print("Left click: reveal | Right click: flag/unflag")

        while True:
            self._handle_input()
            self.game.render()
            self.clock.tick(30)

    def _handle_input(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if self.game.game_over and event.type == pygame.MOUSEBUTTONDOWN:
                print("Restarting...")
                self.reset()
                continue

            if self.game.game_over or event.type != pygame.MOUSEBUTTONDOWN:
                continue

            x, y = pygame.mouse.get_pos()
            if y >= self.game.rows * CELL_SIZE:
                continue

            c = x // CELL_SIZE
            r = y // CELL_SIZE
            if event.button == 1:
                self.game.reveal(r, c)
            elif event.button == 3:
                visibility = self.game.grid_visibility[r][c]
                if visibility == HIDDEN:
                    self.game.flag(r, c)
                elif visibility == FLAGGED:
                    self.game.unflag(r, c)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manual Minesweeper mode")
    parser.add_argument("--rows", type=int, default=15)
    parser.add_argument("--cols", type=int, default=15)
    parser.add_argument("--mines", type=int, default=35)
    parser.add_argument("--seed", type=int, default=2)
    parser.add_argument("--no-auto-flood-fill", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    controller = ManualController(
        rows=args.rows,
        cols=args.cols,
        mines=args.mines,
        seed=args.seed,
        auto_flood_fill=not args.no_auto_flood_fill,
    )
    controller.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
