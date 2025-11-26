"""Game over helper: teleports the player very high/low and spawns Game_Over.glb.

This module follows the project's defensive patterns: safe asset loading,
wrapper groups, and fallbacks to a box primitive when the GLB isn't available.
"""
import os
import random
try:
    import viz
    import vizshape
    try:
        import vizact
    except Exception:
        vizact = None
except Exception:
    # allow import in non-viz environments for static checks
    viz = None
    vizshape = None
    vizact = None


def _center_glb_local_in_wrapper(raw, center_blend=0.6, desired_bottom=0.0):
    try:
        minX, minY, minZ, maxX, maxY, maxZ = raw.getBoundingBox()
        cx = (minX + maxX) * 0.5
        cz = (minZ + maxZ) * 0.5
        try:
            sx, sy, sz, sr = raw.getBoundingSphere()
            a = float(center_blend)
            cx = cx * (1.0 - a) + sx * a
            cz = cz * (1.0 - a) + sz * a
        except Exception:
            pass
        liftY = float(desired_bottom) - minY
        raw.setPosition([-cx, liftY, -cz])
    except Exception:
        try:
            raw.setPosition([0, 0, 0])
        except Exception:
            pass


def _load_game_over_model(filename, desired_dims=(1.81, 3.73, 15.35), tint=None, fallback_color=(0.0, 0.0, 0.0)):
    """Load `filename` from `assets/` and attempt to size it to `desired_dims` (x,y,z).

    If the file is missing or loading fails, return a boxed primitive with those dims.
    """
    asset_path = os.path.normpath(os.path.join(os.path.dirname(__file__), 'assets', filename))
    if viz is not None and os.path.exists(asset_path):
        try:
            wrapper = viz.addGroup()
            raw = viz.addChild(asset_path)
            raw.setParent(wrapper)
            try:
                minX, minY, minZ, maxX, maxY, maxZ = raw.getBoundingBox()
                cur_x = maxX - minX
                cur_y = maxY - minY
                cur_z = maxZ - minZ
                sx = sy = sz = 1.0
                if cur_x > 0:
                    sx = float(desired_dims[0]) / float(cur_x)
                if cur_y > 0:
                    sy = float(desired_dims[1]) / float(cur_y)
                if cur_z > 0:
                    sz = float(desired_dims[2]) / float(cur_z)
                # apply scale to the raw node if supported
                try:
                    raw.setScale([sx, sy, sz])
                except Exception:
                    pass
            except Exception:
                pass
            _center_glb_local_in_wrapper(raw, desired_bottom=0.0)
            try:
                if tint is not None:
                    wrapper.color(*tint)
            except Exception:
                pass
            return wrapper
        except Exception:
            # fall through to primitive fallback
            pass

    # fallback primitive: a box with desired dims (x,y,z)
    if viz is not None and vizshape is not None:
        try:
            g = viz.addGroup()
            box = vizshape.addBox([desired_dims[0], desired_dims[1], desired_dims[2]])
            try:
                box.color(*fallback_color)
            except Exception:
                pass
            box.setParent(g)
            return g
        except Exception:
            pass

    # last resort: return None
    return None


# Module state
_player = None
_map_root = None
_game_node = None
_key_registered = False


def init(player, map_root=None):
    """Initialize module with the active `player` node and optional `map_root`.

    Call once at startup so `trigger_game_over()` can use these references.
    """
    global _player, _map_root
    _player = player
    _map_root = map_root
    # Register a convenient test key ('k') to trigger game over instantly.
    global _key_registered
    try:
        if vizact is not None and not _key_registered:
            try:
                vizact.onkeydown('k', lambda: trigger_game_over())
                vizact.onkeydown('K', lambda: trigger_game_over())
                _key_registered = True
            except Exception:
                _key_registered = False
    except Exception:
        _key_registered = False


def trigger_game_over():
    """Teleport the player (very high or very low) and spawn Game_Over.glb.

    Returns True on success.
    """
    global _player, _map_root, _game_node
    if _player is None:
        return False

    try:
        px, py, pz = _player.getPosition()
    except Exception:
        px = pz = 0.0
        py = 0.0

    # Teleport the player below the map.
    # Compute the lowest Y of the pacmap geometry (floor + walls) and teleport
    # the player a safe offset below it. If map geometry is unavailable, fall
    # back to moving the player down a fixed distance.
    map_min_y = None
    try:
        if _map_root is not None:
            parts = []
            try:
                floor = getattr(_map_root, '_pacmap_floor', None)
                if floor is not None:
                    parts.append(floor)
            except Exception:
                pass
            try:
                walls = getattr(_map_root, '_pacmap_walls', None)
                if walls:
                    parts.extend(walls)
            except Exception:
                pass

            for n in parts:
                if not n:
                    continue
                try:
                    bb = n.getBoundingBox()
                    if bb:
                        raw_minX, raw_minY, raw_minZ, raw_maxX, raw_maxY, raw_maxZ = bb
                        if map_min_y is None:
                            map_min_y = raw_minY
                        else:
                            map_min_y = min(map_min_y, raw_minY)
                        continue
                except Exception:
                    pass
                try:
                    _, py_n, _ = n.getPosition()
                    if map_min_y is None:
                        map_min_y = py_n
                    else:
                        map_min_y = min(map_min_y, py_n)
                except Exception:
                    pass
    except Exception:
        map_min_y = None

    teleport_offset = 20.0
    if map_min_y is not None:
        teleport_y = map_min_y - teleport_offset
    else:
        teleport_y = py - 50.0

    try:
        _player.setPosition((px, teleport_y, pz))
    except Exception:
        pass

    # re-read player position after teleport
    try:
        px, py, pz = _player.getPosition()
    except Exception:
        pass

    # remove previous game node
    try:
        if _game_node is not None:
            try:
                _game_node.remove()
            except Exception:
                try:
                    viz.remove(_game_node)
                except Exception:
                    pass
            _game_node = None
    except Exception:
        pass

    # choose parent for the spawned object
    parent = None
    try:
        parent = _map_root if _map_root is not None else None
    except Exception:
        parent = None

    # user's dims: thickness x wide x height (they provided 1.81 x 15.35 x 3.73)
    # interpret as (x, z, y) but we map to (x,y,z) with reasonable choice: (thickness, height, width)
    thickness = 1.81
    width = 15.35
    height = 3.73
    desired_dims = (thickness, height, width)

    node = _load_game_over_model('Game_Over.glb', desired_dims=desired_dims, tint=None, fallback_color=(0.0, 0.0, 0.0))
    if node is None:
        return False

    # Do NOT parent the spawned node under the map root. Parented nodes can
    # interpret `setPosition` as local coords which may place the node under
    # the map geometry. Leave the node un-parented so world coordinates align
    # with the player's world position.

    # compute ground Y from map floor if available, else fallback
    ground_y = 0.5
    try:
        if _map_root is not None:
            floor = getattr(_map_root, '_pacmap_floor', None)
            if floor is not None:
                try:
                    bb = floor.getBoundingBox()
                    if bb:
                        # bb = (minX,minY,minZ,maxX,maxY,maxZ)
                        minx, miny, minz, maxx, maxy, maxz = bb
                        ground_y = maxy + 0.05
                    else:
                        # fallback to node position
                        px_f, py_f, pz_f = floor.getPosition()
                        ground_y = py_f + 0.05
                except Exception:
                    try:
                        px_f, py_f, pz_f = floor.getPosition()
                        ground_y = py_f + 0.05
                    except Exception:
                        ground_y = 0.5
    except Exception:
        ground_y = 0.5

    # spawn position: directly in front of the player. If player's facing is available
    # use it; otherwise default to +z direction.
    forward_offset = 6.0
    spawn_x = px
    spawn_z = pz
    try:
        # attempt to use player's yaw (facing direction)
        e = _player.getEuler()
        # e may be (pitch, yaw, roll) or (x,y,z) depending on API
        yaw = 0.0
        try:
            yaw = float(e[1])
        except Exception:
            try:
                yaw = float(e[0])
            except Exception:
                yaw = 0.0
        import math
        rad = math.radians(yaw)
        dx = math.sin(rad)
        dz = math.cos(rad)
        spawn_x = px + dx * forward_offset
        spawn_z = pz + dz * forward_offset
    except Exception:
        spawn_x = px
        spawn_z = pz + forward_offset
    spawn_y = ground_y
    try:
        node.setPosition((spawn_x, spawn_y, spawn_z))
    except Exception:
        pass

    # slight side-angle
    try:
        node.setEuler((0.0, 25.0, 10.0))
    except Exception:
        try:
            node.setEuler([0, 25, 10])
        except Exception:
            pass

    try:
        node.disable(viz.LIGHTING)
    except Exception:
        pass

    _game_node = node
    return True
"""
GameOver module: handles the "squished by Pac-Man" screen with countdown and window close.
"""
import viz
import vizact

_game_over_active = False
_game_over_text = None
_countdown_text = None

def show_game_over_and_close():
    """
    Display 'You have been squished by Pac-Man!' message with a 3-2-1 countdown,
    then close the Vizard window.
    """
    global _game_over_active, _game_over_text, _countdown_text
    
    if _game_over_active:
        return  # Already triggered
    
    _game_over_active = True
    print('[GameOver] Player squished by Pac-Man!')
    
    try:
        # Create screen text using viz.addText with parent=viz.SCREEN
        _game_over_text = viz.addText('You have been squished by Pac-Man!', parent=viz.SCREEN)
        _game_over_text.setPosition(0.5, 0.6)  # Center horizontally, upper position
        _game_over_text.alignment(viz.ALIGN_CENTER_TOP)
        _game_over_text.fontSize(42)
        _game_over_text.color(viz.RED)
        
        # Create countdown text below the main message
        _countdown_text = viz.addText('Closing in 3...', parent=viz.SCREEN)
        _countdown_text.setPosition(0.5, 0.5)  # Center horizontally, middle position
        _countdown_text.alignment(viz.ALIGN_CENTER_TOP)
        _countdown_text.fontSize(32)
        _countdown_text.color(viz.WHITE)
    except Exception as e:
        print(f'[GameOver] Failed to create text: {e}')
        import traceback
        traceback.print_exc()
    
    # Start countdown sequence
    countdown_values = [3, 2, 1]
    
    def update_countdown(count_index):
        if count_index < len(countdown_values):
            try:
                if _countdown_text:
                    _countdown_text.message(f'Closing in {countdown_values[count_index]}...')
            except Exception:
                pass
            vizact.ontimer(1.0, update_countdown, count_index + 1)
        else:
            # Countdown finished, close window
            try:
                if _countdown_text:
                    _countdown_text.message('Closing...')
            except Exception:
                pass
            vizact.ontimer(0.5, close_window)
    
    # Start the countdown
    update_countdown(0)

def close_window():
    """Close the Vizard window (same as ESC key)."""
    print('[GameOver] Closing Vizard window...')
    viz.quit()

def is_game_over():
    """Check if game over has been triggered."""
    return _game_over_active
