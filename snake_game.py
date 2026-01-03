#!/usr/bin/env python3
"""A classic Snake game implemented in Python using curses."""

import curses
import random
import time


def main(stdscr):
    # Setup
    curses.curs_set(0)  # Hide cursor
    stdscr.nodelay(1)   # Non-blocking input
    stdscr.timeout(100) # Refresh rate in ms

    # Get screen dimensions
    sh, sw = stdscr.getmaxyx()

    # Create game window
    win = curses.newwin(sh, sw, 0, 0)
    win.keypad(1)
    win.timeout(100)

    # Initial snake position (middle of screen)
    snake_x = sw // 4
    snake_y = sh // 2

    # Snake body (list of [y, x] positions)
    snake = [
        [snake_y, snake_x],
        [snake_y, snake_x - 1],
        [snake_y, snake_x - 2]
    ]

    # Initial food position
    food = [sh // 2, sw // 2]
    win.addch(food[0], food[1], '*')

    # Initial direction (moving right)
    key = curses.KEY_RIGHT

    # Score
    score = 0

    # Game speed (lower = faster)
    speed = 100

    while True:
        # Display score
        win.addstr(0, 2, f' Score: {score} ')
        win.addstr(0, sw - 20, ' Press Q to quit ')

        # Get next key (non-blocking)
        next_key = win.getch()

        # Update direction if valid key pressed
        if next_key != -1:
            if next_key in [curses.KEY_UP, curses.KEY_DOWN,
                           curses.KEY_LEFT, curses.KEY_RIGHT]:
                # Prevent reversing direction
                if (next_key == curses.KEY_UP and key != curses.KEY_DOWN) or \
                   (next_key == curses.KEY_DOWN and key != curses.KEY_UP) or \
                   (next_key == curses.KEY_LEFT and key != curses.KEY_RIGHT) or \
                   (next_key == curses.KEY_RIGHT and key != curses.KEY_LEFT):
                    key = next_key
            elif next_key in [ord('q'), ord('Q')]:
                break

        # Calculate new head position
        head = snake[0].copy()

        if key == curses.KEY_UP:
            head[0] -= 1
        elif key == curses.KEY_DOWN:
            head[0] += 1
        elif key == curses.KEY_LEFT:
            head[1] -= 1
        elif key == curses.KEY_RIGHT:
            head[1] += 1

        # Check for collision with walls
        if head[0] <= 0 or head[0] >= sh - 1 or head[1] <= 0 or head[1] >= sw - 1:
            break

        # Check for collision with self
        if head in snake:
            break

        # Insert new head
        snake.insert(0, head)

        # Check if snake ate food
        if head == food:
            score += 10

            # Increase speed slightly
            if speed > 50:
                speed -= 2
                win.timeout(speed)

            # Generate new food position
            while True:
                food = [
                    random.randint(2, sh - 2),
                    random.randint(2, sw - 2)
                ]
                if food not in snake:
                    break

            win.addch(food[0], food[1], '*')
        else:
            # Remove tail if no food eaten
            tail = snake.pop()
            win.addch(tail[0], tail[1], ' ')

        # Draw snake head
        win.addch(snake[0][0], snake[0][1], '#')

        # Draw snake body
        for segment in snake[1:]:
            win.addch(segment[0], segment[1], 'o')

    # Game over screen
    win.clear()
    game_over_msg = f"GAME OVER! Final Score: {score}"
    win.addstr(sh // 2, (sw - len(game_over_msg)) // 2, game_over_msg)
    win.addstr(sh // 2 + 2, (sw - 22) // 2, "Press any key to exit")
    win.timeout(-1)  # Wait for key
    win.getch()


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    print("Thanks for playing Snake!")
