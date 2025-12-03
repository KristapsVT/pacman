import time
import traceback
import os
import vizact

try:
    os.environ['EXTERNAL_PACMAN_AI'] = '1'
    import Player as game
    print('[ExE] Imported Player runtime')
except Exception:
    print('[ExE] Failed importing Player:')
    traceback.print_exc()

time.sleep(0.05)

try:
    import Ambience
    Ambience.init()
    print('[ExE] Ambience (fog & sound) initialized')
except Exception:
    print('[ExE] Ambience module not available or failed:')
    traceback.print_exc()

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

pacmap_root = None
wall_nodes = []
floor_node = None
try:
    from MapLoader import load_pacmap
    pacmap_root, floor_node, wall_nodes = load_pacmap(apply_style=True)
    print('[ExE] Map built, root:', pacmap_root, 'walls:', len(wall_nodes))
    
    if floor_node is not None:
        try:
            import Ambience
            Ambience.disable_fog_on_node(floor_node)
        except Exception:
            print('[ExE] Could not disable fog on floor')
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

try:
    from LockLoader import spawn_locks_on_map
    locks_group, locks = spawn_locks_on_map(map_root=pacmap_root if pacmap_root is not None else None,
                                            attach_to_map=True)
    print('[ExE] Locks spawned:', locks)
except Exception:
    print('[ExE] LockLoader not available or failed:')
    traceback.print_exc()

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

try:
    import LockUnlocker
    try:
        player_node = getattr(game, 'player', None)
        if player_node is not None:
            try:
                import Escape
                try:
                    Escape.init(player_node, map_root=pacmap_root, cell_size=3.0, restart_callback=getattr(game, 'restart', None))
                    print('[ExE] Escape initialized')
                except Exception:
                    print('[ExE] Escape.init failed')
            except Exception:
                pass

            def _on_unlock(color, node):
                try:
                    print('[ExE] Lock unlocked:', color, 'node=', node)
                except Exception:
                    pass
                try:
                    if 'Escape' in globals():
                        try:
                            Escape.on_unlock(color, node)
                        except Exception:
                            pass
                except Exception:
                    pass

            try:
                LockUnlocker.init(player_node, map_root=pacmap_root, on_unlock=_on_unlock)
                print('[ExE] LockUnlocker initialized')
            except Exception:
                print('[ExE] LockUnlocker.init failed')
        else:
            print('[ExE] No player node found; LockUnlocker not initialized')
    except Exception:
        print('[ExE] Failed to initialize LockUnlocker:')
        traceback.print_exc()
except Exception:
    print('[ExE] LockUnlocker module not available')

print('[ExE] Startup complete. Waiting for delayed Pac-Man spawn...')

