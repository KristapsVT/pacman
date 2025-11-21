"""
Launcher that runs the Player runtime and then loads the map, keys, locks, and Pac-Man.
Run this file to start the app with external MapLoader/KeyLoader orchestration.
Former references to horrorpackman.py have been migrated to Player.py.
"""
import time
import traceback
import os
import vizact
# No launcher popups: user requested removal of on-screen text popups.

# Import the main runtime (this module performs setup on import)
try:
    # Signal to Player runtime not to auto-create Pac-Man AI
    os.environ['EXTERNAL_PACMAN_AI'] = '1'
    # Use Player module as the main runtime
    import Player as game
    print('[ExE] Imported Player runtime')
except Exception:
    print('[ExE] Failed importing Player:')
    traceback.print_exc()

# Allow the viz runtime a short moment to initialize
time.sleep(0.05)

pm_node = None
def _delayed_spawn():
    global pm_node
    if pm_node is not None:
        return
    try:
        from PacManLoaderAndAnimations import run_pacman_animation
        parent_root = getattr(game, 'pacmap_root', None)
        pm_node = run_pacman_animation(parent=parent_root)
        print('[ExE] PacMan animation spawned after 3s delay:', pm_node)
        try:
            from PacManAI import PacManChaser
            game.pacman_ai = PacManChaser(map_root=parent_root, existing_node=pm_node)
            print('[ExE] PacMan AI attached after delay')
        except Exception:
            print('[ExE] PacMan AI attach failed after delay:')
            traceback.print_exc()
    except Exception:
        print('[ExE] PacMan animation spawn failed:')
        traceback.print_exc()

vizact.ontimer(3.0, _delayed_spawn)
print('[ExE] Scheduled Pac-Man spawn after 3 seconds')

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

print('[ExE] Startup complete. Waiting for delayed Pac-Man spawn...')

