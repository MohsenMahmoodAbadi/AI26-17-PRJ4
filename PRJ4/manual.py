import pygame
import sys
from src.minesweeper import MineSweeper, CELL_SIZE

class ManualController:
    def __init__(self):
        self.game = None
        self.reset()
        self.clock = pygame.time.Clock()

    def reset(self):
        self.game = MineSweeper(rows=30, cols=50, mines=500, seed=42, auto_flood_fill=True)

    def run(self):
        print("Starting Manual Game...")
        print("Left Click: Reveal"
              "Right Click: Flag")
        
        while True:
            self._handle_input()
            self.game.render()
            self.clock.tick(30) # Cap FPS at 30

    def _handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # Input is blocked if game is over
            if not self.game.game_over and event.type == pygame.MOUSEBUTTONDOWN:
                x, y = pygame.mouse.get_pos()
                
                # Check if click is inside grid
                if y < (self.game.rows * CELL_SIZE):
                    c = x // CELL_SIZE
                    r = y // CELL_SIZE
                    
                    if event.button == 1:   # Left Click
                        self.game.reveal(r, c)
                    elif event.button == 3: # Right Click
                        if self.game.grid_visibility[r][c] == 0:
                            self.game.flag(r, c)
                        elif self.game.grid_visibility[r][c] == 2:
                            self.game.unflag(r, c)
                        else:
                            continue
            
            # Restart on click if Game Over
            elif self.game.game_over and event.type == pygame.MOUSEBUTTONDOWN:
                print("Restarting...")
                self.reset()

if __name__ == "__main__":
    controller = ManualController()
    controller.run()