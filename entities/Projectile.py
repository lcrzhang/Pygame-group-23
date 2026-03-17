import pygame
import random
import math

# ── Module-level image cache ──────────────────────────────────────────────────
# Maps file-path strings → pygame.Surface so each image is only loaded once.
_IMAGE_CACHE: dict[str, pygame.Surface] = {}

_WARNING_IMAGE_PATH = "images/Warnings/Untitled design.png"


def _get_image(path: str) -> pygame.Surface:
    """Return a cached Surface for the given path, loading it on first use."""
    if path not in _IMAGE_CACHE:
        _IMAGE_CACHE[path] = pygame.image.load(path).convert_alpha()
    return _IMAGE_CACHE[path]


# ── Projectile ────────────────────────────────────────────────────────────────

class Projectile:
    """
    A moving hazard that travels across the screen.

    When `image_path` is given the projectile is rendered as that image
    (scaled to `size` × `size`).  Without an image it falls back to a
    randomly-shaped, randomly-coloured polygon — useful when a level has
    no image assets yet.
    """

    def __init__(self, position, speed, size, image_path: str | None = None):
        self.position   = pygame.Vector2(position)
        self.speed      = pygame.Vector2(speed)
        self.width      = size
        self.height     = size
        # Image-based rendering (stored as a path so the object stays picklable)
        self.image_path = image_path
        # Fallback shape rendering
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
        if self.image_path:
            img    = _get_image(self.image_path)
            scaled = pygame.transform.scale(img, (int(self.width), int(self.height)))
            surface.blit(scaled, (int(self.position.x), int(self.position.y)))
        else:
            # Fallback: draw a coloured shape
            if self.shape == 'rect':
                pygame.draw.rect(surface, self.color, self.get_rect())
            elif self.shape == 'circle':
                radius = self.width // 2
                center = (int(self.position.x + radius), int(self.position.y + radius))
                pygame.draw.circle(surface, self.color, center, radius)
            elif self.shape == 'triangle':
                points = [
                    (self.position.x + self.width / 2, self.position.y),
                    (self.position.x, self.position.y + self.height),
                    (self.position.x + self.width, self.position.y + self.height),
                ]
                pygame.draw.polygon(surface, self.color, points)


# ── ProjectileWarning ─────────────────────────────────────────────────────────

class ProjectileWarning:
    """
    A blinking indicator drawn on the screen edge where a projectile will soon
    appear.  Once `time_remaining` reaches 0, call `spawn_projectile()` to get
    the actual Projectile object.

    Parameters
    ----------
    spawn_pos        : (x, y) — off-screen spawn position of the future projectile
    base_speed       : (vx, vy) — un-scaled velocity of the future projectile
    size             : pixel size of the future projectile
    warning_time     : seconds to show the warning before spawning
    projectile_images: list of image paths the level uses; one is chosen randomly
    """

    # Visual constants
    WARN_SIZE    = 48    # side length of the warning icon in pixels
    BLINK_RATE   = 8.0   # blinks per second
    URGENT_SCALE = 1.25  # scale-up factor when < 0.3 s remain

    def __init__(self, spawn_pos, base_speed, size, warning_time: float,
                 projectile_images: list[str] | None = None):
        self.spawn_pos    = pygame.Vector2(spawn_pos)
        self.base_speed   = pygame.Vector2(base_speed)
        self.size         = size
        self.warning_time    = warning_time
        self.time_remaining  = warning_time

        # Pick the image that the resulting projectile will use (may be None)
        if projectile_images:
            self.chosen_image = random.choice(projectile_images)
        else:
            self.chosen_image = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def update(self, delta: float):
        """Advance the countdown by `delta` seconds."""
        self.time_remaining -= delta

    def is_expired(self) -> bool:
        """True once the countdown has finished — time to spawn the projectile."""
        return self.time_remaining <= 0

    def spawn_projectile(self, speed_mult: float = 1.0) -> Projectile:
        """Return the real Projectile with its velocity scaled by `speed_mult`."""
        scaled_speed = self.base_speed * speed_mult
        return Projectile(self.spawn_pos, scaled_speed, self.size,
                          image_path=self.chosen_image)

    # ── Drawing ───────────────────────────────────────────────────────────────

    def _edge_point(self, world_size: pygame.Vector2) -> pygame.Vector2:
        """
        Project the off-screen spawn position onto the nearest screen edge so
        the warning icon sits exactly on the border regardless of spawn_pos.
        """
        x, y = self.spawn_pos
        w, h = world_size

        edge_x = max(0, min(w, x))
        edge_y = max(0, min(h, y))

        off_x = max(0, -x, x - w)
        off_y = max(0, -y, y - h)

        if off_x >= off_y:
            edge_x = 0 if x < 0 else w
        else:
            edge_y = 0 if y < 0 else h

        return pygame.Vector2(edge_x, edge_y)

    def draw(self, surface: pygame.Surface, world_size: pygame.Vector2):
        elapsed_frac = 1.0 - (self.time_remaining / self.warning_time)
        urgent = self.time_remaining < 0.3

        # Blink: skip drawing on "off" beats (always show when urgent)
        blink_phase = (elapsed_frac * self.warning_time * self.BLINK_RATE) % 1.0
        if blink_phase > 0.5 and not urgent:
            return

        # Direction the projectile will travel (normalised)
        travel_dir = pygame.Vector2(self.base_speed)
        if travel_dir.length() > 0:
            travel_dir = travel_dir.normalize()

        # Edge point, then push the icon just inside the border
        edge  = self._edge_point(world_size)
        scale = self.URGENT_SCALE if urgent else 1.0
        size  = int(self.WARN_SIZE * scale)

        BORDER_INSET = 4          # pixels inside the white border
        ARROW_LEN    = int(14 * scale)
        ARROW_WIDTH  = int(6  * scale)

        # Icon centre: start at the edge, step inward so the icon is fully visible
        icon_centre = edge + travel_dir * (size / 2 + BORDER_INSET)

        WARN_COLOR   = (255, 140, 0)
        URGENT_COLOR = (255,  30, 30)
        color = URGENT_COLOR if urgent else WARN_COLOR

        # ── Draw exclamation-mark icon ────────────────────────────────────────
        try:
            icon_orig   = _get_image(_WARNING_IMAGE_PATH)
            icon_scaled = pygame.transform.scale(icon_orig, (size, size))
            blit_x = int(icon_centre.x - size / 2)
            blit_y = int(icon_centre.y - size / 2)
            surface.blit(icon_scaled, (blit_x, blit_y))
        except Exception:
            # Fallback circle if image is missing
            pygame.draw.circle(surface, color, (int(icon_centre.x), int(icon_centre.y)),
                               size // 2, 3)

        # ── Draw direction arrow next to the icon ─────────────────────────────
        # Arrow starts from the far edge of the icon, points in travel direction
        arrow_start = icon_centre + travel_dir * (size / 2 + 4)
        arrow_tip   = arrow_start + travel_dir * ARROW_LEN
        perp        = pygame.Vector2(-travel_dir.y, travel_dir.x) * ARROW_WIDTH

        pygame.draw.polygon(surface, color, [
            (int(arrow_tip.x),               int(arrow_tip.y)),
            (int(arrow_start.x + perp.x),    int(arrow_start.y + perp.y)),
            (int(arrow_start.x - perp.x),    int(arrow_start.y - perp.y)),
        ])
