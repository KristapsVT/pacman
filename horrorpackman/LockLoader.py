import os
import math
import viz
import vizshape

# Emoji markers in Map_Grid.txt
WALL_EMOJI = '🟧'   # wall cell where locks should attach to (left of the lock cell)
LOCK_CELL = '🟩'    # cell where lock sits (inside this cell)

# Asset filenames (in package assets folder)
_LOCK_ASSETS = ['Lock_Green.glb', 'Lock_White.glb', 'Lock_Yellow.glb']

def _default_grid_path():
    return os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'Map_Grid.txt'))

def _read_grid(grid_path):
    with open(grid_path, 'r', encoding='utf-8') as f:
        raw = [ln.rstrip('\n') for ln in f.readlines() if ln.strip()]
    grid = [list(line) for line in raw]
    return grid

def _center_glb_local_in_wrapper(raw, center_blend=0.6, desired_bottom=0.0):
    # reuse centering heuristic similar to KeyLoader
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

def _load_lock_model(filename, scale_factor=1.0, tint=None, fallback_color=(0.9, 0.9, 0.9), center_blend=0.6, desired_bottom=0.0, desired_size=None):
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
            if tint is not None:
                try:
                    wrapper.color(*tint)
                except Exception:
                    pass
            return wrapper
        except Exception as e:
            print('[LockLoader] Model load error for', asset_path, ':', e)

    # Fallback primitive: small cylinder to resemble a lock
    g = viz.addGroup()
    try:
        radius = 0.25
        height = 0.35
        if desired_size is not None and desired_size > 0:
            radius = desired_size * 0.25
            height = desired_size * 0.35
        node = vizshape.addCylinder(height=height, radius=radius)
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
    return g


def spawn_locks_on_map(map_root=None, attach_to_map=True, grid_path=None, cell_size=3.0, visualize=True, spacing=0.65):
    """Spawn three locks according to Map_Grid.txt pattern.

    Placement rule (per request):
    - Find `🟩` cells that have a `🟧` directly to their left. We expect two such rows stacked vertically.
    - Place the white lock in the top `🟩`, the green lock in the bottom `🟩`, and the yellow lock midway between them.
    - Locks sit inside the `🟩` cell but are offset slightly toward the left (`🟧`) to appear attached to the wall.

    Args:
        spacing: float in (0..1+] that scales the vertical separation between the top and bottom lock positions
                 relative to their midpoint. Values <1 bring locks closer together (default 0.65). Values 1 leave
                 the original positions unchanged.

    Returns: (group, dict) where dict contains keys: 'green','white','yellow' mapping to spawned viz nodes (or None).
    """
    if grid_path is None:
        grid_path = _default_grid_path()
    if not os.path.exists(grid_path):
        raise FileNotFoundError('Grid file not found: %s' % grid_path)

    grid = _read_grid(grid_path)
    if not grid:
        return None, {}

    rows = len(grid)
    cols = max(len(r) for r in grid)

    # Determine map center and origin consistent with KeyLoader logic
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
        group = viz.addGroup()

    # collect candidate lock cells: list of tuples (r, c, pos)
    candidates = []
    for r in range(rows):
        row = grid[r]
        for c in range(cols):
            ch = row[c] if c < len(row) else None
            if ch != LOCK_CELL:
                continue
            # check left neighbor exists and is wall emoji
            left = row[c-1] if c-1 >= 0 and c-1 < len(row) else None
            if left != WALL_EMOJI:
                continue
            grid_r = (rows - 1 - r)
            if use_local:
                lx = local_origin_x + (c * cell_size)
                lz = local_origin_z + (grid_r * cell_size)
                pos = [lx, 0.0, lz]
            else:
                wx = origin_x + (c * cell_size)
                wz = origin_z + (grid_r * cell_size)
                pos = [wx, 0.0, wz]
            candidates.append((r, c, pos))

    if not candidates:
        print('[LockLoader] No suitable 🟩 cells with left 🟧 found')
        return group, {'green': None, 'white': None, 'yellow': None}

    # Prefer candidates in the same column (c) and pick the pair with largest vertical separation
    by_col = {}
    for r, c, pos in candidates:
        by_col.setdefault(c, []).append((r, pos))

    chosen_pair = None
    chosen_col = None
    best_span = -1
    for c, items in by_col.items():
        if len(items) < 2:
            continue
        rs = sorted(items, key=lambda x: x[0])
        span = rs[-1][0] - rs[0][0]
        if span > best_span:
            best_span = span
            chosen_pair = (rs[0], rs[-1])
            chosen_col = c

    if chosen_pair is None:
        # fallback: pick top-most and bottom-most candidates overall
        all_sorted = sorted(candidates, key=lambda x: x[0])
        if len(all_sorted) >= 2:
            top = all_sorted[0]
            bottom = all_sorted[-1]
            chosen_pair = ((top[0], top[2]), (bottom[0], bottom[2]))
        else:
            # only one candidate: duplicate it and place midpoint equal to it
            only = candidates[0]
            chosen_pair = ((only[0], only[2]), (only[0], only[2]))

    # chosen_pair are tuples like (r, pos)
    top_r, top_pos = chosen_pair[0]
    bottom_r, bottom_pos = chosen_pair[1]

    # compute middle position
    mid_pos = [(top_pos[0] + bottom_pos[0]) * 0.5,
               (top_pos[1] + bottom_pos[1]) * 0.5,
               (top_pos[2] + bottom_pos[2]) * 0.5]

    # Optionally compress the vertical separation so locks appear closer together on the wall.
    try:
        s = float(spacing)
        if s < 0.0:
            s = 0.0
    except Exception:
        s = 1.0

    if s != 1.0:
        # vector from midpoint to top/bottom
        vtop = [top_pos[i] - mid_pos[i] for i in range(3)]
        vbot = [bottom_pos[i] - mid_pos[i] for i in range(3)]
        # scale vectors by spacing and recompute positions
        top_pos = [mid_pos[i] + vtop[i] * s for i in range(3)]
        bottom_pos = [mid_pos[i] + vbot[i] * s for i in range(3)]
        # recompute midpoint for later yellow placement
        mid_pos = [(top_pos[0] + bottom_pos[0]) * 0.5,
                   (top_pos[1] + bottom_pos[1]) * 0.5,
                   (top_pos[2] + bottom_pos[2]) * 0.5]

    # offset toward wall (left side): move negative X by ~40% of cell_size
    attach_offset = (-cell_size * 0.40, 0.0, 0.0)

    # spawn helper
    def _spawn_asset(kind, filename, world_pos, offset, desired_size=0.9, fallback=None):
        if fallback is None:
            if 'Green' in filename:
                fallback = (0.2, 0.9, 0.2)
            elif 'White' in filename:
                fallback = (0.95, 0.95, 0.95)
            elif 'Yellow' in filename:
                fallback = (1.0, 0.9, 0.2)
            else:
                fallback = (0.9, 0.9, 0.9)

        node = _load_lock_model(filename, scale_factor=1.0, tint=None, fallback_color=fallback, center_blend=0.6, desired_bottom=0.0, desired_size=desired_size)
        try:
            if attach_to_map and map_root is not None:
                node.setParent(map_root)
            else:
                node.setParent(group)
        except Exception:
            pass
        try:
            node.setPosition((world_pos[0] + offset[0], world_pos[1] + offset[1], world_pos[2] + offset[2]))
        except Exception:
            pass
        try:
            node._is_lock = True
        except Exception:
            pass
        return node

    # Spawn green in bottom, white in top, yellow in middle
    spawned = {'green': None, 'white': None, 'yellow': None}
    try:
        spawned['green'] = _spawn_asset('green', _LOCK_ASSETS[0], bottom_pos, attach_offset)
    except Exception:
        spawned['green'] = None
    try:
        # white asset tends to be large in some exports; request a smaller desired_size
        spawned['white'] = _spawn_asset('white', _LOCK_ASSETS[1], top_pos, attach_offset, desired_size=0.5)
    except Exception:
        spawned['white'] = None
    try:
        spawned['yellow'] = _spawn_asset('yellow', _LOCK_ASSETS[2], mid_pos, attach_offset)
    except Exception:
        spawned['yellow'] = None

    # Apply styling similar to pacmap: disable lighting and assign sensible colors/scales
    try:
        def _style_locks(spawned_dict):
            if not spawned_dict:
                return
            for key, node in spawned_dict.items():
                if not node:
                    continue
                try:
                    node.disable(viz.LIGHTING)
                except Exception:
                    pass
                try:
                    if key == 'green':
                        node.color(0.2, 0.9, 0.2)
                    elif key == 'white':
                        node.color(0.95, 0.95, 0.95)
                        # additionally scale down white lock wrappers which can be huge
                        try:
                            node.setScale([0.5, 0.5, 0.5])
                        except Exception:
                            pass
                    elif key == 'yellow':
                        node.color(1.0, 0.9, 0.2)
                    else:
                        try:
                            node.color(0.9, 0.9, 0.9)
                        except Exception:
                            pass
                except Exception:
                    pass

        _style_locks(spawned)
    except Exception:
        pass

    return group, spawned


if __name__ == '__main__':
    p = _default_grid_path()
    print('Using grid:', p)
    g = _read_grid(p)
    print('Grid size rows=%d cols=%d' % (len(g), max(len(r) for r in g)))
