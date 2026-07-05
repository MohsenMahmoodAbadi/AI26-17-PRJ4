"""
University: University of Isfahan
Faculty: Mathematics and Statistics
Branch: Computer Science
Course: Artificial Intelligence
Professor: Dr. Faria Nasiri Mofakham
TAs: MehrAzin Marzough, Mohammad Karimi, Anahita Honarmandian
Project: Minesweeper Solver with First-Order Logic


This environment implements the classic Minesweeper game with a focus on
solving it using first-order logic and inference engines. The project
requires implementing logical deduction rules to identify safe cells and
mines without random guessing.

Key Components:
- MineSweeper: Main game environment with PyGame visualization
- Inference Engine: PyDatalog or Prolog-based logic system
- Rule Base: Safety and danger rules for deterministic deduction
- Agent: Logical agent that queries the inference engine for moves

Environment Features:
- Configurable grid sizes and mine counts
- Guaranteed safe starting position (always a zero)
- Visualization of game state
- Flagging and revealing actions
- Victory/defeat conditions
- Progress tracking and statistics

Game Rules:
- Cells contain numbers (0-8) indicating adjacent mines
- Flag cells suspected to contain mines
- Reveal safe cells to expand the known area
- Win by flagging all mines and revealing all safe cells

Logical Rules to Implement:
1. Safety Rule: If a cell's number equals its flagged neighbors, all remaining hidden neighbors are safe
2. Danger Rule: If a cell's number equals its total hidden neighbors, all hidden neighbors are mines

"""

import pygame
import random


# --- Constants ---
CELL_SIZE = 30
HUD_HEIGHT = 40
COLORS = {
    'bg': (190, 190, 190),
    'grid_line': (100, 100, 100),
    'cell_hidden': (160, 160, 160),
    'cell_revealed': (220, 220, 220),
    'text': (0, 0, 0),
    'mine': (0, 0, 0),
    'flag': (255, 0, 0),
    'hud_bg': (30, 30, 30),
    'hud_text': (255, 255, 255),
    'overlay_bg': (0, 0, 0, 200),
    'warning': (255, 50, 50)
}
MINE = -1
HIDDEN = 0
REVEALED = 1
FLAGGED = 2


class MineSweeper:
    def __init__(self, rows, cols, mines, seed=None, auto_flood_fill=False):
        if rows < 1 or cols < 1 or mines < 1:
            raise ValueError("rows, cols and mines must be positive")
        self.rows = rows
        self.cols = cols
        self._start_pos = (self.rows // 2, self.cols // 2)
        self._total_mines = mines
        self._seed = seed
        self._auto_flood_fill = auto_flood_fill

        # Dimensions
        self.width = cols * CELL_SIZE
        self.height = (rows * CELL_SIZE) + HUD_HEIGHT
        
        # Game State
        self._grid_values = [[0 for _ in range(cols)] for _ in range(rows)]
        self.grid_visibility = [[HIDDEN for _ in range(cols)] for _ in range(rows)] # 0:Hidden, 1:Rev, 2:Flag
        self.game_over = False
        self.victory = False
        self._flags_placed = 0
        self._revealed_count = 0
        self._total_safe_cells = (rows * cols) - mines
        
        # Pygame Setup
        pygame.init()
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Prolog Environment")
        self.font = pygame.font.SysFont('Arial', 18, bold=True)
        self.large_font = pygame.font.SysFont('Arial', 32, bold=True)

        self._generate_board()

    def _generate_board(self):
        """Generates board with a GUARANTEED 0-value start at center."""
        if self._seed is not None and self._seed > -1:
            random.seed(self._seed)

        if self._total_mines > (self.rows * self.cols) // 2:
            raise ValueError("Too many mines")

        center_r, center_c = self._start_pos
        safe_zone = []
        for r in range(center_r - 1, center_r + 2):
            for c in range(center_c - 1, center_c + 2):
                if 0 <= r < self.rows and 0 <= c < self.cols:
                    safe_zone.append((r, c))

        # Place Mines (Excluding Safe Zone)
        mines_placed = 0
        while mines_placed < self._total_mines:
            r = random.randint(0, self.rows - 1)
            c = random.randint(0, self.cols - 1)
            
            if (r, c) not in safe_zone and self._grid_values[r][c] != MINE:
                self._grid_values[r][c] = MINE
                mines_placed += 1

        # Calculate Clues
        for r in range(self.rows):
            for c in range(self.cols):
                if self._grid_values[r][c] == MINE: continue
                count = 0
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        if dr == 0 and dc == 0: continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < self.rows and 0 <= nc < self.cols:
                            if self._grid_values[nr][nc] == MINE:
                                count += 1
                self._grid_values[r][c] = count

        # Reveal Center (Guaranteed to be 0 and safe)
        self.grid_visibility[center_r][center_c] = REVEALED
        self._revealed_count += 1
        if self._auto_flood_fill:
            self._flood_fill(center_r, center_c)

    # --- Actions ---

    def reveal(self, r, c):
        if self.game_over: return
        if not (0 <= r < self.rows and 0 <= c < self.cols): return
        if self.grid_visibility[r][c] != 0: return # Must be hidden

        # Execute Reveal
        self.grid_visibility[r][c] = 1
        self._revealed_count += 1

        # Check Logic
        val = self._grid_values[r][c]
        
        if val == MINE:
            self.game_over = True
            self.victory = False
            print(f"Game Over! Mine at {r}, {c}")
        elif val == 0 and self._auto_flood_fill:
            self._flood_fill(r, c)
        
        self._check_victory()

        if val == MINE:
            return MINE
        else:
            return val
        

    def flag(self, r, c):
        if self.game_over: return
        if not (0 <= r < self.rows and 0 <= c < self.cols): return
        if self.grid_visibility[r][c] == FLAGGED: return

        self.grid_visibility[r][c] = FLAGGED
        self._flags_placed += 1

        self._check_victory()


    def unflag(self, r, c):
        if self.game_over: return
        if not (0 <= r < self.rows and 0 <= c < self.cols): return
        if self.grid_visibility[r][c] == HIDDEN: return

        self.grid_visibility[r][c] = HIDDEN
        self._flags_placed -= 1

    def get_start_pos(self):
        return self._start_pos

    def _flood_fill(self, r, c):
        """Recursive reveal for zero-islands."""
        stack = [(r, c)]
        visited = set(stack)
        while stack:
            curr_r, curr_c = stack.pop()
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    nr, nc = curr_r + dr, curr_c + dc
                    if 0 <= nr < self.rows and 0 <= nc < self.cols:
                        if (nr, nc) not in visited and self.grid_visibility[nr][nc] == 0:
                            visited.add((nr, nc))
                            self.grid_visibility[nr][nc] = 1
                            self._revealed_count += 1
                            if self._grid_values[nr][nc] == 0:
                                stack.append((nr, nc))
        self._check_victory()

    def _check_victory(self):
        if self._revealed_count == self._total_safe_cells:
            self.game_over = True
            self.victory = True
            return True
        return False

    # --- Rendering ---

    def render(self):
        self.screen.fill(COLORS['bg'])
        
        # Draw Grid
        for r in range(self.rows):
            for c in range(self.cols):
                rect = pygame.Rect(c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                vis = self.grid_visibility[r][c]
                val = self._grid_values[r][c]
                
                if vis == REVEALED:
                    pygame.draw.rect(self.screen, COLORS['cell_revealed'], rect)
                    pygame.draw.rect(self.screen, COLORS['grid_line'], rect, 1)
                    if val == MINE:
                        pygame.draw.circle(self.screen, COLORS['mine'], rect.center, 8)
                    elif val > 0:
                        txt = self.font.render(str(val), True, self._get_number_color(val))
                        self.screen.blit(txt, txt.get_rect(center=rect.center))
                elif vis == FLAGGED:
                    pygame.draw.rect(self.screen, COLORS['cell_hidden'], rect)
                    pygame.draw.rect(self.screen, (255, 255, 255), rect, 2)
                    pygame.draw.circle(self.screen, COLORS['flag'], rect.center, 6)
                elif vis == HIDDEN:
                    pygame.draw.rect(self.screen, COLORS['cell_hidden'], rect)
                    pygame.draw.rect(self.screen, (240, 240, 240), rect, 2)

        # Draw HUD (Bottom Panel)
        self._draw_hud()

        # Draw Game Over Overlay
        if self.game_over:
            self._draw_overlay()

        pygame.display.flip()

    



    def _draw_hud(self):
        hud_rect = pygame.Rect(0, self.rows * CELL_SIZE, self.width, 50)
        pygame.draw.rect(self.screen, COLORS['hud_bg'], hud_rect)
        pygame.draw.line(self.screen, (100, 100, 100),
                        (0, hud_rect.top),
                        (self.width, hud_rect.top),
                        2)
        
        hud_font = pygame.font.Font(None, 20)

        # Progress Calc
        pct = int((self._revealed_count / self._total_safe_cells) * 100)
        
        # Flag Color Logic
        flag_color = COLORS['warning'] if self._flags_placed > self._total_mines else COLORS['hud_text']
        
        txt_progress = hud_font.render(f"Progress: {pct}%", True, COLORS['hud_text'])
        txt_flags = hud_font.render(f"Flags: {self._flags_placed}/{self._total_mines}", True, flag_color)
        
        self.screen.blit(txt_progress, (10, hud_rect.centery - 10))
        self.screen.blit(txt_flags, (self.width - 120, hud_rect.centery - 10))

    def _draw_overlay(self):
        overlay = pygame.Surface((self.width, self.rows * CELL_SIZE), pygame.SRCALPHA)
        overlay.fill(COLORS['overlay_bg'])
        self.screen.blit(overlay, (0, 0))
        
        # Overlay panel
        w, h = 300, 150
        rect = pygame.Rect((self.width - w)//2, (self.rows * CELL_SIZE - h)//2, w, h)

        title = "VICTORY!" if self.victory else "GAME OVER"
        col = (0, 180, 0) if self.victory else (200, 0, 0)
        
        t_surf = self.large_font.render(title, True, col)
        
        # Final Stats
        s_surf = self.font.render(f"Flags Correct: {self._count_correct_flags()}/{self._total_mines}",
                                  True,
                                  (255, 255, 255))
        
        self.screen.blit(t_surf, t_surf.get_rect(center=(rect.centerx, rect.top + 40)))
        self.screen.blit(s_surf, s_surf.get_rect(center=(rect.centerx, rect.top + 90)))

    @staticmethod
    def _get_number_color(n):
        return {
            1: (0, 0, 255),
            2: (0, 128, 0),
            3: (255, 0, 0),
            4: (0, 0, 128),
            5: (128, 0, 128),
            6: (0, 255, 255),
            7: (128, 0, 0),
            8: (128, 128, 128)
        }.get(n)

    def _count_correct_flags(self):
        if self.victory:
            return self._total_mines
        else:
            correct_flags = 0
            for row in range(self.rows):
                for col in range(self.cols):
                    if self.grid_visibility[row][col] == FLAGGED and self._grid_values[row][col] == MINE:
                        correct_flags += 1
            return correct_flags