import pygame
import time
import random
from pyDatalog import pyDatalog
from src.minesweeper import MineSweeper

# =========================================================================
# Section 1: Define First-Order Logic Terms (FOL Terms)
# Students should define the required terms, facts, and rules for pyDatalog here.
# =========================================================================
# Hint: pyDatalog.create_terms('X, Y, R, C, ...')


# Suggested constants for the agent's internal memory (Shadow Board)
AGENT_UNKNOWN = -1
AGENT_FLAGGED = -2

# =========================================================================
# Section 2: Generation of Logical Facts and Rules
# =========================================================================

def init_static_facts(rows, cols):
    """
    Task 1: Generate static facts at the beginning of the game 
    (e.g., adjacency relationships between cells).
    """
    pass

def init_rules():
    """
    Task 2: Define logical inference rules (Safety Rule and Danger Rule).
    According to the project documentation, rules must be defined based on first-order logic.
    """
    # Safe(R2, C2) <= (...)
    # Mine(R2, C2) <= (...)
    pass

def update_knowledge_base(agent_board, rows, cols):
    """
    Task 3: Convert the agent's internal memory (agent_board) into dynamic facts in each turn.
    Before adding new facts, facts from the previous turn must be cleared.
    """
    pass

def query_solver():
    """
    Task 4: Query the inference engine to find safe cells and mines.
    Output: Two lists containing the coordinates of safe cells and mine cells.
    """
    safe_moves = []
    mine_moves = []
    
    # Code for querying Safe(R, C) and Mine(R, C)
    
    return safe_moves, mine_moves

# =========================================================================
# Section 3: Uncertainty Handling Strategy (Smart Guess) - Optional/Bonus
# =========================================================================

def get_safest_guess(agent_board, rows, cols):
    """
    Task 5 (Optional): Calculate the probability of cells being mines during a logical deadlock.
    """
    return None

# =========================================================================
# Section 4: Main Agent Loop
# =========================================================================

def prolog_solver(game):
    # Initialize static facts and rules
    init_static_facts(game.rows, game.cols)
    init_rules()
    
    # Create agent's internal memory (Shadow Board) - initially all cells are unknown
    agent_board = {}
    for r in range(game.rows):
        for c in range(game.cols):
            agent_board[(r, c)] = AGENT_UNKNOWN

    # Get starting position (Guaranteed to be 0 and safe according to the project documentation)
    start_r, start_c = game.get_start_pos()
    print(f"Starting at guaranteed safe position: {start_r}, {start_c}")
    
    # First move: Reveal the starting cell and record it in the agent's memory
    start_val = game.reveal(start_r, start_c)
    agent_board[(start_r, start_c)] = start_val if start_val is not None else 0
    
    running = True
    while running and not game.game_over:
        # Handle Pygame events to prevent the window from freezing/crashing
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # 1. Update the knowledge base based on the latest state of the agent's memory
        update_knowledge_base(agent_board, game.rows, game.cols)

        # 2. Query the logic engine
        safe_moves, mine_moves = query_solver()
        move_made = False

        # 3. Apply the extracted logical actions to the game environment and update memory
        # Hint: Reveal safe cells first, then flag the mine cells.
        
        # 4. Deadlock management (if no deterministic logical move is found)
        if not move_made and not game.game_over:
            print("Logical deadlock! Attempting guess...")
            # First use the Heuristic, and if no data is available, make a completely random choice
            pass

        # Render the environment and add a short delay to observe the solving process
        game.render()
        time.sleep(0.2)

    # Keep the window open after the game ends
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        game.render()

if __name__ == "__main__":
    # Default settings based on the first scenario (Simple level) in the evaluation table
    # Note: auto_flood_fill must be False to preserve the encapsulation of the agent's memory.
    ms = MineSweeper(rows=9, cols=9, mines=10, seed=99, auto_flood_fill=False)
    prolog_solver(ms)