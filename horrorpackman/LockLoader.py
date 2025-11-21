import os
import random
import math
import viz
import vizshape

CELL_LOCK = '🟩'  # green tile marker where locks should appear
CELL_WALL = '🟧'  # orange wall marker used as adjacency reference
DEFAULT_CELL_SIZE = 3.0
LOCK_Y = 1.0

_LOCK_ASSETS = ['Lock_Green.glb', 'Lock_White.glb', 'Lock_Yellow.glb']


def _default_grid_path():
    return os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'Map_Grid.txt'))


def _read_grid(grid_path):
    with open(grid_path, 'r', encoding='utf-8') as f:
        raw = [ln.rstrip('\n') for ln in f.readlines() if ln.strip()]
    return [list(line) for line in raw]


def _load_lock_model(filename, scale_factor=1.0, tint=None, fallback_color=(0.9,0.9,0.9), desired_bottom=0.0, desired_size=None):
    asset_path = os.path.normpath(os.path.join(os.path.dirname(__file__), 'assets', filename))
    if os.path.exists(asset_path):
        try:
            wrapper = viz.addGroup()
            raw = viz.addChild(asset_path)
            raw.setParent(wrapper)
            try:
                raw.setScale([scale_factor]*3)
            except Exception:
                pass
            # attempt to center like other loaders; best-effort
            try:
                minX, minY, minZ, maxX, maxY, maxZ = raw.getBoundingBox()
                cx = (minX + maxX) * 0.5
                cz = (minZ + maxZ) * 0.5
                liftY = float(desired_bottom) - minY
                raw.setPosition([-cx, liftY, -cz])
            except Exception:
                try:
                    raw.setPosition([0, desired_bottom, 0])
                except Exception:
                    pass
            if tint is not None:
                try:
                    wrapper.color(*tint)
                except Exception:
                    pass
            return wrapper
        except Exception as e:
            print('[LockLoader] Model load error for', asset_path, ':', e)

    # fallback primitive
    g = viz.addGroup()
    try:
        node = vizshape.addSphere(radius=0.25)
        try:
            node.color(*fallback_color)
        except Exception:
            pass
        node.setParent(g)
    except Exception:
        pass
    try:
        g.setScale([scale_factor]*3)
    except Exception:
        pass
    if tint is not None:
        try:
            g.color(*tint)
        except Exception:
            pass
    return g


def spawn_locks_on_map(parent=None, map_root=None, attach_to_map=True, grid_path=None, cell_size=DEFAULT_CELL_SIZE, lock_offset=(0.0, 0.0, 0.0), num_locks=3):
    """Spawn lock nodes on `🟩` tiles, positioned against adjacent `🟧` wall tiles.

    - parent/map_root/attach_to_map behave like `KeyLoader.spawn_keys_on_map()`.
    - Each lock is placed inside the green cell but nudged toward the adjacent orange wall.
    - Cycles through `_LOCK_ASSETS` for variety.
    """
    if grid_path is None:
        grid_path = _default_grid_path()

    if not os.path.exists(grid_path):
        raise FileNotFoundError('Grid file not found: %s' % grid_path)

    grid = _read_grid(grid_path)
    if not grid:
        return None, []

    rows = len(grid)
    cols = max(len(r) for r in grid)

    # Determine map center (if map_root provides it)
    if map_root is not None and hasattr(map_root, '_pacmap_center'):
        center_x, center_z = map_root._pacmap_center
    else:
        center_x, center_z = (0.0, 0.0)

    grid_width = cols * cell_size
    grid_depth = rows * cell_size

    if attach_to_map and map_root is not None and hasattr(map_root, '_pacmap_center'):
        local_origin_x = - (grid_width / 2.0) + (cell_size / 2.0)
        local_origin_z = - (grid_depth / 2.0) + (cell_size / 2.0)
        use_local = True
    else:
        origin_x = center_x - (grid_width / 2.0) + (cell_size / 2.0)
        origin_z = center_z - (grid_depth / 2.0) + (cell_size / 2.0)
        use_local = False

    if attach_to_map and map_root is not None:
        group = map_root
    else:
        group = parent if parent is not None else viz.addGroup()

    spawned = []
    try:
        ox, oy, oz = (float(lock_offset[0]), float(lock_offset[1]), float(lock_offset[2]))
    except Exception:
        ox, oy, oz = (0.0, 0.0, 0.0)

    margin = max(0.2, cell_size * 0.12)  # how close to the wall the lock should be
    EXTRA_PULL = max(0.25, margin * 1.0)  # when rotation causes protrusion, pull back this amount from the wall

    # First, gather candidate positions: for each green cell, prefer positions nudged toward adjacent orange walls
    candidates = []
    green_cells = []
    for r in range(rows):
        row = grid[r]
        for c in range(cols):
            ch = row[c] if c < len(row) else None
            if ch != CELL_LOCK:
                continue
            grid_r = (rows - 1 - r)
            if use_local:
                lx = local_origin_x + (c * cell_size)
                lz = local_origin_z + (grid_r * cell_size)
            else:
                wx = origin_x + (c * cell_size)
                wz = origin_z + (grid_r * cell_size)
                lx = wx; lz = wz
            green_cells.append((r, c, lx, lz))

    # If exactly two green cells, place locks as requested: white on top, green on bottom, yellow between
    if len(green_cells) == 2:
        # sort by file-row index r (smaller r is visually top)
        sorted_gc = sorted(green_cells, key=lambda x: x[0])
        top = sorted_gc[0]
        bottom = sorted_gc[1]
        r_top, c_top, lx_top, lz_top = top
        r_bot, c_bot, lx_bot, lz_bot = bottom

        # helper to find adjacent wall direction for a given green cell
        def _adj_dir_for(rc_r, rc_c):
            # returns (dx, dz) where dx/dz in {-1,0,1}
            # left
            try:
                if rc_c - 1 >= 0 and (grid[rc_r][rc_c-1] if rc_c-1 < len(grid[rc_r]) else None) == CELL_WALL:
                    return (-1, 0)
            except Exception:
                pass
            # right
            try:
                if rc_c + 1 < cols and (grid[rc_r][rc_c+1] if rc_c+1 < len(grid[rc_r]) else None) == CELL_WALL:
                    return (1, 0)
            except Exception:
                pass
            # up
            try:
                if rc_r - 1 >= 0 and (grid[rc_r-1][rc_c] if rc_c < len(grid[rc_r-1]) else None) == CELL_WALL:
                    return (0, 1)
            except Exception:
                pass
            # down
            try:
                if rc_r + 1 < rows and (grid[rc_r+1][rc_c] if rc_c < len(grid[rc_r+1]) else None) == CELL_WALL:
                    return (0, -1)
            except Exception:
                pass
            return (0, 0)

        adj_top = _adj_dir_for(r_top, c_top)
        adj_bot = _adj_dir_for(r_bot, c_bot)

        push = (cell_size / 2.0) - margin

        # Yellow between both: midpoint
        mid_x = (lx_top + lx_bot) * 0.5 + ox
        mid_z = (lz_top + lz_bot) * 0.5 + oz

        # Top (white) - nudge toward its adjacent wall if present, but never beyond cell edge
        if adj_top != (0, 0):
            # place toward wall, then pull back slightly to avoid rotated geometry clipping into wall
            place_top_x = lx_top + (adj_top[0] * push) - (adj_top[0] * EXTRA_PULL) + ox
            place_top_z = lz_top + (adj_top[1] * push) - (adj_top[1] * EXTRA_PULL) + oz
        else:
            place_top_x = lx_top + ox
            place_top_z = lz_top + oz

        # Bottom (green) - nudge toward its adjacent wall if present, but never beyond cell edge
        if adj_bot != (0, 0):
            # place toward wall, then pull back slightly to avoid rotated geometry clipping into wall
            place_bot_x = lx_bot + (adj_bot[0] * push) - (adj_bot[0] * EXTRA_PULL) + ox
            place_bot_z = lz_bot + (adj_bot[1] * push) - (adj_bot[1] * EXTRA_PULL) + oz
        else:
            place_bot_x = lx_bot + ox
            place_bot_z = lz_bot + oz

        # Clamp top/bottom to remain inside their cell bounds (not inside wall)
        half = cell_size / 2.0
        min_x_top = lx_top - half + margin
        max_x_top = lx_top + half - margin
        min_z_top = lz_top - half + margin
        max_z_top = lz_top + half - margin
        place_top_x = max(min_x_top, min(max_x_top, place_top_x))
        place_top_z = max(min_z_top, min(max_z_top, place_top_z))

        min_x_bot = lx_bot - half + margin
        max_x_bot = lx_bot + half - margin
        min_z_bot = lz_bot - half + margin
        max_z_bot = lz_bot + half - margin
        place_bot_x = max(min_x_bot, min(max_x_bot, place_bot_x))
        place_bot_z = max(min_z_bot, min(max_z_bot, place_bot_z))

        # Align top/bottom so they share a common line with the midpoint (collinear)
        # Prefer exact grid alignment using column/row indices
        if c_top == c_bot:
            # same column -> align X to midpoint
            place_top_x = mid_x
            place_bot_x = mid_x
        elif r_top == r_bot:
            # same row -> align Z to midpoint
            place_top_z = mid_z
            place_bot_z = mid_z
        else:
            # pick dominant axis of separation and align perpendicular coordinate to midpoint
            dx_sep = abs(lx_top - lx_bot)
            dz_sep = abs(lz_top - lz_bot)
            if dx_sep > dz_sep:
                place_top_z = mid_z
                place_bot_z = mid_z
            else:
                place_top_x = mid_x
                place_bot_x = mid_x

        place_top = (place_top_x, LOCK_Y + oy, place_top_z)
        place_bot = (place_bot_x, LOCK_Y + oy, place_bot_z)

        # adjust midpoint slightly toward average wall direction if both share a wall direction
        avg_dx = adj_top[0] + adj_bot[0]
        avg_dz = adj_top[1] + adj_bot[1]
        if avg_dx != 0 or avg_dz != 0:
            ndx = -1 if avg_dx < 0 else (1 if avg_dx > 0 else 0)
            ndz = -1 if avg_dz < 0 else (1 if avg_dz > 0 else 0)
            mid_x += ndx * (push * 0.5)
            mid_z += ndz * (push * 0.5)

        place_mid = (mid_x, LOCK_Y + oy, mid_z)

        # Now assign assets: white top, green bottom, yellow middle
        chosen = [place_mid, place_top, place_bot]
        asset_order = ['Lock_Yellow.glb', 'Lock_White.glb', 'Lock_Green.glb']

        for idx, pos in enumerate(chosen):
            place_x, place_y, place_z = pos
            asset_filename = asset_order[idx] if asset_order and idx < len(asset_order) else (_LOCK_ASSETS[idx % len(_LOCK_ASSETS)] if _LOCK_ASSETS else None)
            if asset_filename:
                node = _load_lock_model(asset_filename, scale_factor=1.0, tint=None, fallback_color=(0.8,0.8,0.8), desired_bottom=0.0, desired_size=0.6)
            else:
                node = vizshape.addSphere(radius=0.25)
                try:
                    node.color(0.8,0.8,0.8)
                except Exception:
                    pass

            try:
                if attach_to_map and map_root is not None:
                    node.setParent(map_root)
                else:
                    node.setParent(group)
            except Exception:
                pass
            try:
                node.setPosition((place_x, place_y, place_z))
            except Exception:
                pass
            try:
                # rotate to total 270 degrees yaw
                node.setEuler([270, 0, 0])
            except Exception:
                pass
            try:
                node._is_lock = True
            except Exception:
                pass
            try:
                node.disable(viz.LIGHTING)
            except Exception:
                pass
            spawned.append(node)
        return group, spawned

    # If not enough adjacency candidates, add centered positions inside green cells
    for (r, c, lx, lz) in green_cells:
        if len(candidates) >= num_locks:
            break
        candidates.append((lx + ox, LOCK_Y + oy, lz + oz))

    # Trim or pad candidates to exactly num_locks
    chosen = candidates[:num_locks]

    for idx, pos in enumerate(chosen):
        place_x, place_y, place_z = pos
        asset_idx = idx % len(_LOCK_ASSETS) if _LOCK_ASSETS else 0
        asset_filename = _LOCK_ASSETS[asset_idx] if _LOCK_ASSETS else None
        if asset_filename:
            node = _load_lock_model(asset_filename, scale_factor=1.0, tint=None, fallback_color=(0.8,0.8,0.8), desired_bottom=0.0, desired_size=0.6)
        else:
            node = vizshape.addSphere(radius=0.25)
            try:
                node.color(0.8,0.8,0.8)
            except Exception:
                pass

        try:
            if attach_to_map and map_root is not None:
                node.setParent(map_root)
            else:
                node.setParent(group)
        except Exception:
            pass
        try:
            node.setPosition((place_x, place_y, place_z))
        except Exception:
            pass
        try:
            # rotate 90 degrees yaw
            node.setEuler([90, 0, 0])
        except Exception:
            pass
        try:
            node._is_lock = True
        except Exception:
            pass
        try:
            node.disable(viz.LIGHTING)
        except Exception:
            pass
        spawned.append(node)

    return group, spawned


if __name__ == '__main__':
    p = _default_grid_path()
    print('Using grid:', p)
    g = _read_grid(p)
    print('Grid size rows=%d cols=%d' % (len(g), max(len(r) for r in g)))
