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
    """A random modifier active for a single level. Adjusts physics and projectile behaviour."""
    name: str
    # Player physics multipliers (1.0 = unchanged)
    gravity_mult: float = 1.0
    speed_mult: float = 1.0
    friction_mult: float = 1.0
    # Inverted controls (left/right swapped)
    inverted_controls: bool = False
    # Projectile overrides
    projectile_size_mult: float = 1.0
    projectile_speed_mult: float = 1.0
    restrict_spawn_edge: Optional[str] = None  # "top", "sides", or None


# ── Available random modifiers ───────────────────────────────────────────────
AVAILABLE_MODIFIERS: List[LevelModifier] = [
    LevelModifier("Low Gravity",       gravity_mult=0.5),
    LevelModifier("High Gravity",      gravity_mult=1.5),
    LevelModifier("Fast Movement",     speed_mult=1.5),
    LevelModifier("Ice Skates",        friction_mult=1.15),
    LevelModifier("Inverted Controls", inverted_controls=True),
    LevelModifier("Meteor Shower",     projectile_size_mult=2.0, projectile_speed_mult=0.5, restrict_spawn_edge="top"),
    LevelModifier("Sniper Fire",       projectile_size_mult=0.5, projectile_speed_mult=2.0, restrict_spawn_edge="sides"),
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
        "If you fall in spikes, you lose a life.",
        "Adjust volume with + and - keys."
    ]
)

LEVEL_1 = Level(
    name="The Beginning",
    platforms=[

        (0,   1000, 1920, 80), #Ground
        (100,  900, 100, 20), #left under
        (1770, 900, 100, 20), #right under
        (560, 980, 100, 20), #center left under
        (1260, 980, 100, 20), #center right under
        (910, 800, 100, 20), #center under
        (260, 700, 200, 20), #left middle
        (1460, 700, 200, 20), #right middle
        (710, 550, 100, 20), #center middle left
        (1110, 550, 100, 20), #center middle right
        (810, 700, 100, 20), #middle block left
        (1010, 700, 100, 20), #middle block right
        (810, 400, 300, 20), #top middle
        (510, 300, 100, 20), #top middle left
        (1300, 300, 100, 20), #top middle right
        (200, 400, 200, 20), #left upper
        (1520, 400, 200, 20), #right upper
        (0, 500, 100, 20), #left upper under
        (1820, 500, 100, 20), #right upper under
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
        # Left pillar platforms (zigzag up)
        (150, 850, 120, 20),
        (50,  700, 120, 20),
        (180, 550, 120, 20),
        (50,  400, 120, 20),
        # Middle bridge
        (250, 250, 400, 20),
        # Right descent
        (750, 350, 150, 20),
        (950, 450, 150, 20),
        (1200, 550, 150, 20),
        (1450, 650, 150, 20),
        (1700, 750, 150, 20),
    ],
    door=(1750, 670),
    spawn=(50, 900),
    background="images/Level2/cavebackground.jpg",  # dark red
    projectile_images=["images/Level2/image-removebg-preview.png"],
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
        
        # Bottom center
        (900, 900,  120, 20),
        # Lower section
        (650, 860,  120, 20),
        (1150, 860, 120, 20),
        (467, 750,  120, 20),
        (1333, 750, 120, 20),
        # Middle section
        (400, 600,  120, 20),
        (1400, 600, 120, 20),
        # True Center
        (900, 600,  120, 20),
        # Upper section
        (467, 450,  120, 20),
        (1333, 450, 120, 20),
        (650, 340,  120, 20),
        (1150, 340, 120, 20),
        # Top center
        (900, 300,  120, 20),
    ],
    door=(950, 220),
    spawn=(940, 960),
    background="images/Level3/forestbg.jpg",    # dark green
    projectile_images=["images/Level3/banana.png"],
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
    spawn=(150, 700),# extra wide and deep floor
    theme="ice",
    background="images/Level4/ice_bg.png",
    projectile_images=["images/Level4/ice_spike.png"],
    modifiers=PlayerModifiers(
        friction=0.99,       # Very slippery map
        acceleration=0.3,    # Difficult to accelerate (ice)
    ),
    world_size=(1920, 1080)
)

LEVEL_5 = Level(
    name="Beach Resort",
    platforms=[
        # Ground
        (0,   1000, 1920, 80),
        # Some low platforms
        (150, 850, 200, 20),
        (450, 700, 200, 20),
        (800, 600, 300, 20),
        (1200, 750, 200, 20),
        (1500, 850, 200, 20),
    ],
    door=(1800, 920),
    spawn=(50, 900),
    theme="beach",
    background="images/Level5/scenic-view-of-beach-against-clear-blue-sky-740672775-597a52fdc412440010fe86a9.jpg",  # Sandy color
    projectile_images=["images/Level5/coconut.png"],
    world_size=(1920, 1080)
)

LEVELS = [LEVEL_1, LEVEL_2, LEVEL_3, LEVEL_4, LEVEL_5]
