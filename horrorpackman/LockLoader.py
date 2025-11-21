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


def spawn_locks_in_green_cells(parent=None, map_root=None, attach_to_map=True, grid_path=None, cell_size=DEFAULT_CELL_SIZE, gap=0.0, rotate_degrees=270.0, attach_to_wall=True, wall_offset=0.05):
    """Find the green tiles (🟩) in `Map_Grid.txt` and spawn 3 lock models centered inside the combined area of the first two green cells.

    - Places the three locks next to each other along the X axis (world/local depending on attach_to_map) with the provided `gap` between them.
    - `rotate_degrees` : yaw rotation in degrees applied to each lock (first Euler component).
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

    # detect special wall markers (🟧) in the grid and compute their world centers
    wall_cells = []
    for r in range(rows):
        row = grid[r]
        for c in range(cols):
            ch = row[c] if c < len(row) else None
            if ch == '🟧':
                wall_cells.append((r, c))

    wall_centers = []
    for (r, c) in wall_cells:
        grid_r = (rows - 1 - r)
        if use_local:
            wx = local_origin_x + (c * cell_size)
            wz = local_origin_z + (grid_r * cell_size)
        else:
            wx = origin_x + (c * cell_size)
            wz = origin_z + (grid_r * cell_size)
        wall_centers.append((wx, LOCK_Y, wz))

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

    # compute combined center
    center_x = (min_x + max_x) / 2.0
    center_z = (min_z + max_z) / 2.0

    positions = []
    # First, try to find wall cells adjacent to the green cells (prefer exact adjacency using 🟧 markers)
    adj_side = None
    adj_wall_centers = []
    if wall_cells:
        wall_set = set(wall_cells)
        # Check adjacency per green cell
        adj_matches = []
        for (gr, gc) in cells:
            # neighbors: left, right, up, down
            neighbors = [((gr, gc-1), 'left'), ((gr, gc+1), 'right'), ((gr-1, gc), 'top'), ((gr+1, gc), 'bottom')]
            found = None
            for (nr, nc), side_name in neighbors:
                if (nr, nc) in wall_set:
                    found = (nr, nc, side_name)
                    break
            if found:
                adj_matches.append(found)

        if adj_matches:
            # prefer a consistent side if both green cells matched
            sides = [m[2] for m in adj_matches]
            # pick the most common side
            try:
                adj_side = max(set(sides), key=sides.count)
            except Exception:
                adj_side = sides[0]

            # collect wall centers for matched wall cells on that side
            for (nr, nc, sname) in adj_matches:
                if sname == adj_side:
                    # compute world center for this wall cell
                    grid_r = (rows - 1 - nr)
                    if use_local:
                        wx = local_origin_x + (nc * cell_size)
                        wz = local_origin_z + (grid_r * cell_size)
                    else:
                        wx = origin_x + (nc * cell_size)
                        wz = origin_z + (grid_r * cell_size)
                    adj_wall_centers.append((wx, LOCK_Y, wz))

    # If we have adjacency info, place locks along the wall face flush to wall cells.
    if adj_side and adj_wall_centers:
        # average wall center
        wx = sum(p[0] for p in adj_wall_centers) / len(adj_wall_centers)
        wz = sum(p[2] for p in adj_wall_centers) / len(adj_wall_centers)
        if adj_side in ('left', 'right'):
            # wall is to the left or right of green cells -> wall face at wx +/- cell_size/2
            if adj_side == 'left':
                wall_face_x = wx + (cell_size / 2.0)
                # place lock centers to the right of the wall face
                lock_center_x = wall_face_x + wall_offset + (desired_lock_size / 2.0)
            else:
                wall_face_x = wx - (cell_size / 2.0)
                lock_center_x = wall_face_x - wall_offset - (desired_lock_size / 2.0)

            # spread locks along Z centered at combined center_z
            total_locks_depth = 3.0 * desired_lock_size + 2.0 * gap
            start_z = center_z - (total_locks_depth / 2.0) + (desired_lock_size / 2.0)
            for i in range(3):
                x = lock_center_x
                z = start_z + i * (desired_lock_size + gap)
                positions.append((x, LOCK_Y, z))
        else:
            # top/bottom
            if adj_side == 'bottom':
                wall_face_z = wz + (cell_size / 2.0)
                lock_center_z = wall_face_z + wall_offset + (desired_lock_size / 2.0)
            else:
                wall_face_z = wz - (cell_size / 2.0)
                lock_center_z = wall_face_z - wall_offset - (desired_lock_size / 2.0)

            total_locks_width = 3.0 * desired_lock_size + 2.0 * gap
            start_x = center_x - (total_locks_width / 2.0) + (desired_lock_size / 2.0)
            for i in range(3):
                x = start_x + i * (desired_lock_size + gap)
                z = lock_center_z
                positions.append((x, LOCK_Y, z))
    else:
        # fallback: previous behavior using pacmap bounds or centered spread along X
        # If attach_to_wall requested but no adjacency, fall back to bounds-based nearest side
        side = None
        if attach_to_wall and map_root is not None and hasattr(map_root, '_pacmap_bounds'):
            try:
                bminX, bminZ, bmaxX, bmaxZ = map_root._pacmap_bounds
                d_left = abs(center_x - bminX)
                d_right = abs(bmaxX - center_x)
                d_bottom = abs(center_z - bminZ)
                d_top = abs(bmaxZ - center_z)
                side = min((('left', d_left), ('right', d_right), ('bottom', d_bottom), ('top', d_top)), key=lambda t: t[1])[0]
            except Exception:
                side = None

        if side in ('left', 'right'):
            if side == 'left':
                fixed_x = bminX + (desired_lock_size / 2.0) + wall_offset
            else:
                fixed_x = bmaxX - (desired_lock_size / 2.0) - wall_offset

            total_locks_depth = 3.0 * desired_lock_size + 2.0 * gap
            start_z = center_z - (total_locks_depth / 2.0) + (desired_lock_size / 2.0)
            for i in range(3):
                x = fixed_x
                z = start_z + i * (desired_lock_size + gap)
                positions.append((x, LOCK_Y, z))
        elif side in ('top', 'bottom'):
            if side == 'bottom':
                fixed_z = bminZ + (desired_lock_size / 2.0) + wall_offset
            else:
                fixed_z = bmaxZ - (desired_lock_size / 2.0) - wall_offset

            total_locks_width = 3.0 * desired_lock_size + 2.0 * gap
            start_x = center_x - (total_locks_width / 2.0) + (desired_lock_size / 2.0)
            for i in range(3):
                x = start_x + i * (desired_lock_size + gap)
                z = fixed_z
                positions.append((x, LOCK_Y, z))
        else:
            total_locks_width = 3.0 * desired_lock_size + 2.0 * gap
            start_x = center_x - (total_locks_width / 2.0) + (desired_lock_size / 2.0)
            for i in range(3):
                x = start_x + i * (desired_lock_size + gap)
                z = center_z
                positions.append((x, LOCK_Y, z))

    # parent group
    if attach_to_map and map_root is not None:
        group = map_root
    else:
        group = parent if parent is not None else viz.addGroup()

    spawned = []

    for idx, pos in enumerate(positions):
        # Explicit ordering: left = green, center = yellow, right = white
        if idx == 0:
            asset_filename = 'Lock_Green.glb'
        elif idx == 1:
            asset_filename = 'Lock_Yellow.glb'
        else:
            asset_filename = 'Lock_White.glb'

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
        # Attempt to align the node's visual center to the target position so
        # all locks appear in a straight line regardless of model pivots.
        try:
            # compute local bounding-box center of the node (visual center)
            bbox = None
            try:
                bbox = node.getBoundingBox()
            except Exception:
                bbox = None

            tx, ty, tz = pos
            if bbox:
                try:
                    minX, minY, minZ, maxX, maxY, maxZ = bbox
                    local_cx = (minX + maxX) * 0.5
                    local_cy = (minY + maxY) * 0.5
                    local_cz = (minZ + maxZ) * 0.5
                    # Desired world visual center is (tx, LOCK_Y, center_z)
                    desired_vx = tx
                    desired_vy = LOCK_Y
                    desired_vz = center_z
                    # Place the wrapper so that visual center maps to desired world position.
                    # Assume local bbox is in the node's local space so setting node position
                    # to (desired - local_center) aligns it.
                    place_x = desired_vx - local_cx
                    place_y = desired_vy - local_cy
                    place_z = desired_vz - local_cz
                    try:
                        node.setPosition([place_x, place_y, place_z])
                    except Exception:
                        # fallback to naive placement
                        try:
                            node.setPosition([tx, LOCK_Y, tz])
                        except Exception:
                            pass
                except Exception:
                    try:
                        node.setPosition([tx, LOCK_Y, tz])
                    except Exception:
                        pass
            else:
                try:
                    node.setPosition([tx, LOCK_Y, tz])
                except Exception:
                    pass

            # apply yaw rotation after positioning
            if rotate_degrees is not None:
                try:
                    node.setEuler([float(rotate_degrees), 0.0, 0.0])
                except Exception:
                    pass
            # If attaching to a wall side, prefer using explicit 🟧 wall cells
            try:
                if attach_to_wall and wall_centers:
                    # Use the two nearest wall centers to determine wall orientation
                    wc = wall_centers
                    if len(wc) >= 2:
                        # pick two wall centers closest to the combined center
                        wc_sorted = sorted(wc, key=lambda p: (p[0]-center_x)**2 + (p[2]-center_z)**2)
                        a = wc_sorted[0]
                        b = wc_sorted[1]
                    else:
                        a = wc[0]
                        b = wc[0]

                    # vector from a to b determines wall direction
                    dx_ab = b[0] - a[0]
                    dz_ab = b[2] - a[2]
                    # determine if wall is primarily along X or Z
                    if abs(dx_ab) > abs(dz_ab):
                        wall_axis = 'x'  # wall varies in X, fixed Z
                        wall_z = (a[2] + b[2]) * 0.5
                        # interior side: compare combined center to wall_z
                        interior_positive = (center_z > wall_z)
                    else:
                        wall_axis = 'z'  # wall varies in Z, fixed X
                        wall_x = (a[0] + b[0]) * 0.5
                        interior_positive = (center_x > wall_x)

                    # get node bbox in world space
                    bbox2 = None
                    try:
                        bbox2 = node.getBoundingBox()
                    except Exception:
                        bbox2 = None

                    if bbox2:
                        try:
                            bminX_w, bminY_w, bminZ_w, bmaxX_w, bmaxY_w, bmaxZ_w = bbox2
                            cur_minX, cur_minY, cur_minZ = bminX_w, bminY_w, bminZ_w
                            cur_maxX, cur_maxY, cur_maxZ = bmaxX_w, bmaxY_w, bmaxZ_w
                            dx_nudge = 0.0
                            dz_nudge = 0.0
                            if wall_axis == 'x':
                                # wall at wall_z, if interior is positive, place node.minZ == wall_z + wall_offset
                                if interior_positive:
                                    target_minZ = wall_z + wall_offset
                                    dz_nudge = target_minZ - cur_minZ
                                else:
                                    target_maxZ = wall_z - wall_offset
                                    dz_nudge = target_maxZ - cur_maxZ
                            else:
                                # wall at wall_x, align X face
                                if interior_positive:
                                    target_minX = wall_x + wall_offset
                                    dx_nudge = target_minX - cur_minX
                                else:
                                    target_maxX = wall_x - wall_offset
                                    dx_nudge = target_maxX - cur_maxX

                            if abs(dx_nudge) > 1e-6 or abs(dz_nudge) > 1e-6:
                                try:
                                    px, py, pz = node.getPosition()
                                    node.setPosition([px + dx_nudge, py, pz + dz_nudge])
                                except Exception:
                                    pass
                        except Exception:
                            pass
                else:
                    # fallback to pacmap bounds nudging if no wall markers
                    if attach_to_wall and side in ('left','right','top','bottom') and map_root is not None and hasattr(map_root, '_pacmap_bounds'):
                        bbox2 = None
                        try:
                            bbox2 = node.getBoundingBox()
                        except Exception:
                            bbox2 = None
                        if bbox2:
                            try:
                                bminX_w, bminY_w, bminZ_w, bmaxX_w, bmaxY_w, bmaxZ_w = bbox2
                                cur_minX, cur_minY, cur_minZ = bminX_w, bminY_w, bminZ_w
                                cur_maxX, cur_maxY, cur_maxZ = bmaxX_w, bmaxY_w, bmaxZ_w
                                dx = 0.0; dz = 0.0
                                try:
                                    bminX_map, bminZ_map, bmaxX_map, bmaxZ_map = map_root._pacmap_bounds
                                except Exception:
                                    bminX_map = bminZ_map = bmaxX_map = bmaxZ_map = None
                                if side == 'left' and bminX_map is not None:
                                    target_minX = bminX_map + wall_offset
                                    dx = target_minX - cur_minX
                                elif side == 'right' and bmaxX_map is not None:
                                    target_maxX = bmaxX_map - wall_offset
                                    dx = target_maxX - cur_maxX
                                elif side == 'bottom' and bminZ_map is not None:
                                    target_minZ = bminZ_map + wall_offset
                                    dz = target_minZ - cur_minZ
                                elif side == 'top' and bmaxZ_map is not None:
                                    target_maxZ = bmaxZ_map - wall_offset
                                    dz = target_maxZ - cur_maxZ

                                if abs(dx) > 1e-6 or abs(dz) > 1e-6:
                                    try:
                                        px, py, pz = node.getPosition()
                                        node.setPosition([px + dx, py, pz + dz])
                                    except Exception:
                                        pass
                            except Exception:
                                pass
            except Exception:
                pass
        except Exception:
            # best-effort: keep original pos
            try:
                node.setPosition(pos)
            except Exception:
                pass

        spawned.append(node)
        try:
            print('[LockLoader] Spawned lock', idx, 'at', pos, 'using', asset_filename)
        except Exception:
            pass

    # At this point we already attempted per-node visual-centering. As a final
    # safeguard, ensure each spawned node's Y is LOCK_Y (vertical) so they sit flush.
    try:
        for i, node in enumerate(spawned):
            try:
                x, y, z = node.getPosition()
                node.setPosition([x, LOCK_Y, z])
            except Exception:
                pass
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
