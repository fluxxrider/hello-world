#!/usr/bin/env python3
"""A classic Snake game implemented in Python using Pygame."""

import pygame
import random
import sys

# Initialize Pygame
pygame.init()

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
DARK_GREEN = (0, 200, 0)

# Game settings
CELL_SIZE = 20
GRID_WIDTH = 30
GRID_HEIGHT = 20
SCREEN_WIDTH = CELL_SIZE * GRID_WIDTH
SCREEN_HEIGHT = CELL_SIZE * GRID_HEIGHT

# Directions
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)


class SnakeGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Snake Game - Use Arrow Keys, Q to Quit")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.reset_game()

    def reset_game(self):
        # Snake starts in the middle
        start_x = GRID_WIDTH // 4
        start_y = GRID_HEIGHT // 2
        self.snake = [
            (start_x, start_y),
            (start_x - 1, start_y),
            (start_x - 2, start_y)
        ]
        self.direction = RIGHT
        self.next_direction = RIGHT
        self.spawn_food()
        self.score = 0
        self.game_over = False
        self.speed = 10  # FPS

    def spawn_food(self):
        while True:
            self.food = (
                random.randint(0, GRID_WIDTH - 1),
                random.randint(0, GRID_HEIGHT - 1)
            )
            if self.food not in self.snake:
                break

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    return False
                if event.key == pygame.K_r and self.game_over:
                    self.reset_game()
                # Prevent reversing direction
                if event.key == pygame.K_UP and self.direction != DOWN:
                    self.next_direction = UP
                elif event.key == pygame.K_DOWN and self.direction != UP:
                    self.next_direction = DOWN
                elif event.key == pygame.K_LEFT and self.direction != RIGHT:
                    self.next_direction = LEFT
                elif event.key == pygame.K_RIGHT and self.direction != LEFT:
                    self.next_direction = RIGHT
        return True

    def update(self):
        if self.game_over:
            return

        self.direction = self.next_direction

        # Calculate new head position
        head_x, head_y = self.snake[0]
        new_head = (head_x + self.direction[0], head_y + self.direction[1])

        # Check for collision with walls
        if (new_head[0] < 0 or new_head[0] >= GRID_WIDTH or
            new_head[1] < 0 or new_head[1] >= GRID_HEIGHT):
            self.game_over = True
            return

        # Check for collision with self
        if new_head in self.snake:
            self.game_over = True
            return

        # Add new head
        self.snake.insert(0, new_head)

        # Check if snake ate food
        if new_head == self.food:
            self.score += 10
            self.spawn_food()
            # Increase speed
            if self.speed < 20:
                self.speed += 0.5
        else:
            # Remove tail if no food eaten
            self.snake.pop()

    def draw(self):
        self.screen.fill(BLACK)

        # Draw grid (optional, subtle lines)
        for x in range(0, SCREEN_WIDTH, CELL_SIZE):
            pygame.draw.line(self.screen, (30, 30, 30), (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, CELL_SIZE):
            pygame.draw.line(self.screen, (30, 30, 30), (0, y), (SCREEN_WIDTH, y))

        # Draw food
        food_rect = pygame.Rect(
            self.food[0] * CELL_SIZE,
            self.food[1] * CELL_SIZE,
            CELL_SIZE,
            CELL_SIZE
        )
        pygame.draw.rect(self.screen, RED, food_rect)

        # Draw snake
        for i, segment in enumerate(self.snake):
            rect = pygame.Rect(
                segment[0] * CELL_SIZE,
                segment[1] * CELL_SIZE,
                CELL_SIZE,
                CELL_SIZE
            )
            color = GREEN if i == 0 else DARK_GREEN
            pygame.draw.rect(self.screen, color, rect)
            # Add border to segments
            pygame.draw.rect(self.screen, BLACK, rect, 1)

        # Draw score
        score_text = self.font.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, (10, 10))

        # Draw game over message
        if self.game_over:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(180)
            overlay.fill(BLACK)
            self.screen.blit(overlay, (0, 0))

            game_over_text = self.font.render("GAME OVER!", True, RED)
            score_text = self.font.render(f"Final Score: {self.score}", True, WHITE)
            restart_text = self.font.render("Press R to Restart or Q to Quit", True, WHITE)

            self.screen.blit(game_over_text,
                (SCREEN_WIDTH // 2 - game_over_text.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
            self.screen.blit(score_text,
                (SCREEN_WIDTH // 2 - score_text.get_width() // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(restart_text,
                (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, SCREEN_HEIGHT // 2 + 50))

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(self.speed)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = SnakeGame()
    game.run()
