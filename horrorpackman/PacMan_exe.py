"""
Launcher that runs the horrorpackman runtime and then loads the map and keys.
Run this file to start the app with external MapLoader/KeyLoader orchestration.
"""
import time
import traceback
# No launcher popups: user requested removal of on-screen text popups.

# Import the main runtime (this module performs setup on import)
try:
    import horrorpackman as game
    print('[ExE] Imported horrorpackman')
except Exception:
    print('[ExE] Failed importing horrorpackman:')
    traceback.print_exc()

# Allow the viz runtime a short moment to initialize
time.sleep(0.05)

# Defer starting the Pac-Man animation until the map and player references are available.

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
