"""
Levels.py — hand-crafted level definitions.

HOW TO ADD A LEVEL:
  1. Create a new Level(...) at the bottom of this file.
  2. Add it to the LEVELS list.

Level(
    platforms = [(x, y, width, height), ...],
    door      = (x, y),          # top-left corner of the exit door
    spawn     = (x, y),          # player spawn position
    world_size=(800, 600),       # optional: size of the level (width, height)
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
from typing import List, Tuple, Optional, Union, Any


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
class LevelModifier:
    """A random bonus/malus that can be active for a single level.
    
    Currently these are PLACEHOLDERS — they show on the HUD but have
    no gameplay effect yet.  Implement the effect in Game_State.update()
    once you are ready.
    """
    name:        str               # short display name shown in HUD
    description: str               # one-line flavour text
    color:       Tuple[int,int,int] # badge background colour (RGB)


# ── Available random modifiers (placeholders) ────────────────────────────────
# Add more entries here whenever you want new random modifiers.

AVAILABLE_MODIFIERS: List[LevelModifier] = [
    LevelModifier("Double Jump",  "Allows a second jump in the air",    (80,  40, 160)),
    LevelModifier("Speed Boost",  "Increases horizontal movement speed", (200, 120,  0)),
    LevelModifier("Low Gravity",  "Reduces gravity for all players",     ( 30, 140, 200)),
    LevelModifier("Shield",       "Blocks the next projectile hit",      ( 20, 160,  80)),
    LevelModifier("Magnet",       "Attracts nearby collectibles",        (180,  30,  80)),
]


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
    name:       str = "Unknown Level"  # display name for the map


    # Optional list of image file paths to use as projectile sprites for this level.
    # If None or empty the Projectile class falls back to coloured shapes.
    projectile_images: Optional[List[str]] = None

    # Optional rects that represent instant kill zones (x, y, w, h)
    kill_zones: List[Tuple[int, int, int, int]] = field(default_factory=list)

    # Text lines to draw on the background
    instructions: List[str] = field(default_factory=list)

    # Per-level player physics modifiers
    modifiers:  PlayerModifiers = field(default_factory=PlayerModifiers)
    
    # Size of the level surface
    world_size: Tuple[int, int] = (1920, 1080)


# ---------------------------------------------------------------------------
# Level definitions — edit freely!
# ---------------------------------------------------------------------------

LOBBY_LEVEL = Level(
    name="Starter Lobby",
    platforms=[
        (0, 1040, 1920, 40),    # Ground
        (200, 925, 400, 20),    # Left platform
        (760, 800, 400, 20),    # Center platform
        (1320, 925, 400, 20),   # Right platform
    ],
    kill_zones=[],
    door=(940, 720),            # On the center platform
    spawn=(100, 950),
    theme="lobby",
    world_size=(1920, 1080),
    instructions=[
        "Welcome to the game!",
        "Use Arrow Keys or WASD to move & jump.",
        "Everyone must enter the door to start.",
        "Dodge the dropping projectiles!",
        "If you fall in spikes, you lose a life."
    ]
)

LEVEL_1 = Level(
    name="The Beginning",
    platforms=[
        # Ground
        (0,   1000, 1920, 80),
        # Staircase going up-right
        (100, 450, 130, 20),
        (260, 350, 130, 20),
        (420, 250, 130, 20),
        (580, 150, 130, 20),
    ],
    door=(1900, 920),
    spawn=(20, 515),
    background="images/Level1/level1_bg.png",
    theme="default",
    projectile_images=[
        "images/Level1/space_invader_1.png",
        "images/Level1/space_invader_2.png",
        "images/Level1/space_invader_3.png",
        "images/Level1/space_invader_4.png",
        "images/Level1/space_invader_5.png",
    ],
)

LEVEL_2 = Level(
    name="Red Cave",
    platforms=[
        # Ground
        (0,   1000, 1920, 80),
        # Left pillar platforms
        (50,  430, 120, 20),
        (50,  300, 120, 20),
        # Gap in the middle, high bridge
        (250, 200, 300, 20),
        # Right descent
        (600, 320, 120, 20),
        (600, 440, 120, 20),
    ],
    door=(1900, 920),
    spawn=(20, 515),
    background=(40, 15, 15),   # dark red
    theme="cave",
    world_size=(1920, 1080),
    # Example: low-gravity cave level — floatier jumps, slower falling
    modifiers=PlayerModifiers(
        gravity=0.25,
        gravity_hold=0.8,
        jump_speed=-10,
        max_fall_speed=8,
    ),
)

# Add your own levels here ↓
LEVEL_3 = Level(
    name="Forest High",
    platforms=[
        # Ground
        (0,   1000, 1920, 80),
        (100, 1000, 150,  20),
        (350, 850,  150,  20),
        (600, 700,  150,  20),
        (900, 550,  200,  20),
        (1200,400,  150,  20),
    ],
    door=(1900, 920),
    spawn=(50, 1115),
    background=(20, 50, 20),    # dark green
    theme="forest",
    world_size=(1920, 1080),    # 2x width, 2x height
)

LEVEL_4 = Level(
    name="Icy Spikes",
    platforms=[
        # Left spawn platform
        (100, 800, 300, 20),
        # Platform higher up
        (500, 600, 300, 20),
        # Lower middle platform
        (900, 850, 300, 20),
        # Platform higher again
        (1300, 650, 300, 20),
        # Door platform
        (1600, 800, 250, 20)
    ],
    kill_zones=[
        # Spikes along the bottom over the entire 1920 map width
        (0, 1000, 1920, 80)
    ],
    door=(1700, 720),
    spawn=(150, 700),
    theme="ice",
    background="images/Level4/ice_bg.png",
    projectile_images=["images/Level4/ice_spike.png"],
    modifiers=PlayerModifiers(
        gravity=0.35,
        friction=0.99,       # Very slippery map
        acceleration=0.3,    # Difficult to accelerate (ice)
    ),
    world_size=(1920, 1080)
)

LEVELS = [LEVEL_1, LEVEL_2, LEVEL_3, LEVEL_4]
