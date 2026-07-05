# Minesweeper Solver with First-Order Logic

## Project Overview
Intelligent Minesweeper agent that uses first-order logic (FOL) and inference engines to solve the classic puzzle game without guessing. Implement logical deduction rules to identify safe cells and mines.

### Core Environment
- **Grid-based**: N×M grid with hidden mines and seed for map regeneration
- **Cell States**: Hidden, Revealed, or Flagged
- **Game Mechanics**: Reveal safe cells, flag mines, avoid detonations
- **Visual Interface**: PyGame-based visualization with real-time feedback


### Implementation Tasks
1. **FOL Representation**: Convert game state to logical facts and rules
2. **Inference Engine**: Use PyDatalog to deduce safe moves
3. **Rule Implementation**: Implementing *Saftey* and *Danger* rules to solving puzzles
4. **Game Loop**: Query engine, apply moves, update state iteratively

### Learning Objectives
- Represent game knowledge as first-order logic facts and rules
- Use logical inference engines (PyDatalog/Prolog) for deduction
- Handle partial information and uncertainty in puzzle solving
- Design heuristics for non-deterministic scenarios

**Technologies**: Python, PyGame, PyDatalog, SWI-Prolog


