from __future__ import annotations

import argparse
import os
import sys


os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
if "--no-gui" in sys.argv:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from src.knowledge_base import AGENT_UNKNOWN, MinesweeperKnowledgeBase
from src.minesweeper import MineSweeper
from src.solver import LogicalMinesweeperAgent, SolverResult


SCENARIOS = {
    "simple": {"rows": 9, "cols": 9, "mines": 9, "seed": 99},
    "standard": {"rows": 15, "cols": 15, "mines": 35, "seed": 2},
    "challenge": {"rows": 20, "cols": 20, "mines": 5, "seed": 23},
    "large": {"rows": 80, "cols": 80, "mines": 200, "seed": -1},
}

_GLOBAL_KB: MinesweeperKnowledgeBase | None = None


def init_static_facts(rows: int, cols: int, mines: int = 0) -> MinesweeperKnowledgeBase:
    """Create static cell and neighbor facts for compatibility with the starter."""
    global _GLOBAL_KB
    _GLOBAL_KB = MinesweeperKnowledgeBase(rows, cols, mines)
    return _GLOBAL_KB


def init_rules() -> None:
    """Rules are implemented by forward chaining in MinesweeperKnowledgeBase."""
    return None


def update_knowledge_base(
    agent_board: dict[tuple[int, int], int],
    rows: int | None = None,
    cols: int | None = None,
    mines: int | None = None,
) -> dict[str, int]:
    """Synchronize dynamic predicate facts from the agent shadow board."""
    global _GLOBAL_KB
    if _GLOBAL_KB is None:
        if rows is None or cols is None:
            raise ValueError("rows and cols are required before static facts exist")
        _GLOBAL_KB = MinesweeperKnowledgeBase(rows, cols, mines or 0)
    elif mines is not None:
        _GLOBAL_KB.total_mines = mines
    _GLOBAL_KB.sync_from_agent_board(agent_board)
    return _GLOBAL_KB.fact_summary()


def query_solver() -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Query inferred Safe(R, C) and Mine(R, C) predicates."""
    if _GLOBAL_KB is None:
        raise RuntimeError("knowledge base is not initialized")
    safe_moves, mine_moves = _GLOBAL_KB.infer()
    return sorted(safe_moves), sorted(mine_moves)


def get_safest_guess(
    agent_board: dict[tuple[int, int], int],
    rows: int,
    cols: int,
    mines: int = 0,
) -> tuple[int, int] | None:
    kb = MinesweeperKnowledgeBase(rows, cols, mines)
    kb.sync_from_agent_board(agent_board)
    kb.infer()
    return kb.choose_safest_guess()


def prolog_solver(
    game: MineSweeper,
    allow_guess: bool = True,
    render: bool = True,
    delay: float = 0.0,
    verbose: bool = True,
    max_steps: int | None = None,
) -> SolverResult:
    """Run the automatic logical solver on a MineSweeper instance."""
    init_static_facts(game.rows, game.cols, game.total_mines)
    init_rules()
    agent = LogicalMinesweeperAgent(
        game=game,
        allow_guess=allow_guess,
        render=render,
        delay=delay,
        verbose=verbose,
        max_steps=max_steps,
    )
    return agent.run()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Minesweeper FOL solver")
    parser.add_argument("--mode", choices=("auto", "manual"), default="auto")
    parser.add_argument("--scenario", choices=tuple(SCENARIOS), default=None)
    parser.add_argument("--rows", type=int, default=None)
    parser.add_argument("--cols", type=int, default=None)
    parser.add_argument("--mines", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--auto-flood-fill", action="store_true")
    parser.add_argument("--no-gui", action="store_true")
    parser.add_argument("--no-render", action="store_true")
    parser.add_argument("--delay", type=float, default=0.0)
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument("--no-guess", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--show-board", action="store_true")
    return parser


def resolve_config(args: argparse.Namespace) -> dict[str, int]:
    config = dict(SCENARIOS.get(args.scenario or "simple", SCENARIOS["simple"]))
    for key in ("rows", "cols", "mines", "seed"):
        value = getattr(args, key)
        if value is not None:
            config[key] = value
    return config


def run_auto(args: argparse.Namespace) -> SolverResult:
    config = resolve_config(args)
    game = MineSweeper(
        rows=config["rows"],
        cols=config["cols"],
        mines=config["mines"],
        seed=config["seed"],
        auto_flood_fill=args.auto_flood_fill,
        enable_gui=not args.no_gui,
    )
    result = prolog_solver(
        game,
        allow_guess=not args.no_guess,
        render=not args.no_render and not args.no_gui,
        delay=args.delay,
        verbose=not args.quiet,
        max_steps=args.max_steps,
    )

    print(format_result(result, config))
    if args.show_board:
        print(game.render_text(show_mines=game.game_over))
    return result


def run_manual(args: argparse.Namespace) -> None:
    if args.no_gui:
        raise ValueError("manual mode requires the GUI")
    from manual import ManualController

    config = resolve_config(args)
    controller = ManualController(
        rows=config["rows"],
        cols=config["cols"],
        mines=config["mines"],
        seed=config["seed"],
        auto_flood_fill=True,
    )
    controller.run()


def format_result(result: SolverResult, config: dict[str, int]) -> str:
    status = "victory" if result.victory else "loss" if result.lost else "stopped"
    return (
        f"Result: {status} | board={config['rows']}x{config['cols']} "
        f"mines={config['mines']} seed={config['seed']} | "
        f"steps={result.steps} deterministic={result.deterministic_moves} "
        f"guesses={result.guesses} revealed={result.revealed} "
        f"flagged={result.flagged} progress={result.progress:.1%}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.mode == "manual":
        run_manual(args)
    else:
        run_auto(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
