import pygame
import random
import math


class Projectile:
    
    def __init__(self, position, speed, size):
        self.position = pygame.Vector2(position)
        self.speed = pygame.Vector2(speed)
        self.width = size
        self.height = size
        self.color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
        self.shape = random.choice(['rect', 'circle', 'triangle'])

    def update(self, world_size):
        self.position += self.speed

    def is_off_screen(self, world_size):
        if self.position.x + self.width < 0 and self.speed.x < 0:
            return True
        if self.position.x > world_size.x and self.speed.x > 0:
            return True
        if self.position.y + self.height < 0 and self.speed.y < 0:
            return True
        if self.position.y > world_size.y and self.speed.y > 0:
            return True
        return False

    def get_rect(self):
        return pygame.Rect(self.position.x, self.position.y, self.width, self.height)

    def draw(self, surface):
        if self.shape == 'rect':
            rect = self.get_rect()
            pygame.draw.rect(surface, self.color, rect)
        elif self.shape == 'circle':
            radius = self.width // 2
            center = (int(self.position.x + radius), int(self.position.y + radius))
            pygame.draw.circle(surface, self.color, center, radius)
        elif self.shape == 'triangle':
            points = [
                (self.position.x + self.width / 2, self.position.y),
                (self.position.x, self.position.y + self.height),
                (self.position.x + self.width, self.position.y + self.height)
            ]
            pygame.draw.polygon(surface, self.color, points)


# ── Edge warning shown before a projectile spawns ────────────────────────────

class ProjectileWarning:
    """
    A blinking indicator drawn on the screen edge where a projectile will soon
    appear.  Once `time_remaining` reaches 0, call `spawn_projectile()` to get
    the actual Projectile object.

    Parameters
    ----------
    spawn_pos   : (x, y) — off-screen spawn position of the future projectile
    base_speed  : (vx, vy) — un-scaled velocity of the future projectile
    size        : pixel size of the future projectile
    warning_time: seconds to show the warning before spawning
    """

    # Visual constants
    ARROW_SIZE   = 18   # half-length of the warning arrow / triangle
    BLINK_RATE   = 8.0  # blinks per second
    WARN_COLOR   = (255, 140, 0)   # orange
    URGENT_COLOR = (255, 30,  30)  # red (last 0.3 s)

    def __init__(self, spawn_pos, base_speed, size, warning_time: float):
        self.spawn_pos    = pygame.Vector2(spawn_pos)
        self.base_speed   = pygame.Vector2(base_speed)
        self.size         = size
        self.warning_time = warning_time          # total duration
        self.time_remaining = warning_time        # countdown

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def update(self, delta: float):
        """Advance the countdown by `delta` seconds."""
        self.time_remaining -= delta

    def is_expired(self) -> bool:
        """True once the countdown has finished — time to spawn the projectile."""
        return self.time_remaining <= 0

    def spawn_projectile(self, speed_mult: float = 1.0) -> Projectile:
        """Return the real Projectile with its velocity scaled by `speed_mult`."""
        scaled_speed = self.base_speed * speed_mult
        return Projectile(self.spawn_pos, scaled_speed, self.size)

    # ── Drawing ──────────────────────────────────────────────────────────────

    def _edge_point(self, world_size: pygame.Vector2) -> pygame.Vector2:
        """
        Project the off-screen spawn position onto the nearest screen edge so
        the warning arrow sits exactly on the border regardless of spawn_pos.
        """
        x, y = self.spawn_pos
        w, h = world_size

        # clamp to border
        edge_x = max(0, min(w, x))
        edge_y = max(0, min(h, y))

        # prefer the axis that is furthest outside
        off_x = max(0, -x, x - w)
        off_y = max(0, -y, y - h)

        if off_x >= off_y:
            # came from left or right edge
            edge_x = 0 if x < 0 else w
        else:
            edge_y = 0 if y < 0 else h

        return pygame.Vector2(edge_x, edge_y)

    def draw(self, surface: pygame.Surface, world_size: pygame.Vector2):
        # Choose colour: urgent red in the last 0.3 s
        elapsed_frac = 1.0 - (self.time_remaining / self.warning_time)
        urgent = self.time_remaining < 0.3
        color  = self.URGENT_COLOR if urgent else self.WARN_COLOR

        # Blink: skip drawing on "off" beats
        blink_phase = (elapsed_frac * self.warning_time * self.BLINK_RATE) % 1.0
        if blink_phase > 0.5 and not urgent:
            return  # invisible half of blink cycle (always show when urgent)

        edge = self._edge_point(world_size)

        # Direction the arrow points (toward the interior)
        direction = pygame.Vector2(world_size.x / 2, world_size.y / 2) - edge
        if direction.length() > 0:
            direction = direction.normalize()

        # Draw a filled triangle pointing inward
        tip  = edge + direction * self.ARROW_SIZE
        perp = pygame.Vector2(-direction.y, direction.x) * (self.ARROW_SIZE * 0.6)
        base_left  = edge - direction * 4 + perp
        base_right = edge - direction * 4 - perp

        pygame.draw.polygon(surface, color, [
            (int(tip.x),        int(tip.y)),
            (int(base_left.x),  int(base_left.y)),
            (int(base_right.x), int(base_right.y)),
        ])

        # Pulse ring around the tip for extra visibility
        ring_r = int(self.ARROW_SIZE * 0.55 + math.sin(elapsed_frac * math.pi * 6) * 3)
        pygame.draw.circle(surface, color, (int(tip.x), int(tip.y)), ring_r, 2)
