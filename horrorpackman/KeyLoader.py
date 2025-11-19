import os
import random
import viz
import vizshape

CELL_EMOJI = '🟪'  # purple tile marker in Map_Grid.txt
DEFAULT_CELL_SIZE = 3.0
KEY_Y = 0.35
KEY_RADIUS = 0.25

def _default_grid_path():
    # Map_Grid.txt is in the project root next to the horrorpackman package
    return os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'Map_Grid.txt'))

def _read_grid(grid_path):
    with open(grid_path, 'r', encoding='utf-8') as f:
        raw = [ln.rstrip('\n') for ln in f.readlines() if ln.strip()]
    # Convert each line into a list of characters (emoji cells)
    grid = [list(line) for line in raw]
    return grid

def spawn_keys_on_map(parent=None, map_root=None, attach_to_map=True, visualize=True,
                      grid_path=None, cell_size=DEFAULT_CELL_SIZE, spawn_chance=1.0):
    """Spawn key nodes on purple tiles from `Map_Grid.txt`.

    Args:
        parent: optional viz group to attach spawned keys to (created if None and attach_to_map False).
        map_root: the pacmap group returned by `MapLoader.load_pacmap()` (used for center alignment).
        attach_to_map: if True and `map_root` provided, keys are parented to `map_root`.
        visualize: whether to create visible sphere nodes for keys (True) or just return logical positions (False).
        grid_path: optional path to `Map_Grid.txt`; defaults to workspace root Map_Grid.txt.
        cell_size: world units per grid cell (defaults to 3.0 as requested).
        spawn_chance: 0..1 chance to actually spawn a key on a purple tile.

    Returns:
        (group, keys) where `group` is the parent group used and `keys` is a list of spawned nodes (or dicts with positions if visualize=False).
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

    # Determine map center
    if map_root is not None and hasattr(map_root, '_pacmap_center'):
        center_x, center_z = map_root._pacmap_center
    else:
        center_x, center_z = (0.0, 0.0)

    # Compute full grid size
    grid_width = cols * cell_size
    grid_depth = rows * cell_size
    # When attaching to map_root we will compute local coordinates relative to the pacmap center
    # so child positions align with the map group's local space. Otherwise compute world-space origin.
    if attach_to_map and map_root is not None and hasattr(map_root, '_pacmap_center'):
        # local origin relative to pacmap center: center of top-left cell
        local_origin_x = - (grid_width / 2.0) + (cell_size / 2.0)
        local_origin_z = - (grid_depth / 2.0) + (cell_size / 2.0)
        use_local = True
    else:
        # world-space origin
        origin_x = center_x - (grid_width / 2.0) + (cell_size / 2.0)
        origin_z = center_z - (grid_depth / 2.0) + (cell_size / 2.0)
        use_local = False

    # Parent group
    if attach_to_map and map_root is not None:
        group = map_root
    else:
        group = parent if parent is not None else viz.addGroup()

    spawned = []
    for r in range(rows):
        row = grid[r]
        for c in range(cols):
            ch = row[c] if c < len(row) else None
            if ch != CELL_EMOJI:
                continue
            if spawn_chance < 1.0 and random.random() > spawn_chance:
                continue

            # Flip row index so text top corresponds to negative Z->positive Z ordering
            grid_r = (rows - 1 - r)
            if use_local:
                lx = local_origin_x + (c * cell_size)
                lz = local_origin_z + (grid_r * cell_size)
                pos = [lx, KEY_Y, lz]
            else:
                wx = origin_x + (c * cell_size)
                wz = origin_z + (grid_r * cell_size)
                pos = [wx, KEY_Y, wz]

            if visualize:
                node = vizshape.addSphere(radius=KEY_RADIUS)
                try:
                    node.color(1.0, 0.85, 0.05)
                except Exception:
                    pass
                # Parent before setting position when using local coords to avoid transform issues
                try:
                    if attach_to_map and map_root is not None:
                        node.setParent(map_root)
                    else:
                        node.setParent(group)
                except Exception:
                    pass
                node.setPosition(pos)
                # tag for debugging
                try:
                    node._is_key = True
                except Exception:
                    pass
                spawned.append(node)
            else:
                spawned.append({'pos': pos})

    return group, spawned


if __name__ == '__main__':
    # Quick local test (non-Vizard headless awareness): only runs when executed directly
    p = _default_grid_path()
    print('Using grid:', p)
    g = _read_grid(p)
    print('Grid size rows=%d cols=%d' % (len(g), max(len(r) for r in g)))
