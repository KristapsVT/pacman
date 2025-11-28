import os
import random
import math
import viz
import vizshape

CELL_EMOJI = '🟪'  # purple tile marker in Map_Grid.txt
DEFAULT_CELL_SIZE = 3.0
# Place keys slightly above the ground so they don't z-fight with floor
KEY_Y = 0.15
KEY_RADIUS = 0.25

# Key asset filenames (placed in the package `assets` folder)
_KEY_ASSETS = ['Key_Green.glb', 'Key_White.glb', 'Key_Yellow.glb']

def _center_glb_local_in_wrapper(raw, center_blend=0.6, desired_bottom=0.0):
    """Center raw model inside a wrapper: make wrapper origin near visual center (XZ)
    and bottom-align the model so wrapper sits on the floor.

    center_blend: blend factor [0..1] mixing bounding-box center (0) with
                  bounding-sphere center (1). This helps align models with
                  odd pivots. desired_bottom is the Y value to align model's
                  minimum Y to (typically 0.0 for ground).
    """
    def _get_sphere_center(node):
        try:
            sx, sy, sz, sr = node.getBoundingSphere()
            return sx, sy, sz
        except Exception:
            return None

    try:
        minX, minY, minZ, maxX, maxY, maxZ = raw.getBoundingBox()
        cx = (minX + maxX) * 0.5
        cz = (minZ + maxZ) * 0.5
        sc = _get_sphere_center(raw)
        if sc:
            sx, _, sz = sc
            a = float(center_blend) if center_blend is not None else 0.6
            a = max(0.0, min(1.0, a))
            cx = cx * (1.0 - a) + sx * a
            cz = cz * (1.0 - a) + sz * a
        liftY = float(desired_bottom) - minY
        raw.setPosition([-cx, liftY, -cz])
    except Exception:
        try:
            raw.setPosition([0, 0, 0])
        except Exception:
            pass


def _load_key_model(filename, scale_factor=1.0, tint=None, fallback_color=(0.95, 0.9, 0.15), center_blend=0.6, desired_bottom=0.0, desired_size=None):
    """Attempt to load a GLB key model from the package assets folder.
    Returns a group wrapper containing the visual. On failure, returns a simple primitive group.
    """
    asset_path = os.path.normpath(os.path.join(os.path.dirname(__file__), 'assets', filename))
    if os.path.exists(asset_path):
        try:
            wrapper = viz.addGroup()
            raw = viz.addChild(asset_path)
            raw.setParent(wrapper)
            # apply initial scale factor
            try:
                raw.setScale([scale_factor] * 3)
            except Exception:
                pass

            # If a desired_size (world units) is requested, compute the current X/Z size
            # and apply an additional uniform scale so the key fits `desired_size` units
            if desired_size is not None:
                try:
                    minX, minY, minZ, maxX, maxY, maxZ = raw.getBoundingBox()
                    cur_w = maxX - minX
                    cur_d = maxZ - minZ
                    cur_max = max(cur_w, cur_d)
                    if cur_max > 0:
                        # bounding box values already account for the earlier scale
                        extra_scale = float(desired_size) / float(cur_max)
                        raw.setScale([scale_factor * extra_scale] * 3)
                except Exception:
                    pass

            # Re-center after any scaling adjustments
            _center_glb_local_in_wrapper(raw, center_blend=center_blend, desired_bottom=desired_bottom)
            # If no explicit tint was provided, try to apply a sensible
            # authored tint based on filename so visuals and detection match.
            try:
                if tint is not None:
                    wrapper.color(*tint)
                else:
                    lname = filename.lower() if filename else ''
                    if 'green' in lname:
                        wrapper.color(70.0/255.0, 183.0/255.0, 73.0/255.0)
                    elif 'yellow' in lname:
                        wrapper.color(255.0/255.0, 221.0/255.0, 26.0/255.0)
                    elif 'white' in lname:
                        wrapper.color(221.0/255.0, 226.0/255.0, 228.0/255.0)
            except Exception:
                pass
            # mark wrapper as an authored key asset so styling won't override its colors
            try:
                wrapper._is_key_asset = True
            except Exception:
                pass
            return wrapper
        except Exception as e:
            print('[KeyLoader] Model load error for', asset_path, ':', e)

    # Fallback primitive
    g = viz.addGroup()
    try:
        # If a desired_size is provided, create a fallback sphere matching that size
        if desired_size is not None and desired_size > 0:
            try:
                node = vizshape.addSphere(radius=(desired_size * 0.5))
            except Exception:
                node = vizshape.addSphere(radius=KEY_RADIUS)
        else:
            node = vizshape.addSphere(radius=KEY_RADIUS)
        try:
            node.color(*fallback_color)
        except Exception:
            pass
        node.setParent(g)
    except Exception:
        pass
    # apply overall group scale for legacy callers using scale_factor
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


def _style_keys(keys_list):
    """Apply simple styling to spawned key nodes: disable lighting and assign alternating colors.

    keys_list: iterable of viz nodes (or dicts) returned by spawn_keys_on_map when visualize=True.
    """
    if not keys_list:
        return
    for n in keys_list:
        if not n:
            continue
        # skip non-visual dict entries
        if isinstance(n, dict):
            continue
        try:
            n.disable(viz.LIGHTING)
        except Exception:
            pass

    for i, n in enumerate(keys_list):
        if not n or isinstance(n, dict):
            continue
        try:
            # Only apply style color to fallback primitives (non-asset keys).
            if not getattr(n, '_is_key_asset', False):
                if i % 2 == 0:
                    n.color(0.00, 0.80, 1.00)
                else:
                    n.color(0.02, 0.02, 0.02)
        except Exception:
            pass

def _default_grid_path():
    # Map_Grid.txt is in the project root next to the Player runtime package
    return os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'Map_Grid.txt'))

def _read_grid(grid_path):
    with open(grid_path, 'r', encoding='utf-8') as f:
        raw = [ln.rstrip('\n') for ln in f.readlines() if ln.strip()]
    # Convert each line into a list of characters (emoji cells)
    grid = [list(line) for line in raw]
    return grid

def spawn_keys_on_map(parent=None, map_root=None, attach_to_map=True, visualize=True,
                      grid_path=None, cell_size=DEFAULT_CELL_SIZE, spawn_chance=1.0,
                      num_keys=3, min_distance=None, key_offset=(0.0, 0.0, 0.0), center_blend=0.6):
    """Spawn key nodes on purple tiles from `Map_Grid.txt`.

    Args:
        parent: optional viz group to attach spawned keys to (created if None and attach_to_map False).
        map_root: the pacmap group returned by `MapLoader.load_pacmap()` (used for center alignment).
        attach_to_map: if True and `map_root` provided, keys are parented to `map_root`.
        visualize: whether to create visible sphere nodes for keys (True) or just return logical positions (False).
        grid_path: optional path to `Map_Grid.txt`; defaults to workspace root Map_Grid.txt.
        cell_size: world units per grid cell (defaults to 3.0 as requested).
        spawn_chance: 0..1 chance to consider a purple tile as eligible (pre-filter).
        num_keys: how many keys to place (chosen randomly from eligible purple tiles).
        min_distance: minimum world distance between spawned keys; defaults to cell_size * 1.25.

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

    # Collect eligible positions first (apply spawn_chance as eligibility filter)
    eligible_positions = []
    for r in range(rows):
        row = grid[r]
        for c in range(cols):
            ch = row[c] if c < len(row) else None
            if ch != CELL_EMOJI:
                continue
            if spawn_chance < 1.0 and random.random() > spawn_chance:
                continue
            grid_r = (rows - 1 - r)
            if use_local:
                lx = local_origin_x + (c * cell_size)
                lz = local_origin_z + (grid_r * cell_size)
                pos = [lx, KEY_Y, lz]
            else:
                wx = origin_x + (c * cell_size)
                wz = origin_z + (grid_r * cell_size)
                pos = [wx, KEY_Y, wz]
            eligible_positions.append(pos)

    # If no eligible positions, return early
    if not eligible_positions:
        print('[KeyLoader] No eligible purple tiles found in grid -> no keys spawned')
        return group, []

    # Determine minimum distance
    if min_distance is None:
        min_distance = cell_size * 1.25

    # Pick positions using a farthest-point greedy sampler to maximize spread.
    # Start with one random seed, then repeatedly pick the eligible position with
    # the largest distance to the set of already chosen positions. This avoids
    # clustering in one area (e.g., the top part of the map).
    chosen = []
    if not eligible_positions:
        return group, []

    if num_keys >= len(eligible_positions):
        chosen = list(eligible_positions)
    else:
        # seed with a random eligible position
        first = random.choice(eligible_positions)
        chosen.append(first)

        # iterative farthest-point selection
        while len(chosen) < num_keys:
            best_pos = None
            best_min_sq = -1.0
            for pos in eligible_positions:
                if pos in chosen:
                    continue
                # compute squared distance to nearest chosen
                min_sq = min((pos[0]-p[0])**2 + (pos[2]-p[2])**2 for p in chosen)
                if min_sq > best_min_sq:
                    best_min_sq = min_sq
                    best_pos = pos

            if best_pos is None:
                break

            # If best candidate still violates min_distance, we still accept it
            # because it is the farthest available; this prevents all keys clustering
            chosen.append(best_pos)

    print('[KeyLoader] Eligible positions:', len(eligible_positions), '  requested keys:', num_keys)
    spawned = []
    # normalize key_offset into tuple of floats
    try:
        ox, oy, oz = (float(key_offset[0]), float(key_offset[1]), float(key_offset[2]))
    except Exception:
        ox, oy, oz = (0.0, 0.0, 0.0)

    for idx, pos in enumerate(chosen):
        if visualize:
            # preserve original model size intent, but request a 1.0 world-size key
            # so a 1x1 key fits centrally inside a 3x3 cell.
            scale_factor = 1.0
            # Cycle through available key assets to provide variety
            asset_filename = _KEY_ASSETS[idx % len(_KEY_ASSETS)] if _KEY_ASSETS else None
            # choose sensible fallback tint based on filename
            if asset_filename and 'Green' in asset_filename:
                fallback = (0.2, 0.9, 0.2)
            elif asset_filename and 'White' in asset_filename:
                fallback = (0.95, 0.95, 0.95)
            elif asset_filename and 'Yellow' in asset_filename:
                fallback = (1.0, 0.9, 0.2)
            else:
                fallback = (0.95, 0.85, 0.15)

            if asset_filename:
                asset_path = os.path.normpath(os.path.join(os.path.dirname(__file__), 'assets', asset_filename))
                print('[KeyLoader] Spawning key', idx, 'using asset:', asset_path, 'exists=', os.path.exists(asset_path), 'center_blend=', center_blend)
                node = _load_key_model(asset_filename, scale_factor=scale_factor, tint=None, fallback_color=fallback, center_blend=center_blend, desired_bottom=0.0, desired_size=1.0)
            else:
                node = vizshape.addSphere(radius=KEY_RADIUS)
                try:
                    node.color(*fallback)
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
                # apply optional offset so callers can nudge models relative to grid center
                node_pos = (pos[0] + ox, pos[1] + oy, pos[2] + oz)
                node.setPosition(node_pos)
            except Exception:
                pass
            try:
                print('[KeyLoader] Spawned node:', getattr(node, '__repr__', lambda: str(node))(), 'at', pos)
            except Exception:
                pass
            try:
                node._is_key = True
            except Exception:
                pass
            spawned.append(node)
        else:
            spawned.append({'pos': pos})

    # Apply styling similar to _style_pacmap and record last spawned keys
    try:
        if visualize:
            _style_keys(spawned)
    except Exception:
        pass

    try:
        global _last_spawned
        _last_spawned = list(spawned)
    except Exception:
        pass

    return group, spawned


# Keep an internal cache of last spawned keys (list of viz nodes or dicts)
_last_spawned = []


def get_last_spawned_keys():
    """Return the last spawned keys list (may contain viz nodes or dicts).

    Returns a shallow copy of the internal list to avoid accidental modification.
    """
    try:
        return list(_last_spawned)
    except Exception:
        return []


def point_to_closest_key(player=None, keys_list=None):
    """Find the nearest key and compute yaw (degrees) towards it.

    Args:
        player: optional viz node to read current player position (if provided) and optionally set euler.
        keys_list: optional list of keys (viz nodes or dicts). If None, uses internal `get_last_spawned_keys()`.

    Returns:
        dict with keys: 'yaw' (degrees), 'distance' (float), 'target_pos' (x,y,z) on success;
        None if no keys or on failure.
    """
    if keys_list is None:
        keys_list = get_last_spawned_keys()
    if not keys_list:
        return None

    # get player position
    if player is not None:
        try:
            px, py, pz = player.getPosition()
        except Exception:
            px = py = pz = None
    else:
        px = py = pz = None

    # if no player position provided, attempt to use first key as reference
    best = None
    best_sq = float('inf')
    for k in keys_list:
        tx = tz = ty = None
        if isinstance(k, dict):
            pos = k.get('pos')
            if pos:
                tx, ty, tz = pos
        else:
            try:
                kx, ky, kz = k.getPosition()
                tx, ty, tz = kx, ky, kz
            except Exception:
                pass
        if tx is None or tz is None:
            continue
        if px is None:
            # no player reference; choose first valid key
            best = (tx, ty, tz)
            break
        dx = tx - px
        dz = tz - pz
        sq = dx*dx + dz*dz
        if sq < best_sq:
            best_sq = sq
            best = (tx, ty, tz)

    if best is None:
        return None

    tx, ty, tz = best
    if px is None:
        # can't compute yaw without player position
        return {'yaw': 0.0, 'distance': None, 'target_pos': (tx, ty, tz)}

    dx = tx - px
    dz = tz - pz
    try:
        yaw_target = math.degrees(math.atan2(dx, dz))
    except Exception:
        yaw_target = 0.0

    dist = math.sqrt((dx*dx)+(dz*dz))

    result = {'yaw': yaw_target, 'distance': dist, 'target_pos': (tx, ty, tz)}

    # if player provided, attempt to set its facing
    if player is not None:
        try:
            player.setEuler([yaw_target, 0, 0])
        except Exception:
            pass

    return result


if __name__ == '__main__':
    # Quick local test (non-Vizard headless awareness): only runs when executed directly
    p = _default_grid_path()
    print('Using grid:', p)
    g = _read_grid(p)
    print('Grid size rows=%d cols=%d' % (len(g), max(len(r) for r in g)))
