"""
Launcher that runs the horrorpackman runtime and then loads the map and keys.
Run this file to start the app with external MapLoader/KeyLoader orchestration.
"""
import time
import traceback
import os
# No launcher popups: user requested removal of on-screen text popups.

# Import the main runtime (this module performs setup on import)
try:
    # Signal to horrorpackman not to auto-create Pac-Man AI
    os.environ['EXTERNAL_PACMAN_AI'] = '1'
    import horrorpackman as game
    print('[ExE] Imported horrorpackman')
except Exception:
    print('[ExE] Failed importing horrorpackman:')
    traceback.print_exc()

# Allow the viz runtime a short moment to initialize
time.sleep(0.05)

# Attempt to load the Pac-Man animation module and run its animation
pm_node = None
try:
    from PacManLoaderAndAnimations import run_pacman_animation
    try:
        # Parent under map root if already built
        parent_root = getattr(game, 'pacmap_root', None)
        pm_node = run_pacman_animation(parent=parent_root)
        print('[ExE] PacMan animation started, node:', pm_node)
    except Exception:
        print('[ExE] PacMan animation failed to start:')
        traceback.print_exc()
except Exception:
    print('[ExE] PacMan module not available or failed to import:')
    traceback.print_exc()

# Load map and keys (if available)
pacmap_root = None
wall_nodes = []
floor_node = None
try:
    # use load_pacmap to obtain wall nodes for AI collision checks
    from MapLoader import load_pacmap
    pacmap_root, floor_node, wall_nodes = load_pacmap(apply_style=True)
    print('[ExE] Map built, root:', pacmap_root, 'walls:', len(wall_nodes))
except Exception:
    print('[ExE] MapLoader not available or failed:')
    traceback.print_exc()

try:
    from KeyLoader import spawn_keys_on_map
    keys = spawn_keys_on_map(parent=pacmap_root if pacmap_root is not None else None,
                              map_root=pacmap_root if pacmap_root is not None else None)
    print('[ExE] Keys spawned:', keys)
except Exception:
    print('[ExE] KeyLoader not available or failed:')
    traceback.print_exc()

# Spawn locks (if LockLoader available) and attach to pacmap_root
try:
    from LockLoader import spawn_locks_on_map
    locks_group, locks = spawn_locks_on_map(map_root=pacmap_root if pacmap_root is not None else None,
                                            attach_to_map=True)
    print('[ExE] Locks spawned:', locks)
except Exception:
    print('[ExE] LockLoader not available or failed:')
    traceback.print_exc()

# Initialize KeyCollector so player can look at and click keys
try:
    import KeyCollector
    try:
        player_node = getattr(game, 'player', None)
        if player_node is not None:
            try:
                KeyCollector.init(player_node)
                print('[ExE] KeyCollector initialized')
            except Exception:
                print('[ExE] KeyCollector.init failed')
        else:
            print('[ExE] No player node found; KeyCollector not initialized')
    except Exception:
        print('[ExE] Failed to initialize KeyCollector:')
        traceback.print_exc()
except Exception:
    print('[ExE] KeyCollector module not available')

print('[ExE] Startup complete. Use the game window to interact.')

# Attach AI to existing animation node (single Pac-Man instance)
try:
    if pm_node is not None:
        from PacManAI import PacManChaser
        game.pacman_ai = PacManChaser(map_root=pacmap_root, existing_node=pm_node)
        print('[ExE] PacMan AI attached to existing animation node')
    else:
        print('[ExE] Skipped AI attach: animation node missing')
except Exception:
    print('[ExE] Failed to attach PacMan AI:')
    traceback.print_exc()

print('[ExE] Startup complete. Use the game window to interact.')

