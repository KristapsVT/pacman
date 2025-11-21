import os
import math
import random

import viz
import vizact
import vizshape
from PacManLoaderAndAnimations import run_pacman_animation

# -----------------------------
# Constants / Config
# -----------------------------
GRID_FILE = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'Map_Grid.txt'))
CELL_SIZE = 3.0
PACMAN_TURN_RATE = 360.0  # deg/sec for smooth facing
PACMAN_RADIUS = 0.45
PACMAN_SCALE = 0.11
PACMAN_Y = 0.35
JUMP_FORWARD_FACTOR = 2  # increase jump distance beyond one cell

# LOS/behavior
SIGHT_MAX_DIST = 9999.0  # rely on walls to block
REPATH_INTERVAL_CHASE = 0.25
REPATH_INTERVAL_WANDER = 1.25
REPATH_INTERVAL_SEEK = 0.35  # repath rate while moving toward last seen position
WANDER_REACH_CELLS = 6

# Player interaction radius: inside this Pac-Man wanders, outside he pursues/ seeks
PLAYER_WANDER_RADIUS = 10.0  # world units (updated to 10m as requested)

# Tiles: restrict walkable tiles to blue/yellow/purple; everything else blocks
WALKABLE_EMOJIS = {'🟦','🟨','🟪'}


def _read_grid(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = [ln.rstrip('\n') for ln in f.readlines() if ln.strip()]
    return [list(line) for line in lines]


class PacManChaser:
    def __init__(self, map_root=None, existing_node=None):
        self.map_root = map_root
        self.grid = _read_grid(GRID_FILE) if os.path.exists(GRID_FILE) else []
        self.rows = len(self.grid)
        self.cols = max((len(r) for r in self.grid), default=0)

        # Map bounds and origin mapping
        if self.map_root is not None and hasattr(self.map_root, '_pacmap_center'):
            cx, cz = self.map_root._pacmap_center
            # Use grid-aligned local origin when parented to map
            self.use_local = True
            self.local_origin_x = - (self.cols * CELL_SIZE) / 2.0 + (CELL_SIZE / 2.0)
            self.local_origin_z = - (self.rows * CELL_SIZE) / 2.0 + (CELL_SIZE / 2.0)
            self.center_x = cx
            self.center_z = cz
        else:
            self.use_local = False
            self.local_origin_x = None
            self.local_origin_z = None
            self.center_x = 0.0
            self.center_z = 0.0

        # Place at first walkable cell near center
        spawn_rc = self._find_spawn_cell_near_center()
        self.grid_r, self.grid_c = spawn_rc
        wx, wz = self.grid_to_world(self.grid_r, self.grid_c)
        if existing_node is not None:
            # Reuse externally created Pac-Man animation node
            self.node = existing_node
            try:
                self.node.setPosition([wx, PACMAN_Y, wz])
            except Exception:
                pass
        else:
            # Build Pac-Man using animation loader; parent under map if available
            self.node = run_pacman_animation(
                position=(wx, PACMAN_Y, wz),
                parent=self.map_root,
                base_scale=PACMAN_SCALE,
                jump_forward=CELL_SIZE * JUMP_FORWARD_FACTOR,
                forward_dir=(0.0, 0.0, 1.0)
            )
            if self.node is None:
                # Fallback primitive if Vizard unavailable
                self.node = viz.addGroup()
                ball = vizshape.addSphere(radius=0.5)
                ball.setParent(self.node)
                self.node.setPosition([wx, PACMAN_Y, wz])
                self.node.setScale([PACMAN_SCALE, PACMAN_SCALE, PACMAN_SCALE])
        self.facing_yaw = 0.0

        # Behavior state
        self.mode = 'wander'
        self.current_path = []  # list of (r,c)
        self.next_path_idx = 0
        self.repath_timer = 0.0
        self.last_seen_rc = None  # (r,c) of player when last in LOS
        self.caught_player = False  # updated each frame by distance check
        self._did_pounce_this_cycle = False
        self.last_chase_target = None  # track last chosen chase goal (walkable cell)

        # Animation state
        self.anim_time = 0.0
        self.anim_freq = 1.0  # slowed from 1.8 for less frantic squash cycles
        self.anim_w_amp = 0.2
        self.anim_h_amp = 0.22
    # -----------------------------
    # Grid/World mapping
    # -----------------------------
    def grid_to_world(self, r, c):
        # Flip row so text top is -Z
        grid_r = (self.rows - 1 - r)
        if self.use_local:
            lx = self.local_origin_x + c * CELL_SIZE
            lz = self.local_origin_z + grid_r * CELL_SIZE
            return lx, lz
        else:
            wx = (self.center_x - (self.cols * CELL_SIZE)/2.0 + (CELL_SIZE/2.0)) + c * CELL_SIZE
            wz = (self.center_z - (self.rows * CELL_SIZE)/2.0 + (CELL_SIZE/2.0)) + grid_r * CELL_SIZE
            return wx, wz

    def world_to_grid(self, x_in, z_in):
        if self.use_local:
            # Inputs are local coordinates relative to map_root origin
            lx = x_in - self.local_origin_x
            lz = z_in - self.local_origin_z
        else:
            # Inputs are world coordinates, convert relative to world-space grid origin
            lx = x_in - (self.center_x - (self.cols * CELL_SIZE)/2.0 + (CELL_SIZE/2.0))
            lz = z_in - (self.center_z - (self.rows * CELL_SIZE)/2.0 + (CELL_SIZE/2.0))
        # Convert to grid indices (rounded to nearest cell)
        grid_r = int(round(lz / CELL_SIZE))
        c = int(round(lx / CELL_SIZE))
        r = (self.rows - 1 - grid_r)
        r = max(0, min(self.rows - 1, r))
        c = max(0, min(self.cols - 1, c))
        return r, c

    def is_walkable(self, r, c):
        if r < 0 or c < 0 or r >= self.rows or c >= self.cols:
            return False
        tile = self.grid[r][c] if c < len(self.grid[r]) else None
        return tile in WALKABLE_EMOJIS

    # -----------------------------
    # Behavior utilities
    # -----------------------------
    def _find_spawn_cell_near_center(self):
        center_r = self.rows // 2
        center_c = self.cols // 2
        # Spiral search
        radius = max(self.rows, self.cols)
        for d in range(radius):
            for dr in range(-d, d + 1):
                for dc in range(-d, d + 1):
                    r = center_r + dr
                    c = center_c + dc
                    if self.is_walkable(r, c):
                        return (r, c)
        return (center_r, center_c)

    def _neighbors(self, r, c):
        for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
            nr, nc = r + dr, c + dc
            if self.is_walkable(nr, nc):
                yield nr, nc

    def _heuristic(self, a, b):
        return abs(a[0]-b[0]) + abs(a[1]-b[1])

    def _astar(self, start, goal, max_iter=5000):
        if start == goal:
            return [start]
        open_set = {start}
        came = {}
        g = {start: 0}
        f = {start: self._heuristic(start, goal)}
        for _ in range(max_iter):
            if not open_set:
                break
            current = min(open_set, key=lambda n: f.get(n, float('inf')))
            if current == goal:
                # reconstruct
                path = [current]
                while current in came:
                    current = came[current]
                    path.append(current)
                path.reverse()
                return path
            open_set.remove(current)
            cr, cc = current
            for nb in self._neighbors(cr, cc):
                tentative = g[current] + 1
                if tentative < g.get(nb, float('inf')):
                    came[nb] = current
                    g[nb] = tentative
                    f[nb] = tentative + self._heuristic(nb, goal)
                    open_set.add(nb)
        return []

    def _los_clear_grid(self, a, b):
        # Bresenham-like grid LOS
        (r0, c0) = a
        (r1, c1) = b
        dr = abs(r1 - r0)
        dc = abs(c1 - c0)
        sr = 1 if r0 < r1 else -1
        sc = 1 if c0 < c1 else -1
        err = dr - dc
        r, c = r0, c0
        while True:
            if not self.is_walkable(r, c) and (r, c) != a and (r, c) != b:
                return False
            if (r, c) == (r1, c1):
                break
            e2 = 2 * err
            if e2 > -dc:
                err -= dc
                r += sr
            if e2 < dr:
                err += dr
                c += sc
        return True

    def _choose_wander_target(self, from_rc):
        fr, fc = from_rc
        for _ in range(200):
            dr = random.randint(-WANDER_REACH_CELLS, WANDER_REACH_CELLS)
            dc = random.randint(-WANDER_REACH_CELLS, WANDER_REACH_CELLS)
            tr, tc = fr + dr, fc + dc
            if self.is_walkable(tr, tc):
                return (tr, tc)
        return from_rc

    def _nearest_walkable(self, r, c, max_radius=25):
        """Return nearest walkable cell to (r,c). If (r,c) walkable, returns it; else BFS outward."""
        if self.is_walkable(r, c):
            return (r, c)
        visited = set([(r, c)])
        frontier = [(r, c)]
        for depth in range(1, max_radius + 1):
            next_frontier = []
            for cr, cc in frontier:
                for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
                    nr, nc = cr + dr, cc + dc
                    if (nr, nc) in visited:
                        continue
                    visited.add((nr, nc))
                    if 0 <= nr < self.rows and 0 <= nc < self.cols:
                        if self.is_walkable(nr, nc):
                            return (nr, nc)
                        next_frontier.append((nr, nc))
            if not next_frontier:
                break
            frontier = next_frontier
        return None

    # -----------------------------
    # Public update
    # -----------------------------
    def update(self, dt, player_world_pos):
        if self.rows == 0 or self.cols == 0:
            # No grid; just idle animation
            self._update_animation(dt)
            return

        # Our current grid cell (snap from world)
        nx, ny, nz = self.node.getPosition()
        # node position is local when parented to map; pass as local/world accordingly
        self.grid_r, self.grid_c = self.world_to_grid(nx, nz)

        # Player grid cell
        px, py, pz = player_world_pos
        if self.use_local and self.map_root is not None:
            mx, my, mz = self.map_root.getPosition()
            pr, pc = self.world_to_grid(px - mx, pz - mz)
            pac_world_x = mx + nx
            pac_world_z = mz + nz
        else:
            pr, pc = self.world_to_grid(px, pz)
            pac_world_x = nx
            pac_world_z = nz

        # World-space distance Pac-Man -> player (XZ plane)
        dist_to_player = math.hypot(px - pac_world_x, pz - pac_world_z)
        inside_radius = dist_to_player <= PLAYER_WANDER_RADIUS

        # LOS check (grid-based) used to refresh last seen and determine chase vs seek
        in_sight = self._los_clear_grid((self.grid_r, self.grid_c), (pr, pc))
        if in_sight:
            self.last_seen_rc = (pr, pc)

        # Decide behavior mode and target cell (grid-based + pounce for fluid catch)
        # If in LOS:
        #   - if near player (within trigger) and not already caught -> pounce
        #   - else chase using player's current cell
        # Else out of LOS:
        #   - if outside radius: seek last seen or wander
        #   - if inside radius: wander (can't see player)
        POUNCE_TRIGGER_DIST = (PACMAN_RADIUS + 0.22) + 0.6
        POUNCE_OVERSHOOT = 0.4
        # Only allow pounce if player is in same or adjacent cell to avoid wall tunneling
        cell_sep = abs(self.grid_r - pr) + abs(self.grid_c - pc)
        def _can_pounce():
            return in_sight and (cell_sep <= 1)
        # Determine chase goal (nearest walkable to player's grid cell)
        chase_goal = self._nearest_walkable(pr, pc)
        if chase_goal is None:
            chase_goal = (pr, pc)  # may be non-walkable but gives direction
        # Outside radius: always chase (ignore LOS) unless immediate pounce applies
        if not inside_radius:
            if _can_pounce() and dist_to_player <= POUNCE_TRIGGER_DIST and not self.caught_player:
                self.mode = 'pounce'
                target_rc = None
                repath_interval = REPATH_INTERVAL_CHASE
            else:
                self.mode = 'chase'
                target_rc = chase_goal
                repath_interval = REPATH_INTERVAL_CHASE
        else:
            # Inside radius: original mixed behavior
            if in_sight:
                if _can_pounce() and dist_to_player <= POUNCE_TRIGGER_DIST and not self.caught_player:
                    self.mode = 'pounce'
                    target_rc = None
                    repath_interval = REPATH_INTERVAL_CHASE
                else:
                    self.mode = 'chase'
                    target_rc = chase_goal
                    repath_interval = REPATH_INTERVAL_CHASE
            else:
                if self.last_seen_rc is not None:
                    self.mode = 'seek'
                    target_rc = self.last_seen_rc
                    repath_interval = REPATH_INTERVAL_SEEK
                else:
                    self.mode = 'wander'
                    target_rc = None
                    repath_interval = REPATH_INTERVAL_WANDER
        # Track last chase goal
        if self.mode == 'chase' and target_rc is not None:
            self.last_chase_target = target_rc

        # Repath timer (skip for pounce since we override movement directly)
        if self.mode != 'pounce':
            self.repath_timer -= dt
            if self.repath_timer <= 0.0:
                if self.mode in ('chase','seek') and target_rc is not None:
                    self.current_path = self._astar((self.grid_r, self.grid_c), target_rc)
                    self.repath_timer = repath_interval
                elif self.mode == 'wander':
                    wander_goal = self._choose_wander_target((self.grid_r, self.grid_c))
                    self.current_path = self._astar((self.grid_r, self.grid_c), wander_goal)
                    self.repath_timer = REPATH_INTERVAL_WANDER
                else:
                    self.current_path = []
                    self.repath_timer = REPATH_INTERVAL_WANDER
                self.next_path_idx = 1
            else:
                # If chase goal changed, force quick repath
                if self.mode == 'chase' and self.last_chase_target and target_rc != self.last_chase_target:
                    self.current_path = self._astar((self.grid_r, self.grid_c), self.last_chase_target)
                    self.next_path_idx = 1
        else:
            self.current_path = []  # ensure no path influences jump params
            self.next_path_idx = 0

        # Movement steering
        if self.mode == 'pounce':
            # Direct jump toward player with slight overshoot
            dx = px - pac_world_x
            dz = pz - pac_world_z
            dist = math.hypot(dx, dz)
            if dist > 1e-6:
                vx = dx / dist
                vz = dz / dist
                jump_len = min(CELL_SIZE * 1.25 * JUMP_FORWARD_FACTOR, dist + POUNCE_OVERSHOOT)
                try:
                    if hasattr(self.node, 'set_jump_params'):
                        self.node.set_jump_params(new_forward_dir=(vx,0.0,vz), new_jump_forward=jump_len)
                except Exception:
                    pass
                desired_yaw = math.degrees(math.atan2(vx, vz))
                self.facing_yaw = self._turn_towards(self.facing_yaw, desired_yaw, PACMAN_TURN_RATE * dt)
                try:
                    self.node.setEuler([self.facing_yaw,0,0])
                except Exception:
                    pass
                self._did_pounce_this_cycle = True
        else:
            # Grid-relative jump steering
            self._follow_path_jump(dt)

        # Catch detection (generic distance check). After a pounce we allow tighter threshold.
        catch_threshold = PACMAN_RADIUS + 0.22
        if self.mode == 'pounce':
            catch_threshold += 0.15  # small leniency during pounce
        self.caught_player = (dist_to_player <= catch_threshold)

        # If seeking and path finished, clear last seen and revert to wander
        if self.mode == 'seek' and (not self.current_path or self.next_path_idx >= len(self.current_path)):
            self.last_seen_rc = None
            self.mode = 'wander'

        # Visual animation
        self._update_animation(dt)

    def _follow_path_jump(self, dt):
        if not self.current_path or self.next_path_idx >= len(self.current_path):
            return
        # Next desired cell
        tr, tc = self.current_path[self.next_path_idx]
        tx, tz = self.grid_to_world(tr, tc)
        # Current pos
        cx, cy, cz = self.node.getPosition()
        # Compute desired heading
        dx = (tx - cx)
        dz = (tz - cz)
        dist = math.hypot(dx, dz)
        if dist < 0.05:
            # Arrived at next cell
            self.next_path_idx += 1
            return
        vx = dx / max(dist, 1e-6)
        vz = dz / max(dist, 1e-6)
        # Steer the next jump toward the target cell and set jump distance to one cell
        try:
            if hasattr(self.node, 'set_jump_params'):
                self.node.set_jump_params(new_forward_dir=(vx, 0.0, vz), new_jump_forward=min(CELL_SIZE * JUMP_FORWARD_FACTOR, dist))
        except Exception:
            pass
        # Smooth face for visual correctness
        desired_yaw = math.degrees(math.atan2(vx, vz))
        self.facing_yaw = self._turn_towards(self.facing_yaw, desired_yaw, PACMAN_TURN_RATE * dt)
        self.node.setEuler([self.facing_yaw, 0, 0])

    def _turn_towards(self, current, target, max_delta):
        # shortest angle
        a = (target - current + 180.0) % 360.0 - 180.0
        if a > max_delta:
            a = max_delta
        if a < -max_delta:
            a = -max_delta
        return (current + a) % 360.0

    def _update_animation(self, dt):
        self.anim_time += dt
        phase = math.sin(2.0 * math.pi * self.anim_freq * self.anim_time)
        sx = PACMAN_SCALE * (1.0 + self.anim_w_amp * max(0.0, phase))
        sy = PACMAN_SCALE * (1.0 - self.anim_h_amp * max(0.0, phase))
        sz = PACMAN_SCALE * (1.0 + self.anim_w_amp * max(0.0, phase))
        try:
            self.node.setScale([sx, sy, sz])
        except Exception:
            pass

    # -----------------------------
    # Collision helpers
    # -----------------------------
    def collides_with_point(self, pos, radius=0.25):
        px, py, pz = pos
        cx, cy, cz = self.node.getPosition()
        return math.hypot(px - cx, pz - cz) <= (PACMAN_RADIUS + radius)
