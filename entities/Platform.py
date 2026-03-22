import pygame
import os

class Platform:
    """
    Represents a solid rectangular platform in the game world.
    Supports either a plain colored rectangle or a repeating texture image.
    """
    color = (150, 150, 150)

    # Class-level texture cache: path → pygame.Surface
    _texture_cache: dict = {}

    def __init__(self, x, y, width, height, texture_path=None):
        """Initializes a platform with given bounds and optional texture path."""
        self.rect = pygame.Rect(x, y, width, height)
        self._texture_path = texture_path
        self._tiled_surface = None  # built lazily

    # ── Class helper ─────────────────────────────────────────────────────────
    @classmethod
    def _load_texture(cls, path):
        """Load (and cache) a raw texture surface."""
        if path not in cls._texture_cache:
            try:
                cls._texture_cache[path] = pygame.image.load(path).convert_alpha()
            except Exception:
                cls._texture_cache[path] = None
        return cls._texture_cache[path]

    # ── Instance helper ───────────────────────────────────────────────────────
    def _build_tiled(self):
        """Create a surface the same size as this platform, tiled with the texture."""
        tex = self._load_texture(self._texture_path)
        if tex is None:
            self._tiled_surface = None
            return

        tw, th = tex.get_size()
        surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        for ty in range(0, self.rect.height, th):
            for tx in range(0, self.rect.width, tw):
                surf.blit(tex, (tx, ty))
        self._tiled_surface = surf

    # ── Public ────────────────────────────────────────────────────────────────
    def draw(self, surface):
        """Draws the tiled texture if available; otherwise falls back to a plain filled rect."""
        if self._texture_path:
            if self._tiled_surface is None:
                self._build_tiled()
            if self._tiled_surface is not None:
                surface.blit(self._tiled_surface, self.rect.topleft)
                return
        # Fallback: plain grey rectangle
        pygame.draw.rect(surface, Platform.color, self.rect)
