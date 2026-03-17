"""
Levels.py — hand-crafted level definitions.

HOW TO ADD A LEVEL:
  1. Create a new Level(...) at the bottom of this file.
  2. Add it to the LEVELS list.

Level(
    platforms = [(x, y, width, height), ...],
    door      = (x, y),          # top-left corner of the exit door
    spawn     = (x, y),          # player spawn position
    modifiers = PlayerModifiers(...),  # optional: override player physics
)

PlayerModifiers fields (all optional, defaults match the base game):
    gravity          – gravity added each tick when falling  (default 0.5)
    gravity_hold     – gravity when jump button is held down  (default 1.5)
    jump_speed       – upward velocity on jump  (default -12)
    acceleration     – horizontal speed added per frame  (default 1.0)
    friction         – horizontal speed multiplier per frame  (default 0.85)
    max_fall_speed   – terminal falling velocity  (default 15)

World is 800 x 600.  Floor is at y=560 (40 px tall).
Player is 40 x 40.  Door is 20 wide x 80 tall.
Max jump height ≈ 150 px.  Max horizontal reach ≈ 320 px per jump.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Union


@dataclass
class PlayerModifiers:
    """Per-level physics tweaks for the player.  All values are optional;
    unset fields fall back to the original hardcoded defaults."""
    gravity:        float = 0.5    # added each tick while falling
    gravity_hold:   float = 1.5   # added when jump button is NOT held (faster fall)
    jump_speed:     float = -12   # upward velocity on jump  (negative = up)
    acceleration:   float = 1.0   # horizontal speed delta per frame
    friction:       float = 0.85  # horizontal speed multiplier per frame
    max_fall_speed: float = 15    # terminal falling velocity


@dataclass
class Level:
    platforms:  List[Tuple[int, int, int, int]]            # (x, y, w, h)
    door:       Tuple[int, int]                             # (x, y) top-left
    spawn:      Tuple[int, int]                             # (x, y) player start

    # Optional theming — hook these up in mygame_client.py when ready
    # background: RGB tuple → solid colour fill
    #             str       → path to a background image
    #             None      → default black
    background: Optional[Union[Tuple[int, int, int], str]] = None
    theme:      Optional[str] = None   # e.g. "cave", "space", "forest"

    # Per-level player physics modifiers
    modifiers:  PlayerModifiers = field(default_factory=PlayerModifiers)


# ---------------------------------------------------------------------------
# Level definitions — edit freely!
# ---------------------------------------------------------------------------

LEVEL_1 = Level(
    platforms=[
        # Ground
        (0,   560, 800, 40),
        # Staircase going up-right
        (100, 450, 130, 20),
        (260, 350, 130, 20),
        (420, 250, 130, 20),
        (580, 150, 130, 20),
    ],
    door=(740, 480),
    spawn=(20, 515),
    background=(20, 20, 40),   # dark blue
    theme="default",
)

LEVEL_2 = Level(
    platforms=[
        # Ground
        (0,   560, 800, 40),
        # Left pillar platforms
        (50,  430, 120, 20),
        (50,  300, 120, 20),
        # Gap in the middle, high bridge
        (250, 200, 300, 20),
        # Right descent
        (600, 320, 120, 20),
        (600, 440, 120, 20),
    ],
    door=(740, 480),
    spawn=(20, 515),
    background=(40, 15, 15),   # dark red
    theme="cave",
    # Example: low-gravity cave level — floatier jumps, slower falling
    modifiers=PlayerModifiers(
        gravity=0.25,
        gravity_hold=0.8,
        jump_speed=-10,
        max_fall_speed=8,
    ),
)

# Add your own levels here ↓
# LEVEL_3 = Level(
#     platforms=[...],
#     door=(...),
#     spawn=(...),
# )

LEVELS = [LEVEL_1, LEVEL_2]
