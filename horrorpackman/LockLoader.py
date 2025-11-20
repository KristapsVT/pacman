import os
import math
import viz
import vizshape

# Lock asset filenames (placed in this package's `assets` folder)
_LOCK_ASSETS = ['Lock_Green.glb', 'Lock_White.glb', 'Lock_Yellow.glb']

# Vertical offset to sit above the floor to avoid z-fighting
LOCK_Y = 0.15

DEFAULT_CELL_SIZE = 3.0


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


def _load_lock_model(filename, desired_size=None, scale_factor=1.0, tint=None, fallback_color=(0.95,0.85,0.2)):
    """Load a lock GLB from package assets. Returns a group wrapper. Falls back to a primitive sphere if missing."""
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
            # If desired_size provided, compute bounding and rescale to match world size
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
            _center_glb_local_in_wrapper(raw, center_blend=0.6, desired_bottom=0.0)
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
        node = vizshape.addBox([0.6, 0.6, 0.2])
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


def spawn_locks_in_green_cells(parent=None, map_root=None, attach_to_map=True, grid_path=None, cell_size=DEFAULT_CELL_SIZE, gap=0.1):
    """Find the green tiles (🟩) in `Map_Grid.txt` and spawn 3 lock models centered inside the combined area of the first two green cells.

    - Places the three locks next to each other along the X axis (world/local depending on attach_to_map) with the provided `gap` between them.
    - Returns (group, [nodes]) where nodes is a list of the spawned viz nodes.
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

    # find green cells
    green_positions = []  # list of (r, c)
    for r in range(rows):
        row = grid[r]
        for c in range(cols):
            ch = row[c] if c < len(row) else None
            if ch == '🟩':
                green_positions.append((r, c))

    if not green_positions:
        print('[LockLoader] No green tiles found in grid')
        return None, []

    # use the first two green cells (user indicated there are two)
    cells = green_positions[:2]

    # compute local/world centers using same origin math as KeyLoader
    rows = len(grid)
    cols = max(len(r) for r in grid)
    grid_width = cols * cell_size
    grid_depth = rows * cell_size

    use_local = False
    if attach_to_map and map_root is not None and hasattr(map_root, '_pacmap_center'):
        local_origin_x = - (grid_width / 2.0) + (cell_size / 2.0)
        local_origin_z = - (grid_depth / 2.0) + (cell_size / 2.0)
        use_local = True
    else:
        # world-space origin (map center fallback to 0,0)
        if map_root is not None and hasattr(map_root, '_pacmap_center'):
            center_x, center_z = map_root._pacmap_center
        else:
            center_x, center_z = (0.0, 0.0)
        origin_x = center_x - (grid_width / 2.0) + (cell_size / 2.0)
        origin_z = center_z - (grid_depth / 2.0) + (cell_size / 2.0)

    centers = []
    for (r, c) in cells:
        grid_r = (rows - 1 - r)
        if use_local:
            lx = local_origin_x + (c * cell_size)
            lz = local_origin_z + (grid_r * cell_size)
            centers.append((lx, LOCK_Y, lz))
        else:
            wx = origin_x + (c * cell_size)
            wz = origin_z + (grid_r * cell_size)
            centers.append((wx, LOCK_Y, wz))

    # compute combined bounding box of the two cells (centers are cell centers)
    min_x = min(c[0] - (cell_size/2.0) for c in centers)
    max_x = max(c[0] + (cell_size/2.0) for c in centers)
    min_z = min(c[2] - (cell_size/2.0) for c in centers)
    max_z = max(c[2] + (cell_size/2.0) for c in centers)

    combined_width = max_x - min_x
    combined_depth = max_z - min_z

    # decide lock visual size so three locks fit with gaps
    # available horizontal space = combined_width - 2*margin (small margin to avoid touching walls)
    margin = 0.05
    avail = max(0.0, combined_width - 2.0 * margin - 2.0 * gap)
    desired_lock_size = max(0.1, min(1.0, avail / 3.0))

    # compute X offsets for three locks centered in combined area
    center_x = (min_x + max_x) / 2.0
    center_z = (min_z + max_z) / 2.0

    total_locks_width = 3.0 * desired_lock_size + 2.0 * gap
    start_x = center_x - (total_locks_width / 2.0) + (desired_lock_size / 2.0)

    positions = []
    for i in range(3):
        x = start_x + i * (desired_lock_size + gap)
        y = LOCK_Y
        z = center_z
        positions.append((x, y, z))

    # parent group
    if attach_to_map and map_root is not None:
        group = map_root
    else:
        group = parent if parent is not None else viz.addGroup()

    spawned = []

    for idx, pos in enumerate(positions):
        asset_filename = _LOCK_ASSETS[idx % len(_LOCK_ASSETS)] if _LOCK_ASSETS else None
        if asset_filename:
            node = _load_lock_model(asset_filename, desired_size=desired_lock_size)
        else:
            node = vizshape.addBox([desired_lock_size, desired_lock_size, desired_lock_size * 0.4])
            try:
                node.color(0.9, 0.7, 0.2)
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
            node.setPosition(pos)
        except Exception:
            pass
        spawned.append(node)
        try:
            print('[LockLoader] Spawned lock', idx, 'at', pos, 'using', asset_filename)
        except Exception:
            pass

    return group, spawned


if __name__ == '__main__':
    # Quick static test: compute placements and print them without requiring Vizard window interaction
    p = _default_grid_path()
    try:
        g, locks = spawn_locks_in_green_cells(grid_path=p, attach_to_map=False)
        print('Spawned', len(locks), 'locks under group', g)
    except Exception as e:
        print('LockLoader quick test failed:', e)
