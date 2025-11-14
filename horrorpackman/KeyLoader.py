import os
import random

# Key spawner for Horror Pac-Man
# Places one of each key (red, yellow, white) on random 🟪 cells read from Map_Grid.txt
# Usage:
#   from KeyLoader import spawn_keys_on_map
#   spawn_keys_on_map(parent=some_group)

try:
    import viz
    import vizshape
except Exception:
    viz = None
    vizshape = None

GRID_FILE = os.path.join(os.path.dirname(__file__), '..', 'Map_Grid.txt')
# Cell world size: the user said each grid cell (🟥) is 3x3 units in world space
CELL_SIZE = 3.0
KEY_ASSETS = [
    os.path.join('assets', 'Key_Red.glb'),
    os.path.join('assets', 'Key_Yellow.glb'),
    os.path.join('assets', 'Key_White.glb')
]

def _read_grid(path=GRID_FILE):
    """Read the grid file and return list of (r,c,char) and grid dims."""
    if not os.path.exists(path):
        return [], 0, 0
    with open(path, 'r', encoding='utf-8') as f:
        lines = [ln.rstrip('\n') for ln in f.readlines() if ln.strip()]
    if not lines:
        return [], 0, 0
    # Each character in the text is an emoji cell; build matrix
    grid = [list(line) for line in lines]
    rows = len(grid)
    cols = max(len(r) for r in grid)
    return grid, rows, cols


def _find_candidate_cells(grid):
    """Return list of (r,c) positions where the cell is 🟪 (path+chance for key)."""
    cand = []
    for r, row in enumerate(grid):
        for c, ch in enumerate(row):
            if ch == '🟪':
                cand.append((r, c))
    return cand


def _find_candidate_cells_filtered(grid, avoid_symbols=None):
    """Return list of (r,c) positions where the cell is 🟪, excluding avoid_symbols."""
    if avoid_symbols is None:
        avoid_symbols = ['🟦', '🟩']
    cand = []
    for r, row in enumerate(grid):
        for c, ch in enumerate(row):
            if ch == '🟪':
                # avoid cells that are or neighbor to any avoid symbol
                skip = False
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        rr = r + dr
                        cc = c + dc
                        if 0 <= rr < len(grid) and 0 <= cc < len(grid[rr]):
                            if grid[rr][cc] in avoid_symbols:
                                skip = True
                                break
                    if skip:
                        break
                if skip:
                    continue
                cand.append((r, c))
    return cand


def _grid_to_world(r, c, rows, cols, cell_size=CELL_SIZE, left=None, top=None):
    """Map grid indices to world X,Z coordinates.

    If `left`/`top` are provided they are treated as world coordinates of the
    grid's top-left corner. Otherwise the grid is centered at origin.

    Returns (x, y, z) where y is set to 0.5 (above floor).
    """
    width = cols * cell_size
    height = rows * cell_size
    # compute top-left corner in world coords
    if left is None:
        left = -width / 2.0
    if top is None:
        top = height / 2.0
    # place at center of cell. Note: Z axis in world coords is mapped so
    # increasing row index moves toward negative Z (top->bottom maps to +Z->-Z)
    x = left + (c + 0.5) * cell_size
    z = top - (r + 0.5) * cell_size
    y = 0.5
    return x, y, z


def _compute_group_bounds(group):
    """Estimate bounding rectangle (minX, minZ, maxX, maxZ) of a Vizard group.

    Returns (minX, minZ, maxX, maxZ) or None if unable to compute.
    """
    # Try direct group bounding box (some Vizard versions expose this)
    try:
        bb = group.getBoundingBox()
        if bb:
            minX, minY, minZ, maxX, maxY, maxZ = bb
            return minX, minZ, maxX, maxZ
    except Exception:
        pass

    try:
        children = group.getChildren()
    except Exception:
        try:
            children = []
        except Exception:
            return None

    minX = float('inf'); minZ = float('inf'); maxX = float('-inf'); maxZ = float('-inf')
    any_geom = False
    for ch in children:
        try:
            bb = ch.getBoundingBox()
            if bb:
                cminX, cminY, cminZ, cmaxX, cmaxY, cmaxZ = bb
                minX = min(minX, cminX); minZ = min(minZ, cminZ)
                maxX = max(maxX, cmaxX); maxZ = max(maxZ, cmaxZ)
                any_geom = True
                continue
        except Exception:
            pass
        try:
            px, py, pz = ch.getPosition()
            minX = min(minX, px); minZ = min(minZ, pz)
            maxX = max(maxX, px); maxZ = max(maxZ, pz)
            any_geom = True
        except Exception:
            pass

    if not any_geom:
        return None
    return minX, minZ, maxX, maxZ


def _safe_load_key(path, parent=None, scale=1.0):
    """Load a key GLB; if missing, create a simple placeholder.

    Returns the node or None.
    """
    if viz is None:
        print('[KeyLoader] viz not available; cannot create keys at runtime in this environment')
        return None
    full = os.path.join(os.path.dirname(__file__), '..', path)
    try:
        if os.path.exists(full):
            node = viz.addChild(full)
            if parent is not None:
                node.setParent(parent)
            try:
                node.setScale([scale] * 3)
            except Exception:
                pass
            print('[KeyLoader] Loaded key asset:', full)
            return node
        else:
            print('[KeyLoader] Key asset missing:', full)
    except Exception as e:
        print('[KeyLoader] Error loading key', full, e)
    # fallback placeholder
    if vizshape:
        ph = vizshape.addSphere(radius=0.25)
        ph.color(1, 1, 0)
        if parent is not None:
            ph.setParent(parent)
        print('[KeyLoader] Placed placeholder key')
        return ph
    return None


def spawn_keys_on_map(parent=None, grid_path=GRID_FILE, assets=KEY_ASSETS, map_root=None, cell_size=CELL_SIZE, avoid_symbols=None, attach_to_map=False):
    """Spawn one of each key on distinct random 🟪 cells read from `grid_path`.

    - parent: optional Vizard group to attach keys to.
    - grid_path: path to Map_Grid.txt.
    - assets: list of 3 asset relative paths (red, yellow, white).

    Returns list of spawned nodes (or None for missing creations) in same order as assets.
    """
    grid, rows, cols = _read_grid(grid_path)
    if not grid:
        print('[KeyLoader] Grid not found or empty:', grid_path)
        return [None, None, None]

    # prefer filtered candidates (avoid player's spawn and hideout)
    candidates = _find_candidate_cells_filtered(grid, avoid_symbols=avoid_symbols)
    if not candidates:
        # fallback to unfiltered
        candidates = _find_candidate_cells(grid)
    if not candidates:
        print('[KeyLoader] No 🟪 cells found in grid; cannot place keys')
        return [None, None, None]

    if len(candidates) < len(assets):
        print('[KeyLoader] Warning: fewer candidate cells than keys; will reuse cells')

    chosen = random.sample(candidates, min(len(candidates), len(assets)))
    # if fewer candidates than assets, allow repeats but ensure one each by cycling
    while len(chosen) < len(assets):
        chosen.append(random.choice(candidates))

    # If a map_root (Vizard group) is provided, try to align grid cell coordinates
    # to the group's bounding rectangle so keys land on the visible map.
    left = None; top = None; used_cell = cell_size
    if map_root is not None and viz is not None:
        bounds = _compute_group_bounds(map_root)
        if bounds is not None:
            minX, minZ, maxX, maxZ = bounds
            width = maxX - minX
            height = maxZ - minZ
            # compute cell size from geometry (average X/Z cell sizes)
            if cols > 0 and rows > 0:
                cell_x = width / float(cols)
                cell_z = height / float(rows)
                used_cell = (cell_x + cell_z) / 2.0 if cell_x > 0 and cell_z > 0 else cell_size
                left = minX
                top = maxZ
                print('[KeyLoader] Aligned grid to map bounds:', (minX, minZ, maxX, maxZ), 'cell=', used_cell)

    spawned = []
    for asset, (r, c) in zip(assets, chosen):
        x, y, z = _grid_to_world(r, c, rows, cols, cell_size=used_cell, left=left, top=top)
        # By default spawn keys as top-level children at world coords to avoid
        # parent-relative transforms or collision/overlap issues. If attach_to_map
        # is True we'll parent them to the provided `parent` (map group).
        load_parent = parent if attach_to_map else None
        node = _safe_load_key(asset, parent=load_parent, scale=0.7)
        if node:
            try:
                node.setPosition([x, y, z])
            except Exception:
                pass
        spawned.append(node)
        print('[KeyLoader] Placed key', asset, 'grid=', (r, c), 'world=', (x, y, z), 'parented=', bool(load_parent))
    print('[KeyLoader] Spawned keys at', chosen)
    return spawned


if __name__ == '__main__':
    # Quick test when run directly (non-Vizard environments will just print warnings)
    print('KeyLoader quick test: spawning keys (no parent)')
    spawn_keys_on_map()
