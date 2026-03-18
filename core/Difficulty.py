"""
Difficulty.py — Centralized difficulty scaling based on levels played.

All game-wide difficulty parameters live here. To tune the curve,
only this file needs to change.
"""

from dataclasses import dataclass


# ── Constants ────────────────────────────────────────────────────────────────

MODIFIER_UNLOCK_LEVEL = 2   # levels_played must exceed this before modifiers appear
MODIFIER_CHANCE       = 0.5 # probability of a random modifier each level load


# ── Difficulty settings (computed from levels_played) ────────────────────────

@dataclass
class DifficultySettings:
    """
    All difficulty parameters derived from how many levels have been played.

    levels_played: int  — incremented every time a new level is loaded.
    """
    levels_played: int

    @property
    def warning_time(self) -> float:
        """
        How long (in seconds) the edge warning shows before a projectile spawns.

        Starts at 1.0s and decreases by 0.15s every 3 levels,
        flooring at 0.2s so there is always *some* warning.

        levels  0-2  → 1.00s
        levels  3-5  → 0.85s
        levels  6-8  → 0.70s
        levels  9-11 → 0.55s
        levels 12-14 → 0.40s
        levels 15-17 → 0.25s
        levels 18+   → 0.20s  (minimum)
        """
        reduction = (self.levels_played // 3) * 0.15
        return max(0.2, 1.0 - reduction)

    @property
    def spawn_rate_per_sec(self) -> float:
        """
        Expected number of ProjectileWarnings created per second.

        Starts at 1.0/sec and grows by 0.2/sec per level, capped at 3.5/sec.
        """
        return min(3.5, 1.0 + self.levels_played * 0.2)

    @property
    def projectile_speed_mult(self) -> float:
        """
        Multiplier applied to every projectile's velocity vector.

        Starts at 1.0× and grows by 0.08 per level, capped at 2.5×.
        """
        return min(2.5, 1.0 + self.levels_played * 0.08)
