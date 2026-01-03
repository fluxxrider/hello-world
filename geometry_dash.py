import pygame
import random
import sys

pygame.init()

# Screen settings
WIDTH = 800
HEIGHT = 400
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Geometry Dash Clone")
clock = pygame.time.Clock()

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
PINK = (255, 100, 150)
PURPLE = (150, 0, 255)
GROUND_COLOR = (0, 50, 255)
BG_COLOR = (0, 0, 50)

# Game settings
GROUND_HEIGHT = 50
GRAVITY = 0.8
JUMP_STRENGTH = -14
GAME_SPEED = 8

# Fonts
font_big = pygame.font.Font(None, 74)
font_small = pygame.font.Font(None, 36)

class Player:
    def __init__(self):
        self.size = 40
        self.x = 100
        self.y = HEIGHT - GROUND_HEIGHT - self.size
        self.vel_y = 0
        self.on_ground = True
        self.rotation = 0
        self.color = CYAN
        self.dead = False

    def jump(self):
        if self.on_ground and not self.dead:
            self.vel_y = JUMP_STRENGTH
            self.on_ground = False

    def update(self, platforms):
        if self.dead:
            return

        # Apply gravity
        self.vel_y += GRAVITY
        self.y += self.vel_y

        # Rotate while in air
        if not self.on_ground:
            self.rotation -= 5
        else:
            # Snap rotation to nearest 90 degrees
            self.rotation = round(self.rotation / 90) * 90

        # Check ground collision
        ground_y = HEIGHT - GROUND_HEIGHT - self.size
        if self.y >= ground_y:
            self.y = ground_y
            self.vel_y = 0
            self.on_ground = True

        # Check platform collisions
        player_rect = pygame.Rect(self.x, self.y, self.size, self.size)
        self.on_ground = self.y >= ground_y

        for plat in platforms:
            if plat.type == "platform":
                plat_rect = pygame.Rect(plat.x, plat.y, plat.width, plat.height)
                if player_rect.colliderect(plat_rect):
                    # Landing on top
                    if self.vel_y > 0 and self.y + self.size - self.vel_y <= plat.y:
                        self.y = plat.y - self.size
                        self.vel_y = 0
                        self.on_ground = True

    def draw(self, surface):
        # Draw rotated square
        points = []
        cx = self.x + self.size // 2
        cy = self.y + self.size // 2
        import math
        angle_rad = math.radians(self.rotation)
        for dx, dy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
            px = dx * self.size // 2
            py = dy * self.size // 2
            rotated_x = px * math.cos(angle_rad) - py * math.sin(angle_rad)
            rotated_y = px * math.sin(angle_rad) + py * math.cos(angle_rad)
            points.append((cx + rotated_x, cy + rotated_y))

        pygame.draw.polygon(surface, self.color, points)
        pygame.draw.polygon(surface, WHITE, points, 3)

        # Draw eye
        eye_x = cx + 8 * math.cos(angle_rad) - (-5) * math.sin(angle_rad)
        eye_y = cy + 8 * math.sin(angle_rad) + (-5) * math.cos(angle_rad)
        pygame.draw.circle(surface, WHITE, (int(eye_x), int(eye_y)), 6)
        pygame.draw.circle(surface, BLACK, (int(eye_x + 2), int(eye_y)), 3)

    def get_rect(self):
        # Smaller hitbox for fairness
        margin = 5
        return pygame.Rect(self.x + margin, self.y + margin,
                          self.size - margin * 2, self.size - margin * 2)

class Obstacle:
    def __init__(self, x, obs_type="spike", y=None, width=None, height=None):
        self.type = obs_type
        self.x = x

        if obs_type == "spike":
            self.width = 40
            self.height = 40
            self.y = HEIGHT - GROUND_HEIGHT - self.height
            self.color = random.choice([MAGENTA, ORANGE, PINK, PURPLE])
        elif obs_type == "platform":
            self.width = width or 100
            self.height = height or 20
            self.y = y or (HEIGHT - GROUND_HEIGHT - 80)
            self.color = PURPLE
        elif obs_type == "double_spike":
            self.width = 80
            self.height = 40
            self.y = HEIGHT - GROUND_HEIGHT - self.height
            self.color = random.choice([MAGENTA, ORANGE, PINK])
        elif obs_type == "tall_spike":
            self.width = 40
            self.height = 60
            self.y = HEIGHT - GROUND_HEIGHT - self.height
            self.color = random.choice([YELLOW, ORANGE])

    def update(self, speed):
        self.x -= speed

    def draw(self, surface):
        if self.type == "platform":
            pygame.draw.rect(surface, self.color, (self.x, self.y, self.width, self.height))
            pygame.draw.rect(surface, WHITE, (self.x, self.y, self.width, self.height), 2)
        elif self.type == "double_spike":
            # Draw two spikes
            for i in range(2):
                spike_x = self.x + i * 40
                points = [
                    (spike_x + 20, self.y),
                    (spike_x, self.y + self.height),
                    (spike_x + 40, self.y + self.height)
                ]
                pygame.draw.polygon(surface, self.color, points)
                pygame.draw.polygon(surface, WHITE, points, 2)
        else:
            # Draw triangle spike
            points = [
                (self.x + self.width // 2, self.y),
                (self.x, self.y + self.height),
                (self.x + self.width, self.y + self.height)
            ]
            pygame.draw.polygon(surface, self.color, points)
            pygame.draw.polygon(surface, WHITE, points, 2)

    def get_collision_rect(self):
        if "spike" in self.type:
            # Smaller hitbox for spikes (only the middle part)
            margin_x = self.width // 4
            margin_y = self.height // 3
            return pygame.Rect(self.x + margin_x, self.y + margin_y,
                             self.width - margin_x * 2, self.height - margin_y)
        return pygame.Rect(self.x, self.y, self.width, self.height)

class Game:
    def __init__(self):
        self.player = Player()
        self.obstacles = []
        self.score = 0
        self.best_score = 0
        self.game_over = False
        self.started = False
        self.speed = GAME_SPEED
        self.spawn_timer = 0
        self.bg_x = 0
        self.attempts = 1

        # Background decorations
        self.bg_blocks = []
        for i in range(20):
            self.bg_blocks.append({
                'x': random.randint(0, WIDTH),
                'y': random.randint(50, HEIGHT - GROUND_HEIGHT - 50),
                'size': random.randint(20, 60),
                'color': random.choice([(30, 30, 80), (40, 40, 100), (20, 20, 60)])
            })

    def spawn_obstacle(self):
        patterns = [
            # Single spike
            [("spike", 0)],
            # Double spike
            [("double_spike", 0)],
            # Triple spikes
            [("spike", 0), ("spike", 45), ("spike", 90)],
            # Platform with spike on top
            [("platform", 0, HEIGHT - GROUND_HEIGHT - 80, 100, 20),
             ("spike", 30, "on_platform")],
            # Gap jump
            [("spike", 0), ("spike", 150)],
            # Tall spike
            [("tall_spike", 0)],
        ]

        pattern = random.choice(patterns)
        base_x = WIDTH + 50

        for item in pattern:
            if item[0] == "platform":
                self.obstacles.append(Obstacle(base_x + item[1], "platform",
                                               item[2], item[3], item[4]))
            elif len(item) > 2 and item[2] == "on_platform":
                # Spike on platform
                self.obstacles.append(Obstacle(base_x + item[1], "spike"))
                self.obstacles[-1].y = HEIGHT - GROUND_HEIGHT - 80 - 40
            else:
                self.obstacles.append(Obstacle(base_x + item[1], item[0]))

    def update(self):
        if not self.started or self.game_over:
            return

        self.score += 1

        # Gradually increase speed
        self.speed = GAME_SPEED + (self.score // 500) * 0.5

        # Update background
        self.bg_x -= self.speed * 0.3
        if self.bg_x <= -100:
            self.bg_x = 0

        for block in self.bg_blocks:
            block['x'] -= self.speed * 0.2
            if block['x'] < -block['size']:
                block['x'] = WIDTH + block['size']
                block['y'] = random.randint(50, HEIGHT - GROUND_HEIGHT - 50)

        # Spawn obstacles
        self.spawn_timer += 1
        if self.spawn_timer >= random.randint(60, 120):
            self.spawn_obstacle()
            self.spawn_timer = 0

        # Update obstacles
        for obs in self.obstacles[:]:
            obs.update(self.speed)
            if obs.x + obs.width < 0:
                self.obstacles.remove(obs)

        # Update player
        platforms = [o for o in self.obstacles if o.type == "platform"]
        self.player.update(platforms)

        # Check collisions
        player_rect = self.player.get_rect()
        for obs in self.obstacles:
            if "spike" in obs.type:
                if player_rect.colliderect(obs.get_collision_rect()):
                    self.game_over = True
                    self.player.dead = True
                    if self.score > self.best_score:
                        self.best_score = self.score

    def draw(self):
        # Background
        screen.fill(BG_COLOR)

        # Background grid effect
        for x in range(int(self.bg_x) % 100 - 100, WIDTH + 100, 100):
            pygame.draw.line(screen, (30, 30, 70), (x, 0), (x, HEIGHT - GROUND_HEIGHT), 1)
        for y in range(0, HEIGHT - GROUND_HEIGHT, 50):
            pygame.draw.line(screen, (30, 30, 70), (0, y), (WIDTH, y), 1)

        # Background blocks
        for block in self.bg_blocks:
            pygame.draw.rect(screen, block['color'],
                           (block['x'], block['y'], block['size'], block['size']))

        # Draw obstacles
        for obs in self.obstacles:
            obs.draw(screen)

        # Draw player
        self.player.draw(screen)

        # Ground
        pygame.draw.rect(screen, GROUND_COLOR, (0, HEIGHT - GROUND_HEIGHT, WIDTH, GROUND_HEIGHT))
        pygame.draw.rect(screen, WHITE, (0, HEIGHT - GROUND_HEIGHT, WIDTH, 3))

        # Ground pattern
        for x in range(int(self.bg_x) % 50 - 50, WIDTH + 50, 50):
            pygame.draw.line(screen, (0, 70, 255),
                           (x, HEIGHT - GROUND_HEIGHT + 10),
                           (x + 30, HEIGHT - 10), 2)

        # UI
        score_text = font_small.render(f"Score: {self.score}", True, WHITE)
        screen.blit(score_text, (10, 10))

        best_text = font_small.render(f"Best: {self.best_score}", True, YELLOW)
        screen.blit(best_text, (10, 45))

        attempt_text = font_small.render(f"Attempt {self.attempts}", True, WHITE)
        screen.blit(attempt_text, (WIDTH - 150, 10))

        # Start screen
        if not self.started:
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(150)
            overlay.fill(BLACK)
            screen.blit(overlay, (0, 0))

            title = font_big.render("GEOMETRY DASH", True, CYAN)
            screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 80))

            start_text = font_small.render("Press SPACE or CLICK to start!", True, WHITE)
            screen.blit(start_text, (WIDTH // 2 - start_text.get_width() // 2, HEIGHT // 2))

            controls = font_small.render("SPACE / CLICK / UP = Jump", True, YELLOW)
            screen.blit(controls, (WIDTH // 2 - controls.get_width() // 2, HEIGHT // 2 + 50))

        # Game over screen
        if self.game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(180)
            overlay.fill(BLACK)
            screen.blit(overlay, (0, 0))

            dead_text = font_big.render("YOU CRASHED!", True, MAGENTA)
            screen.blit(dead_text, (WIDTH // 2 - dead_text.get_width() // 2, HEIGHT // 2 - 60))

            score_text = font_small.render(f"Score: {self.score}", True, WHITE)
            screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, HEIGHT // 2))

            if self.score >= self.best_score and self.score > 0:
                new_best = font_small.render("NEW BEST!", True, YELLOW)
                screen.blit(new_best, (WIDTH // 2 - new_best.get_width() // 2, HEIGHT // 2 + 35))

            restart_text = font_small.render("Press SPACE to retry", True, WHITE)
            screen.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT // 2 + 70))

        pygame.display.flip()

    def restart(self):
        self.player = Player()
        self.obstacles = []
        self.score = 0
        self.game_over = False
        self.speed = GAME_SPEED
        self.spawn_timer = 0
        self.attempts += 1

    def handle_input(self, event):
        if event.type == pygame.QUIT:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return False
            if event.key in [pygame.K_SPACE, pygame.K_UP, pygame.K_w]:
                if not self.started:
                    self.started = True
                elif self.game_over:
                    self.restart()
                else:
                    self.player.jump()

        if event.type == pygame.MOUSEBUTTONDOWN:
            if not self.started:
                self.started = True
            elif self.game_over:
                self.restart()
            else:
                self.player.jump()

        return True

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                running = self.handle_input(event)

            # Hold space for continuous jumping
            keys = pygame.key.get_pressed()
            if keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]:
                if self.started and not self.game_over:
                    self.player.jump()

            self.update()
            self.draw()
            clock.tick(60)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()
