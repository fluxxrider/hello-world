import pygame
import math
import random
import sys

pygame.init()

# Screen settings
WIDTH = 1000
HEIGHT = 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Angry Birds Clone")
clock = pygame.time.Clock()

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 50, 50)
YELLOW = (255, 220, 50)
BLUE = (100, 150, 255)
GREEN = (100, 200, 100)
BROWN = (139, 90, 43)
DARK_BROWN = (101, 67, 33)
LIGHT_BROWN = (205, 170, 125)
SKY_BLUE = (135, 206, 235)
GRASS_GREEN = (34, 139, 34)
WOOD_COLOR = (160, 82, 45)
STONE_COLOR = (128, 128, 128)
ICE_COLOR = (173, 216, 230)
PIG_GREEN = (124, 185, 71)
DARK_GREEN = (50, 120, 50)
SLINGSHOT_COLOR = (101, 67, 33)
ORANGE = (255, 165, 0)

# Physics
GRAVITY = 0.25
FRICTION = 0.98
BOUNCE_DAMPING = 0.6
MIN_VELOCITY = 0.5

# Fonts
font_big = pygame.font.Font(None, 74)
font_medium = pygame.font.Font(None, 48)
font_small = pygame.font.Font(None, 32)

class Bird:
    def __init__(self, x, y, bird_type="red"):
        self.start_x = x
        self.start_y = y
        self.x = x
        self.y = y
        self.radius = 20
        self.vel_x = 0
        self.vel_y = 0
        self.launched = False
        self.active = True
        self.bird_type = bird_type
        self.ability_used = False
        self.trail = []

        if bird_type == "red":
            self.color = RED
            self.radius = 20
        elif bird_type == "yellow":
            self.color = YELLOW
            self.radius = 18
        elif bird_type == "blue":
            self.color = BLUE
            self.radius = 15

    def launch(self, vel_x, vel_y):
        self.vel_x = vel_x
        self.vel_y = vel_y
        self.launched = True

    def use_ability(self):
        if self.ability_used or not self.launched:
            return []

        self.ability_used = True
        new_birds = []

        if self.bird_type == "yellow":
            # Speed boost
            self.vel_x *= 1.8
            self.vel_y *= 0.5
        elif self.bird_type == "blue":
            # Split into 3 birds
            for angle_offset in [-20, 0, 20]:
                angle = math.atan2(self.vel_y, self.vel_x) + math.radians(angle_offset)
                speed = math.sqrt(self.vel_x**2 + self.vel_y**2)
                new_bird = Bird(self.x, self.y, "blue")
                new_bird.radius = 12
                new_bird.vel_x = math.cos(angle) * speed
                new_bird.vel_y = math.sin(angle) * speed
                new_bird.launched = True
                new_bird.ability_used = True
                new_birds.append(new_bird)

        return new_birds

    def update(self):
        if not self.launched or not self.active:
            return

        # Store trail position
        if len(self.trail) > 30:
            self.trail.pop(0)
        self.trail.append((int(self.x), int(self.y)))

        # Apply gravity
        self.vel_y += GRAVITY

        # Apply velocity
        self.x += self.vel_x
        self.y += self.vel_y

        # Ground collision
        ground_y = HEIGHT - 60
        if self.y + self.radius > ground_y:
            self.y = ground_y - self.radius
            self.vel_y = -self.vel_y * BOUNCE_DAMPING
            self.vel_x *= FRICTION

        # Wall collisions
        if self.x - self.radius < 0:
            self.x = self.radius
            self.vel_x = -self.vel_x * BOUNCE_DAMPING
        if self.x + self.radius > WIDTH:
            self.x = WIDTH - self.radius
            self.vel_x = -self.vel_x * BOUNCE_DAMPING

        # Deactivate if moving too slowly
        if self.launched and abs(self.vel_x) < MIN_VELOCITY and abs(self.vel_y) < MIN_VELOCITY and self.y >= ground_y - self.radius - 5:
            self.active = False

    def draw(self, surface):
        # Draw trail
        for i, pos in enumerate(self.trail):
            alpha = int(255 * (i / len(self.trail)) * 0.3)
            size = int(self.radius * (i / len(self.trail)) * 0.5)
            if size > 2:
                trail_surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(trail_surface, (*self.color, alpha), (size, size), size)
                surface.blit(trail_surface, (pos[0] - size, pos[1] - size))

        # Draw bird body
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, BLACK, (int(self.x), int(self.y)), self.radius, 2)

        # Draw eyes
        eye_offset_x = 5
        eye_offset_y = -5
        pygame.draw.circle(surface, WHITE, (int(self.x + eye_offset_x - 4), int(self.y + eye_offset_y)), 6)
        pygame.draw.circle(surface, WHITE, (int(self.x + eye_offset_x + 4), int(self.y + eye_offset_y)), 6)
        pygame.draw.circle(surface, BLACK, (int(self.x + eye_offset_x - 3), int(self.y + eye_offset_y)), 3)
        pygame.draw.circle(surface, BLACK, (int(self.x + eye_offset_x + 5), int(self.y + eye_offset_y)), 3)

        # Draw eyebrows (angry!)
        pygame.draw.line(surface, BLACK,
                        (int(self.x + eye_offset_x - 10), int(self.y + eye_offset_y - 8)),
                        (int(self.x + eye_offset_x - 2), int(self.y + eye_offset_y - 5)), 3)
        pygame.draw.line(surface, BLACK,
                        (int(self.x + eye_offset_x + 10), int(self.y + eye_offset_y - 8)),
                        (int(self.x + eye_offset_x + 2), int(self.y + eye_offset_y - 5)), 3)

        # Draw beak
        beak_points = [
            (int(self.x + self.radius - 2), int(self.y + 2)),
            (int(self.x + self.radius + 10), int(self.y + 5)),
            (int(self.x + self.radius - 2), int(self.y + 8))
        ]
        pygame.draw.polygon(surface, ORANGE, beak_points)
        pygame.draw.polygon(surface, DARK_BROWN, beak_points, 1)

class Block:
    def __init__(self, x, y, width, height, block_type="wood"):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.block_type = block_type
        self.vel_x = 0
        self.vel_y = 0
        self.health = self.get_max_health()
        self.destroyed = False
        self.rotation = 0

        if block_type == "wood":
            self.color = WOOD_COLOR
            self.max_health = 50
        elif block_type == "stone":
            self.color = STONE_COLOR
            self.max_health = 100
        elif block_type == "ice":
            self.color = ICE_COLOR
            self.max_health = 30

    def get_max_health(self):
        if self.block_type == "wood":
            return 50
        elif self.block_type == "stone":
            return 100
        elif self.block_type == "ice":
            return 30
        return 50

    def damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.destroyed = True
            return True
        return False

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def update(self):
        if self.destroyed:
            return

        # Apply gravity
        self.vel_y += GRAVITY * 0.5

        # Apply velocity
        self.x += self.vel_x
        self.y += self.vel_y

        # Apply friction
        self.vel_x *= FRICTION

        # Ground collision
        ground_y = HEIGHT - 60
        if self.y + self.height > ground_y:
            self.y = ground_y - self.height
            self.vel_y = -self.vel_y * 0.3
            self.vel_x *= 0.8
            if abs(self.vel_y) < 0.5:
                self.vel_y = 0

    def draw(self, surface):
        if self.destroyed:
            return

        # Draw block
        pygame.draw.rect(surface, self.color, (int(self.x), int(self.y), self.width, self.height))

        # Draw damage cracks based on health percentage
        health_pct = self.health / self.get_max_health()
        if health_pct < 0.7:
            # Light damage
            pygame.draw.line(surface, BLACK,
                           (int(self.x + self.width * 0.3), int(self.y)),
                           (int(self.x + self.width * 0.5), int(self.y + self.height * 0.4)), 2)
        if health_pct < 0.4:
            # Heavy damage
            pygame.draw.line(surface, BLACK,
                           (int(self.x + self.width * 0.6), int(self.y + self.height)),
                           (int(self.x + self.width * 0.8), int(self.y + self.height * 0.5)), 2)

        # Draw outline
        border_color = DARK_BROWN if self.block_type == "wood" else BLACK
        pygame.draw.rect(surface, border_color, (int(self.x), int(self.y), self.width, self.height), 2)

        # Wood grain for wood blocks
        if self.block_type == "wood":
            for i in range(3):
                y_pos = self.y + self.height * (0.25 + i * 0.25)
                pygame.draw.line(surface, DARK_BROWN,
                               (int(self.x + 2), int(y_pos)),
                               (int(self.x + self.width - 2), int(y_pos)), 1)

class Pig:
    def __init__(self, x, y, size="medium"):
        self.x = x
        self.y = y
        self.size = size
        self.vel_x = 0
        self.vel_y = 0
        self.destroyed = False

        if size == "small":
            self.radius = 18
            self.health = 30
            self.points = 500
        elif size == "medium":
            self.radius = 25
            self.health = 50
            self.points = 1000
        elif size == "large":
            self.radius = 35
            self.health = 80
            self.points = 2000

        self.max_health = self.health

    def damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.destroyed = True
            return self.points
        return 0

    def get_rect(self):
        return pygame.Rect(self.x - self.radius, self.y - self.radius,
                          self.radius * 2, self.radius * 2)

    def update(self):
        if self.destroyed:
            return

        # Apply gravity
        self.vel_y += GRAVITY * 0.5

        # Apply velocity
        self.x += self.vel_x
        self.y += self.vel_y

        # Apply friction
        self.vel_x *= FRICTION

        # Ground collision
        ground_y = HEIGHT - 60
        if self.y + self.radius > ground_y:
            self.y = ground_y - self.radius
            self.vel_y = -self.vel_y * 0.3
            self.vel_x *= 0.8
            if abs(self.vel_y) < 0.5:
                self.vel_y = 0

    def draw(self, surface):
        if self.destroyed:
            return

        # Draw pig body
        pygame.draw.circle(surface, PIG_GREEN, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, DARK_GREEN, (int(self.x), int(self.y)), self.radius, 2)

        # Draw ears
        ear_offset = self.radius - 5
        pygame.draw.circle(surface, PIG_GREEN, (int(self.x - ear_offset), int(self.y - ear_offset)), 8)
        pygame.draw.circle(surface, PIG_GREEN, (int(self.x + ear_offset), int(self.y - ear_offset)), 8)
        pygame.draw.circle(surface, DARK_GREEN, (int(self.x - ear_offset), int(self.y - ear_offset)), 8, 2)
        pygame.draw.circle(surface, DARK_GREEN, (int(self.x + ear_offset), int(self.y - ear_offset)), 8, 2)

        # Draw snout
        snout_width = self.radius * 0.6
        snout_height = self.radius * 0.4
        pygame.draw.ellipse(surface, (144, 205, 91),
                           (int(self.x - snout_width/2), int(self.y + 2),
                            int(snout_width), int(snout_height)))
        pygame.draw.ellipse(surface, DARK_GREEN,
                           (int(self.x - snout_width/2), int(self.y + 2),
                            int(snout_width), int(snout_height)), 2)

        # Nostrils
        pygame.draw.circle(surface, DARK_GREEN, (int(self.x - 4), int(self.y + 8)), 3)
        pygame.draw.circle(surface, DARK_GREEN, (int(self.x + 4), int(self.y + 8)), 3)

        # Eyes - change based on health
        health_pct = self.health / self.max_health
        eye_y = self.y - 5

        # White of eyes
        pygame.draw.circle(surface, WHITE, (int(self.x - 8), int(eye_y)), 7)
        pygame.draw.circle(surface, WHITE, (int(self.x + 8), int(eye_y)), 7)

        if health_pct > 0.5:
            # Normal eyes
            pygame.draw.circle(surface, BLACK, (int(self.x - 7), int(eye_y)), 4)
            pygame.draw.circle(surface, BLACK, (int(self.x + 9), int(eye_y)), 4)
        else:
            # Worried eyes (X eyes when damaged)
            pygame.draw.line(surface, BLACK, (int(self.x - 11), int(eye_y - 3)),
                           (int(self.x - 5), int(eye_y + 3)), 2)
            pygame.draw.line(surface, BLACK, (int(self.x - 11), int(eye_y + 3)),
                           (int(self.x - 5), int(eye_y - 3)), 2)
            pygame.draw.line(surface, BLACK, (int(self.x + 5), int(eye_y - 3)),
                           (int(self.x + 11), int(eye_y + 3)), 2)
            pygame.draw.line(surface, BLACK, (int(self.x + 5), int(eye_y + 3)),
                           (int(self.x + 11), int(eye_y - 3)), 2)

        # Eyebrows
        if health_pct < 0.5:
            pygame.draw.line(surface, DARK_GREEN,
                           (int(self.x - 12), int(eye_y - 8)),
                           (int(self.x - 4), int(eye_y - 10)), 2)
            pygame.draw.line(surface, DARK_GREEN,
                           (int(self.x + 12), int(eye_y - 8)),
                           (int(self.x + 4), int(eye_y - 10)), 2)

class Slingshot:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 20
        self.height = 100
        self.band_left = (x - 15, y - 60)
        self.band_right = (x + 15, y - 60)
        self.anchor = (x, y - 50)

    def draw(self, surface, bird=None, pull_pos=None):
        # Draw back band if pulling
        if bird and pull_pos and not bird.launched:
            pygame.draw.line(surface, DARK_BROWN, self.band_left, pull_pos, 6)

        # Draw slingshot frame (Y shape)
        # Left arm
        pygame.draw.line(surface, SLINGSHOT_COLOR,
                        (self.x - 5, self.y),
                        (self.x - 20, self.y - 70), 12)
        # Right arm
        pygame.draw.line(surface, SLINGSHOT_COLOR,
                        (self.x + 5, self.y),
                        (self.x + 20, self.y - 70), 12)
        # Base
        pygame.draw.line(surface, SLINGSHOT_COLOR,
                        (self.x, self.y),
                        (self.x, self.y + 30), 14)

        # Draw front band if pulling
        if bird and pull_pos and not bird.launched:
            pygame.draw.line(surface, DARK_BROWN, self.band_right, pull_pos, 6)
        elif not bird or not bird.launched:
            # Draw resting band
            pygame.draw.line(surface, DARK_BROWN, self.band_left, self.anchor, 4)
            pygame.draw.line(surface, DARK_BROWN, self.band_right, self.anchor, 4)

class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.vel_x = random.uniform(-3, 3)
        self.vel_y = random.uniform(-5, -1)
        self.color = color
        self.life = 60
        self.size = random.randint(3, 8)

    def update(self):
        self.vel_y += 0.15
        self.x += self.vel_x
        self.y += self.vel_y
        self.life -= 1
        return self.life > 0

    def draw(self, surface):
        alpha = int(255 * (self.life / 60))
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.rect(s, (*self.color, alpha), (0, 0, self.size, self.size))
        surface.blit(s, (int(self.x), int(self.y)))

class Game:
    def __init__(self):
        self.slingshot = Slingshot(150, HEIGHT - 120)
        self.reset_game()
        self.level = 1
        self.max_level = 3
        self.total_score = 0

    def reset_game(self):
        self.birds = []
        self.current_bird_index = 0
        self.blocks = []
        self.pigs = []
        self.particles = []
        self.score = 0
        self.game_state = "aiming"  # aiming, flying, ended, won, level_complete
        self.dragging = False
        self.drag_pos = None
        self.load_level(getattr(self, 'level', 1))

    def load_level(self, level):
        self.birds = []
        self.blocks = []
        self.pigs = []

        if level == 1:
            # Level 1: Simple introduction
            self.birds = [
                Bird(self.slingshot.x, self.slingshot.y - 50, "red"),
                Bird(self.slingshot.x, self.slingshot.y - 50, "red"),
                Bird(self.slingshot.x, self.slingshot.y - 50, "red"),
            ]

            # Simple tower
            base_x = 650
            ground_y = HEIGHT - 60

            # Foundation
            self.blocks.append(Block(base_x, ground_y - 30, 80, 30, "wood"))
            self.blocks.append(Block(base_x + 100, ground_y - 30, 80, 30, "wood"))

            # Pillars
            self.blocks.append(Block(base_x + 10, ground_y - 100, 20, 70, "wood"))
            self.blocks.append(Block(base_x + 50, ground_y - 100, 20, 70, "wood"))
            self.blocks.append(Block(base_x + 110, ground_y - 100, 20, 70, "wood"))
            self.blocks.append(Block(base_x + 150, ground_y - 100, 20, 70, "wood"))

            # Roof
            self.blocks.append(Block(base_x, ground_y - 120, 180, 20, "wood"))

            # Pigs
            self.pigs.append(Pig(base_x + 40, ground_y - 50, "medium"))
            self.pigs.append(Pig(base_x + 130, ground_y - 50, "medium"))

        elif level == 2:
            # Level 2: Mixed materials
            self.birds = [
                Bird(self.slingshot.x, self.slingshot.y - 50, "red"),
                Bird(self.slingshot.x, self.slingshot.y - 50, "yellow"),
                Bird(self.slingshot.x, self.slingshot.y - 50, "red"),
                Bird(self.slingshot.x, self.slingshot.y - 50, "blue"),
            ]

            base_x = 600
            ground_y = HEIGHT - 60

            # Stone foundation
            self.blocks.append(Block(base_x, ground_y - 30, 100, 30, "stone"))
            self.blocks.append(Block(base_x + 120, ground_y - 30, 100, 30, "stone"))

            # Ice middle section
            self.blocks.append(Block(base_x + 20, ground_y - 80, 60, 50, "ice"))
            self.blocks.append(Block(base_x + 140, ground_y - 80, 60, 50, "ice"))

            # Wood top
            self.blocks.append(Block(base_x, ground_y - 100, 220, 20, "wood"))
            self.blocks.append(Block(base_x + 60, ground_y - 170, 20, 70, "wood"))
            self.blocks.append(Block(base_x + 140, ground_y - 170, 20, 70, "wood"))
            self.blocks.append(Block(base_x + 40, ground_y - 190, 140, 20, "wood"))

            # Pigs
            self.pigs.append(Pig(base_x + 50, ground_y - 50, "small"))
            self.pigs.append(Pig(base_x + 170, ground_y - 50, "small"))
            self.pigs.append(Pig(base_x + 110, ground_y - 130, "large"))

        elif level == 3:
            # Level 3: Fortress
            self.birds = [
                Bird(self.slingshot.x, self.slingshot.y - 50, "red"),
                Bird(self.slingshot.x, self.slingshot.y - 50, "yellow"),
                Bird(self.slingshot.x, self.slingshot.y - 50, "blue"),
                Bird(self.slingshot.x, self.slingshot.y - 50, "red"),
                Bird(self.slingshot.x, self.slingshot.y - 50, "yellow"),
            ]

            base_x = 550
            ground_y = HEIGHT - 60

            # Stone fortress walls
            for i in range(4):
                self.blocks.append(Block(base_x + i * 80, ground_y - 40, 70, 40, "stone"))

            # Pillars
            for i in range(5):
                self.blocks.append(Block(base_x + i * 80, ground_y - 120, 20, 80, "stone"))

            # Ice decorations
            self.blocks.append(Block(base_x + 30, ground_y - 120, 40, 30, "ice"))
            self.blocks.append(Block(base_x + 110, ground_y - 120, 40, 30, "ice"))
            self.blocks.append(Block(base_x + 190, ground_y - 120, 40, 30, "ice"))
            self.blocks.append(Block(base_x + 270, ground_y - 120, 40, 30, "ice"))

            # Roof
            self.blocks.append(Block(base_x, ground_y - 140, 320, 20, "wood"))

            # Top structure
            self.blocks.append(Block(base_x + 100, ground_y - 200, 20, 60, "wood"))
            self.blocks.append(Block(base_x + 200, ground_y - 200, 20, 60, "wood"))
            self.blocks.append(Block(base_x + 80, ground_y - 220, 160, 20, "wood"))

            # Pigs
            self.pigs.append(Pig(base_x + 50, ground_y - 70, "small"))
            self.pigs.append(Pig(base_x + 130, ground_y - 70, "medium"))
            self.pigs.append(Pig(base_x + 210, ground_y - 70, "medium"))
            self.pigs.append(Pig(base_x + 290, ground_y - 70, "small"))
            self.pigs.append(Pig(base_x + 160, ground_y - 170, "large"))

        self.current_bird_index = 0
        self.game_state = "aiming"

    def get_current_bird(self):
        if self.current_bird_index < len(self.birds):
            return self.birds[self.current_bird_index]
        return None

    def next_bird(self):
        self.current_bird_index += 1
        if self.current_bird_index >= len(self.birds):
            if len([p for p in self.pigs if not p.destroyed]) > 0:
                self.game_state = "ended"
            else:
                self.level_complete()
        else:
            self.game_state = "aiming"

    def level_complete(self):
        # Bonus points for remaining birds
        remaining_birds = len(self.birds) - self.current_bird_index - 1
        self.score += remaining_birds * 1000
        self.total_score += self.score

        if self.level < self.max_level:
            self.game_state = "level_complete"
        else:
            self.game_state = "won"

    def check_collisions(self, bird):
        if not bird.active or not bird.launched:
            return

        bird_rect = pygame.Rect(bird.x - bird.radius, bird.y - bird.radius,
                               bird.radius * 2, bird.radius * 2)

        # Check block collisions
        for block in self.blocks:
            if block.destroyed:
                continue

            block_rect = block.get_rect()
            if bird_rect.colliderect(block_rect):
                # Calculate impact force
                speed = math.sqrt(bird.vel_x ** 2 + bird.vel_y ** 2)
                impact = speed * 5

                # Damage block
                if block.damage(impact):
                    self.score += 50
                    # Create particles
                    for _ in range(10):
                        self.particles.append(Particle(block.x + block.width/2,
                                                       block.y + block.height/2,
                                                       block.color))

                # Apply force to block
                block.vel_x += bird.vel_x * 0.3
                block.vel_y += bird.vel_y * 0.3

                # Bounce bird
                bird.vel_x *= -0.5
                bird.vel_y *= -0.5

        # Check pig collisions
        for pig in self.pigs:
            if pig.destroyed:
                continue

            pig_rect = pig.get_rect()
            if bird_rect.colliderect(pig_rect):
                speed = math.sqrt(bird.vel_x ** 2 + bird.vel_y ** 2)
                impact = speed * 8

                points = pig.damage(impact)
                if points > 0:
                    self.score += points
                    for _ in range(15):
                        self.particles.append(Particle(pig.x, pig.y, PIG_GREEN))

                pig.vel_x += bird.vel_x * 0.5
                pig.vel_y += bird.vel_y * 0.5

                bird.vel_x *= 0.5
                bird.vel_y *= 0.5

        # Check block-to-pig collisions
        for block in self.blocks:
            if block.destroyed:
                continue

            block_rect = block.get_rect()
            block_speed = math.sqrt(block.vel_x ** 2 + block.vel_y ** 2)

            if block_speed > 2:
                for pig in self.pigs:
                    if pig.destroyed:
                        continue

                    pig_rect = pig.get_rect()
                    if block_rect.colliderect(pig_rect):
                        impact = block_speed * 10
                        points = pig.damage(impact)
                        if points > 0:
                            self.score += points
                            for _ in range(15):
                                self.particles.append(Particle(pig.x, pig.y, PIG_GREEN))

    def update(self):
        # Update particles
        self.particles = [p for p in self.particles if p.update()]

        # Update blocks
        for block in self.blocks:
            block.update()

        # Update pigs
        for pig in self.pigs:
            pig.update()

        # Update birds
        for bird in self.birds:
            bird.update()
            self.check_collisions(bird)

        # Check if current bird is done
        current_bird = self.get_current_bird()
        if current_bird and current_bird.launched and not current_bird.active:
            self.game_state = "waiting"

        # Check win condition
        if len([p for p in self.pigs if not p.destroyed]) == 0 and self.game_state not in ["level_complete", "won"]:
            self.level_complete()

    def handle_event(self, event):
        current_bird = self.get_current_bird()

        if event.type == pygame.QUIT:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return False
            if event.key == pygame.K_r:
                self.score = 0
                self.reset_game()
            if event.key == pygame.K_SPACE:
                if self.game_state == "flying" and current_bird:
                    new_birds = current_bird.use_ability()
                    for b in new_birds:
                        self.birds.insert(self.current_bird_index + 1, b)
                elif self.game_state == "waiting":
                    self.next_bird()
                elif self.game_state == "level_complete":
                    self.level += 1
                    self.score = 0
                    self.reset_game()
                elif self.game_state == "ended":
                    self.score = 0
                    self.reset_game()
                elif self.game_state == "won":
                    self.level = 1
                    self.total_score = 0
                    self.score = 0
                    self.reset_game()

        if self.game_state == "aiming" and current_bird:
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                dist = math.sqrt((mx - current_bird.x)**2 + (my - current_bird.y)**2)
                if dist < 50:
                    self.dragging = True

            if event.type == pygame.MOUSEMOTION and self.dragging:
                mx, my = pygame.mouse.get_pos()
                # Limit pull distance
                dx = mx - self.slingshot.x
                dy = my - (self.slingshot.y - 50)
                dist = math.sqrt(dx**2 + dy**2)
                max_dist = 100
                if dist > max_dist:
                    dx = dx / dist * max_dist
                    dy = dy / dist * max_dist

                # Only allow pulling backwards
                if dx < 0:
                    current_bird.x = self.slingshot.x + dx
                    current_bird.y = self.slingshot.y - 50 + dy
                    self.drag_pos = (int(current_bird.x), int(current_bird.y))

            if event.type == pygame.MOUSEBUTTONUP and self.dragging:
                self.dragging = False
                # Calculate launch velocity
                dx = self.slingshot.x - current_bird.x
                dy = (self.slingshot.y - 50) - current_bird.y

                if dx > 10:  # Only launch if pulled back enough
                    vel_x = dx * 0.2
                    vel_y = dy * 0.2
                    current_bird.launch(vel_x, vel_y)
                    self.game_state = "flying"
                else:
                    # Reset bird position
                    current_bird.x = self.slingshot.x
                    current_bird.y = self.slingshot.y - 50

                self.drag_pos = None

        return True

    def draw(self):
        # Sky gradient
        for y in range(HEIGHT - 60):
            color_val = int(135 + (y / HEIGHT) * 50)
            pygame.draw.line(screen, (color_val, 200 + int(y / HEIGHT * 30), 235),
                           (0, y), (WIDTH, y))

        # Clouds
        for cx, cy, size in [(100, 80, 40), (300, 50, 35), (600, 70, 45), (850, 100, 38)]:
            pygame.draw.circle(screen, WHITE, (cx, cy), size)
            pygame.draw.circle(screen, WHITE, (cx - size//2, cy + 10), size - 10)
            pygame.draw.circle(screen, WHITE, (cx + size//2, cy + 5), size - 5)

        # Ground
        pygame.draw.rect(screen, GRASS_GREEN, (0, HEIGHT - 60, WIDTH, 60))
        pygame.draw.rect(screen, DARK_GREEN, (0, HEIGHT - 60, WIDTH, 5))

        # Draw underground layers
        pygame.draw.rect(screen, BROWN, (0, HEIGHT - 40, WIDTH, 40))

        # Draw particles
        for particle in self.particles:
            particle.draw(screen)

        # Draw blocks
        for block in self.blocks:
            block.draw(screen)

        # Draw pigs
        for pig in self.pigs:
            pig.draw(screen)

        # Draw slingshot and current bird
        current_bird = self.get_current_bird()
        self.slingshot.draw(screen, current_bird, self.drag_pos)

        # Draw current bird
        if current_bird and not current_bird.launched:
            current_bird.draw(screen)

        # Draw launched birds
        for bird in self.birds:
            if bird.launched:
                bird.draw(screen)

        # Draw trajectory preview
        if self.dragging and current_bird:
            dx = self.slingshot.x - current_bird.x
            dy = (self.slingshot.y - 50) - current_bird.y
            vel_x = dx * 0.2
            vel_y = dy * 0.2

            px, py = current_bird.x, current_bird.y
            for i in range(30):
                px += vel_x
                py += vel_y
                vel_y += GRAVITY

                if py > HEIGHT - 60:
                    break

                if i % 3 == 0:
                    alpha = int(255 * (1 - i / 30))
                    dot_surface = pygame.Surface((6, 6), pygame.SRCALPHA)
                    pygame.draw.circle(dot_surface, (255, 255, 255, alpha), (3, 3), 3)
                    screen.blit(dot_surface, (int(px) - 3, int(py) - 3))

        # Draw remaining birds
        remaining = len(self.birds) - self.current_bird_index - 1
        for i in range(remaining):
            bx = 50 + i * 30
            by = HEIGHT - 30
            bird_type = self.birds[self.current_bird_index + 1 + i].bird_type if self.current_bird_index + 1 + i < len(self.birds) else "red"
            color = RED if bird_type == "red" else YELLOW if bird_type == "yellow" else BLUE
            pygame.draw.circle(screen, color, (bx, by), 12)
            pygame.draw.circle(screen, BLACK, (bx, by), 12, 2)

        # UI
        score_text = font_small.render(f"Score: {self.score}", True, BLACK)
        screen.blit(score_text, (WIDTH - 150, 10))

        level_text = font_small.render(f"Level {self.level}", True, BLACK)
        screen.blit(level_text, (WIDTH // 2 - level_text.get_width() // 2, 10))

        # Instructions
        if self.game_state == "aiming":
            hint = font_small.render("Drag bird to aim, release to launch!", True, BLACK)
            screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 30))
        elif self.game_state == "flying":
            current = self.get_current_bird()
            if current and not current.ability_used:
                if current.bird_type == "yellow":
                    hint = font_small.render("Press SPACE for speed boost!", True, BLACK)
                elif current.bird_type == "blue":
                    hint = font_small.render("Press SPACE to split!", True, BLACK)
                else:
                    hint = font_small.render("", True, BLACK)
                screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 30))
        elif self.game_state == "waiting":
            hint = font_small.render("Press SPACE for next bird", True, BLACK)
            screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 30))

        # Game over screen
        if self.game_state == "ended":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))

            text = font_big.render("LEVEL FAILED", True, RED)
            screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - 60))

            score_text = font_medium.render(f"Score: {self.score}", True, WHITE)
            screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, HEIGHT // 2))

            restart = font_small.render("Press R to restart or SPACE to try again", True, WHITE)
            screen.blit(restart, (WIDTH // 2 - restart.get_width() // 2, HEIGHT // 2 + 50))

        # Level complete screen
        if self.game_state == "level_complete":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))

            text = font_big.render("LEVEL COMPLETE!", True, YELLOW)
            screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - 80))

            score_text = font_medium.render(f"Score: {self.score}", True, WHITE)
            screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, HEIGHT // 2 - 20))

            # Star rating
            remaining_birds = len(self.birds) - self.current_bird_index - 1
            stars = min(3, 1 + remaining_birds)
            star_text = font_medium.render("*" * stars, True, YELLOW)
            screen.blit(star_text, (WIDTH // 2 - star_text.get_width() // 2, HEIGHT // 2 + 30))

            next_text = font_small.render("Press SPACE for next level", True, WHITE)
            screen.blit(next_text, (WIDTH // 2 - next_text.get_width() // 2, HEIGHT // 2 + 80))

        # Win screen
        if self.game_state == "won":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))

            text = font_big.render("YOU WIN!", True, YELLOW)
            screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - 80))

            total_text = font_medium.render(f"Total Score: {self.total_score}", True, WHITE)
            screen.blit(total_text, (WIDTH // 2 - total_text.get_width() // 2, HEIGHT // 2 - 20))

            congrats = font_small.render("Congratulations! All pigs defeated!", True, GREEN)
            screen.blit(congrats, (WIDTH // 2 - congrats.get_width() // 2, HEIGHT // 2 + 30))

            restart = font_small.render("Press SPACE to play again", True, WHITE)
            screen.blit(restart, (WIDTH // 2 - restart.get_width() // 2, HEIGHT // 2 + 70))

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                running = self.handle_event(event)

            self.update()
            self.draw()
            clock.tick(60)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()
