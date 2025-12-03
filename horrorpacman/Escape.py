import os
import math
import viz
import vizshape
import vizact

LOCK_CELL = '🟩'

def _default_grid_path():
    return os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'Map_Grid.txt'))

def _read_grid(grid_path):
    with open(grid_path, 'r', encoding='utf-8') as f:
        raw = [ln.rstrip('\n') for ln in f.readlines() if ln.strip()]
    grid = [list(line) for line in raw]
    return grid


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


def _load_escape_model(filename, scale_factor=1.0, tint=None, fallback_color=(0.9, 0.9, 0.9), center_blend=0.6, desired_bottom=0.0, desired_size=None):
    asset_path = os.path.normpath(os.path.join(os.path.dirname(__file__), 'assets', filename))
    if os.path.exists(asset_path):
        try:
            wrapper = viz.addGroup()
            raw = viz.addChild(asset_path)
            raw.setParent(wrapper)
            try:
                raw.setScale([scale_factor] * 3)
            except Exception:
                pass
            if desired_size is not None:
                try:
                    minX, minY, minZ, maxX, maxY, maxZ = raw.getBoundingBox()
                    cur_w = maxX - minX
                    cur_d = maxZ - minZ
                    cur_max = max(cur_w, cur_d)
                    if cur_max > 0:
                        extra_scale = float(desired_size) / float(cur_max)
                        raw.setScale([scale_factor * extra_scale] * 3)
                except Exception:
                    pass
            _center_glb_local_in_wrapper(raw, center_blend=center_blend, desired_bottom=desired_bottom)
            try:
                if tint is not None:
                    wrapper.color(*tint)
            except Exception:
                pass
            try:
                wrapper._is_escape = True
            except Exception:
                pass
            return wrapper
        except Exception as e:
            print('[Escape] Model load error for', asset_path, ':', e)

    g = viz.addGroup()
    try:
        node = vizshape.addBox([1.0, 0.2, 1.0])
        try:
            node.color(*fallback_color)
        except Exception:
            pass
        node.setParent(g)
    except Exception:
        pass
    try:
        g.setScale([scale_factor] * 3)
    except Exception:
        pass
    if tint is not None:
        try:
            g.color(*tint)
        except Exception:
            pass
    try:
        g._is_escape = True
    except Exception:
        pass
    return g


_node = None
_map_root = None
_player = None
_cell_size = 3.0
_unlocked = False
_locks_total = None
_locks_remaining = None
_restart_cb = None
_spawn_offset = (4.0, 0.1, -2.7)
_sank = False
_black_override_applied = False
_activation_pos = None


def _count_locks(map_root):
    if map_root is None:
        return 0
    count = 0
    try:
        stack = [map_root]
        while stack:
            n = stack.pop()
            try:
                if getattr(n, '_is_lock', False):
                    count += 1
            except Exception:
                pass
            try:
                children = n.getChildren()
            except Exception:
                children = []
            if children:
                for c in children:
                    stack.append(c)
    except Exception:
        pass
    return count


def spawn_escape(map_root=None, attach_to_map=True, grid_path=None, cell_size=3.0, spawn_offset=None):
    global _node, _map_root, _cell_size
    _map_root = map_root
    _cell_size = float(cell_size or 3.0)
    global _spawn_offset
    if spawn_offset is not None:
        try:
            ox, oy, oz = float(spawn_offset[0]), float(spawn_offset[1]), float(spawn_offset[2])
            _spawn_offset = (ox, oy, oz)
        except Exception:
            pass
    else:
        try:
            ox = float(os.environ.get('ESCAPE_OFFSET_X', _spawn_offset[0]))
            oy = float(os.environ.get('ESCAPE_OFFSET_Y', _spawn_offset[1]))
            oz = float(os.environ.get('ESCAPE_OFFSET_Z', _spawn_offset[2]))
            _spawn_offset = (ox, oy, oz)
        except Exception:
            pass
    if grid_path is None:
        grid_path = _default_grid_path()
    if not os.path.exists(grid_path):
        print('[Escape] Grid file not found:', grid_path)
        return None
    grid = _read_grid(grid_path)
    if not grid:
        print('[Escape] Empty grid')
        return None

    rows = len(grid)
    cols = max(len(r) for r in grid)

    found = None
    for r in range(rows - 1):
        for c in range(cols):
            a = grid[r][c] if c < len(grid[r]) else None
            b = grid[r+1][c] if c < len(grid[r+1]) else None
            if a == LOCK_CELL and b == LOCK_CELL:
                found = (r, r+1, c)
                break
        if found:
            break

    if not found:
        print('[Escape] No vertical 🟩 pair found in grid')
        return None

    r_top, r_bottom, c = found

    if map_root is not None and hasattr(map_root, '_pacmap_center'):
        center_x, center_z = map_root._pacmap_center
    else:
        center_x, center_z = (0.0, 0.0)

    grid_width = cols * _cell_size
    grid_depth = rows * _cell_size

    if attach_to_map and map_root is not None and hasattr(map_root, '_pacmap_center'):
        origin_x = - (grid_width / 2.0) + (_cell_size / 2.0)
        origin_z = - (grid_depth / 2.0) + (_cell_size / 2.0)
        use_local = True
    else:
        origin_x = center_x - (grid_width / 2.0) + (_cell_size / 2.0)
        origin_z = center_z - (grid_depth / 2.0) + (_cell_size / 2.0)
        use_local = False

    grid_r_top = (rows - 1 - r_top)
    grid_r_bot = (rows - 1 - r_bottom)
    if use_local:
        top_pos = [origin_x + (c * _cell_size), 0.0, origin_z + (grid_r_top * _cell_size)]
        bot_pos = [origin_x + (c * _cell_size), 0.0, origin_z + (grid_r_bot * _cell_size)]
    else:
        top_pos = [origin_x + (c * _cell_size), 0.0, origin_z + (grid_r_top * _cell_size)]
        bot_pos = [origin_x + (c * _cell_size), 0.0, origin_z + (grid_r_bot * _cell_size)]

    mid = [(top_pos[0] + bot_pos[0]) * 0.5,
           (top_pos[1] + bot_pos[1]) * 0.5,
           (top_pos[2] + bot_pos[2]) * 0.5]

    desired_size = _cell_size * 0.9
    node = _load_escape_model('Escape.glb', scale_factor=1.0, tint=None, fallback_color=(0.8,0.8,0.8), desired_bottom=0.0, desired_size=desired_size)
    try:
        if attach_to_map and map_root is not None:
            node.setParent(map_root)
        else:
            node.setParent(viz.addGroup())
    except Exception:
        pass
    try:
        global _activation_pos
        _activation_pos = tuple(mid)

        ox, oy, oz = _spawn_offset
        spawn_pos = (mid[0] + ox, mid[1] + oy, mid[2] + oz)
        node.setPosition(spawn_pos)
        try:
            print('[Escape] Spawned at grid top/bottom rows %s/%s col %s -> mid=%s offset=%s pos=%s' % (
                r_top, r_bottom, c, str(mid), str(_spawn_offset), str(spawn_pos)
            ))
        except Exception:
            pass
    except Exception:
        pass

    try:
        node.disable(viz.LIGHTING)
    except Exception:
        pass

    try:
        node._is_escape = True
    except Exception:
        pass

    _node = node
    try:
        global _locks_total, _locks_remaining
        _locks_total = _count_locks(map_root)
        _locks_remaining = _locks_total
    except Exception:
        _locks_total = None
        _locks_remaining = None

    return node


def init(player, map_root=None, cell_size=3.0, restart_callback=None):
    global _player, _restart_cb
    _player = player
    _restart_cb = restart_callback
    spawn_escape(map_root=map_root, attach_to_map=True, cell_size=cell_size)

    try:
        vizact.onkeydown('l', lambda: _try_activate())
    except Exception:
        try:
            vizact.onkeydown('L', lambda: _try_activate())
        except Exception:
            pass

    try:
        vizact.ontimer(0, _update)
    except Exception:
        try:
            vizact.ontimer(1/30.0, _update)
        except Exception:
            pass


def _try_activate():
    global _unlocked, _node, _player, _restart_cb, _map_root
    if not _unlocked or _node is None or _player is None:
        return False
    try:
        px, py, pz = _player.getPosition()
        if _activation_pos is not None:
            ex, ey, ez = _activation_pos
        else:
            ex, ey, ez = _node.getPosition()
    except Exception:
        return False
    try:
        thresh = (_cell_size * 0.6)
    except Exception:
        thresh = 1.8
    dx = px - ex
    dz = pz - ez
    if (dx*dx + dz*dz) <= (thresh * thresh):
        try:
            try:
                _player.setPosition((0.0, -150.0, 0.0))
            except Exception:
                try:
                    _player.setPosition(0.0, -150.0, 0.0)
                except Exception:
                    pass

            try:
                game_node = _load_escape_model('Game_Over.glb', scale_factor=1.0, tint=None, fallback_color=(0.0,0.0,0.0), desired_bottom=0.0, desired_size=_cell_size * 0.9)
                if game_node is not None:
                    try:
                        if _map_root is not None:
                            game_node.setParent(_map_root)
                        else:
                            game_node.setParent(viz.addGroup())
                    except Exception:
                        pass
                    try:
                        game_node.setPosition((25.0, -148.0, 4.0))
                    except Exception:
                        pass
                    try:
                        game_node.disable(viz.LIGHTING)
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                try:
                    import Player as _P
                    yaw_target = 90.0
                    try:
                        _P.cam_yaw = yaw_target
                    except Exception:
                        pass
                    try:
                        _P.player_yaw = yaw_target
                    except Exception:
                        pass
                except Exception:
                    yaw_target = 90.0
                try:
                    _player.setEuler([yaw_target, 0, 0])
                except Exception:
                    pass
                try:
                    import Player as _P2
                    try:
                        _P2.CONTROLS_LOCKED = True
                    except Exception:
                        pass
                    try:
                        _P2.cam_pitch = 0.0
                    except Exception:
                        pass
                except Exception:
                    pass
            except Exception:
                pass

            return True
        except Exception:
            return False
    return False


def on_unlock(color, node):
    global _locks_remaining, _unlocked
    try:
        _locks_remaining = _count_locks(_map_root)
    except Exception:
        try:
            if _locks_remaining is not None:
                _locks_remaining = max(0, _locks_remaining - 1)
        except Exception:
            _locks_remaining = None

    if _locks_remaining == 0:
        _unlocked = True
        try:
            global _sank, _black_override_applied
            _sank = False
            _black_override_applied = False
        except Exception:
            pass


def set_spawn_offset(offset):
    global _spawn_offset, _node
    try:
        ox, oy, oz = float(offset[0]), float(offset[1]), float(offset[2])
    except Exception:
        try:
            parts = str(offset).split(',')
            ox, oy, oz = float(parts[0]), float(parts[1]), float(parts[2])
        except Exception:
            return False
    try:
        prev = _spawn_offset
        dx, dy, dz = (ox - prev[0], oy - prev[1], oz - prev[2])
    except Exception:
        dx = dy = dz = 0.0
    _spawn_offset = (ox, oy, oz)
    if _node is not None:
        try:
            x, y, z = _node.getPosition()
            _node.setPosition((x + dx, y + dy, z + dz))
            try:
                print('[Escape] spawn offset set to', _spawn_offset, 'node moved by', (dx, dy, dz))
            except Exception:
                pass
        except Exception:
            pass
    return True


def _style_locked():
    global _node
    if _node is None:
        return
    try:
        _node.disable(viz.LIGHTING)
    except Exception:
        pass
    try:
        _node.color(0.9, 0.9, 0.9)
    except Exception:
        pass


def _style_unlocked():
    global _node
    if _node is None:
        return
    try:
        try:
            _node.color(0.0, 0.0, 0.0, 1.0)
        except Exception:
            try:
                _node.color(0.0, 0.0, 0.0)
            except Exception:
                pass

        try:
            stack = [_node]
            while stack:
                cur = stack.pop()
                try:
                    try:
                        cur.disable(viz.LIGHTING)
                    except Exception:
                        pass
                    try:
                        cur.color(0.0, 0.0, 0.0)
                    except Exception:
                        pass
                    if hasattr(cur, 'texture'):
                        try:
                            cur.texture(None)
                        except Exception:
                            pass
                    if hasattr(cur, 'setTexture'):
                        try:
                            cur.setTexture(None)
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    children = cur.getChildren()
                except Exception:
                    children = []
                for c in children:
                    stack.append(c)
        except Exception:
            pass
    except Exception:
        pass


def _try_remove_node(node):
    try:
        node.remove()
        return True
    except Exception:
        pass
    try:
        viz.remove(node)
        return True
    except Exception:
        pass
    try:
        node.visible(False)
        try:
            node.setParent(None)
        except Exception:
            pass
        return True
    except Exception:
        pass
    return False


def _replace_with_unlocked_model():
    global _node
    if _node is None:
        return False
    try:
        try:
            parent = _node.getParent()
        except Exception:
            parent = None
        try:
            pos = _node.getPosition()
        except Exception:
            pos = None
        try:
            euler = _node.getEuler()
        except Exception:
            euler = None
        try:
            scale = _node.getScale()
        except Exception:
            scale = None

        _try_remove_node(_node)

        new_node = _load_escape_model('Escape_Unlocked.glb', scale_factor=1.0, tint=None, fallback_color=(0.0,0.0,0.0), desired_bottom=0.0, desired_size=_cell_size * 0.9)
        if new_node is None:
            return False

        try:
            if parent is not None:
                new_node.setParent(parent)
            else:
                if _map_root is not None:
                    new_node.setParent(_map_root)
                else:
                    new_node.setParent(viz.addGroup())
        except Exception:
            pass

        try:
            if pos is not None:
                new_node.setPosition(pos)
            else:
                if _activation_pos is not None:
                    ox, oy, oz = _spawn_offset
                    new_node.setPosition((_activation_pos[0] + ox, _activation_pos[1] + oy, _activation_pos[2] + oz))
        except Exception:
            pass

        try:
            if scale is not None:
                new_node.setScale(scale)
        except Exception:
            pass
        try:
            if euler is not None:
                new_node.setEuler(euler)
        except Exception:
            pass

        try:
            new_node._is_escape = True
        except Exception:
            pass

        _node = new_node
        return True
    except Exception:
        return False


def _update():
    global _unlocked, _node
    if _node is None:
        return
    try:
        if _unlocked:
            global _sank, _black_override_applied
            if not _black_override_applied:
                replaced = False
                try:
                    replaced = _replace_with_unlocked_model()
                except Exception:
                    replaced = False
                if not replaced:
                    try:
                        _style_unlocked()
                    except Exception:
                        pass
                _black_override_applied = True

            if not _sank:
                try:
                    x, y, z = _node.getPosition()
                    _node.setPosition((x, y - 0.02, z))
                except Exception:
                    pass
                _sank = True
        else:
            _style_locked()
    except Exception:
        pass
