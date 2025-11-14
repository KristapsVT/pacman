"""
Launcher that runs the horrorpackman runtime and then loads the map and keys.
Run this file to start the app with external MapLoader/KeyLoader orchestration.
"""
import time
import traceback

# Import the main runtime (this module performs setup on import)
try:
    import horrorpackman as game
    print('[ExE] Imported horrorpackman')
except Exception:
    print('[ExE] Failed importing horrorpackman:')
    traceback.print_exc()

# Allow the viz runtime a short moment to initialize
time.sleep(0.05)

# Attempt to load the Pac-Man animation module and run its animation
try:
    from PacMan import run_pacman_animation
    try:
        pm_node = run_pacman_animation()
        print('[ExE] PacMan animation started, node:', pm_node)
    except Exception:
        print('[ExE] PacMan animation failed to start:')
        traceback.print_exc()
except Exception:
    print('[ExE] PacMan module not available or failed to import:')
    traceback.print_exc()

# Load map and keys (if available)
pacmap_root = None
try:
    from MapLoader import build_and_attach_map
    pacmap_root = build_and_attach_map()
    print('[ExE] Map built, root:', pacmap_root)
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

print('[ExE] Startup complete. Use the game window to interact.')
