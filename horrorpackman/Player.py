# First/Third-person movement + rotation with unified FP-like camera control in TP
# - TP camera uses the same yaw/pitch control as FP (mouse deltas)
# - Pac-Man removed from the scene (no model, no animation, no updates)
# - Shadows and arena borders previously removed
# Controls: W/A/S/D move player, R restart, Esc quit, Tab toggle mouse lock, F toggle FP/TP

import viz
import vizact
import vizshape
import math
import os
import random
from MapLoader import build_and_attach_map
from PacManAI import PacManChaser
import codecs

# -----------------------------
# Config
# -----------------------------
PLAYER_SPEED        = 12.0
PLAYER_RADIUS       = 0.22
PLAYER_MODEL_SCALE  = 0.35
PLAYER_Y_OFFSET     = 0.35
ASSET_PLAYER_GLTF   = os.path.join('assets','Person.glb')
CELL_SIZE           = 3.0  # grid cell size (must match PacManAI/KeyLoader)
PASSABLE_EMOJIS     = {'🟨','🟪','🟦'}  # tiles player can occupy / move through
CENTERING_STRENGTH  = 6.0  # higher pulls player faster toward cell center
PLAYER_COLLISION_ENABLED = True  # enables smooth grid-based wall collisions

# Collision configuration
COLLISION_PADDING   = 0.35  # distance from wall center to keep player away
COLLISION_SMOOTH    = True  # use smooth wall sliding instead of hard stops

# Free camera testing mode (toggle with 'C')
FREE_CAM            = False
FREE_CAM_SPEED      = 18.0  # movement speed for free cam
FREE_CAM_VERTICAL_SPEED = 12.0  # Q/E up/down

FIRST_PERSON        = True
CAMERA_DISTANCE_TP  = 5.5
CAMERA_HEIGHT_FP    = 1.3
CAMERA_HEIGHT_TP    = 1.3
CAMERA_MIN_HEIGHT_TP= 0.25

PITCH_LIMIT         = 85.0
MOUSE_SENS_DEG      = 0.15

INVERT_Y_FP         = True
INVERT_Y_TP         = True

CAMERA_SMOOTH_TP    = False
CAMERA_DAMPING_TP   = 14.0

# Camera collision configuration (prevents camera clipping through walls)
CAMERA_COLLISION_ENABLED = True  # enables ray-based camera collision
CAMERA_COLLISION_RADIUS  = 0.3   # minimum distance camera keeps from walls
CAMERA_COLLISION_SMOOTH  = 12.0  # smoothing factor for camera collision adjustment

mouse_locked        = True

# Facing behavior for TP
FACE_STRAFE_ONLY    = True
STRAFE_FACE_OFFSET  = 90.0

# -----------------------------
# Helpers
# -----------------------------
def clamp(v,a,b): return max(a,min(v,b))
def lerp(a,b,t): return a + (b-a)*t

def _get_sphere_center(raw):
    try:
        sx,sy,sz,sr = raw.getBoundingSphere()
        return sx,sy,sz
    except:
        return None

def _center_glb_local_in_wrapper(raw):
    """Center raw model inside a wrapper so wrapper origin is near the visual center (XZ), bottom aligned."""
    try:
        minX,minY,minZ,maxX,maxY,maxZ = raw.getBoundingBox()
        cx = (minX+maxX)*0.5
        cz = (minZ+maxZ)*0.5
        sc = _get_sphere_center(raw)
        if sc:
            sx,_,sz = sc
            a=0.6
            cx = cx*(1-a)+sx*a
            cz = cz*(1-a)+sz*a
        desiredBottom = 1.75
        liftY = desiredBottom - minY
        raw.setPosition([-cx,liftY,-cz])
    except:
        raw.setPosition([0,1.75,0])

def load_model(asset_path, scale, tint=None, fallback_color=(0.9,0.85,0.15)):
    if os.path.exists(asset_path):
        try:
            wrapper = viz.addGroup()
            raw = viz.addChild(asset_path)
            raw.setParent(wrapper)
            raw.setScale([scale]*3)
            _center_glb_local_in_wrapper(raw)
            if tint is not None:
                try:
                    wrapper.color(*tint)
                except:
                    pass
            print('[Model] Loaded:', asset_path)
            return wrapper
        except Exception as e:
            print('[Model] Load error for', asset_path, ':', e)
    # fallback primitive if asset not found or failed to load
    print('[Model] Not found, using primitive ->', asset_path)
    g = viz.addGroup()
    head = vizshape.addSphere(radius=PLAYER_RADIUS,slices=24,stacks=18)
    base_color = tint if tint is not None else fallback_color
    try:
        head.color(*base_color)
    except:
        pass
    head.setParent(g)
    body = vizshape.addCylinder(height=0.5,radius=0.15,axis=vizshape.AXIS_Y)
    try:
        body.color(0.2,0.6,1.0)
    except:
        pass
    body.setParent(g); body.setPosition([0,-0.3,0])
    g.setScale([scale]*3)
    if tint is not None:
        try:
            g.color(*tint)
        except:
            pass
    return g

# -----------------------------
# Init
# -----------------------------
viz.setMultiSample(4)

# Launch the viz runtime (fullscreen preference requested above)
viz.go()
viz.clearcolor(0.10,0.10,0.14)
viz.mouse.setOverride(viz.ON)

def apply_mouse_lock():
    if mouse_locked:
        viz.mouse.setVisible(False)
        viz.mouse.setTrap(viz.ON)
    else:
        viz.mouse.setTrap(viz.OFF)
        viz.mouse.setVisible(True)
apply_mouse_lock()

# -----------------------------
# Player
# -----------------------------
player = load_model(ASSET_PLAYER_GLTF, PLAYER_MODEL_SCALE)
player.setPosition([0,PLAYER_Y_OFFSET,0])
player_yaw = 0.0
player.visible(False if FIRST_PERSON else True)

# -----------------------------
# Map + Pac-Man chaser
# -----------------------------
pacmap_root = build_and_attach_map()
# -----------------------------
# Grid load (Map_Grid.txt) for collision/path restriction
# -----------------------------
_grid = []
_grid_rows = 0
_grid_cols = 0
_grid_origin_x = 0.0
_grid_origin_z = 0.0
try:
    _grid_path = os.path.normpath(os.path.join(os.path.dirname(__file__),'..','Map_Grid.txt'))
    if os.path.exists(_grid_path):
        with codecs.open(_grid_path,'r',encoding='utf-8') as f:
            raw_lines = [ln.rstrip('\n') for ln in f.readlines() if ln.strip()]
        _grid = [list(line) for line in raw_lines]
        _grid_rows = len(_grid)
        _grid_cols = max((len(r) for r in _grid), default=0)
        if pacmap_root is not None and hasattr(pacmap_root,'_pacmap_center'):
            cx, cz = pacmap_root._pacmap_center
        else:
            cx = cz = 0.0
        grid_w = _grid_cols * CELL_SIZE
        grid_d = _grid_rows * CELL_SIZE
        _grid_origin_x = cx - (grid_w/2.0) + (CELL_SIZE/2.0)
        _grid_origin_z = cz - (grid_d/2.0) + (CELL_SIZE/2.0)
        print('[Map] Player grid loaded rows=%d cols=%d origin=(%.2f,%.2f)' % (_grid_rows,_grid_cols,_grid_origin_x,_grid_origin_z))
    else:
        print('[Map] Grid file missing for player collision -> no wall blocking')
except Exception as e:
    print('[Map] Grid load error:', e)

def _world_to_grid(x,z):
    if _grid_rows == 0 or _grid_cols == 0:
        return None
    gx = (x - _grid_origin_x) / CELL_SIZE
    gz = (z - _grid_origin_z) / CELL_SIZE
    grid_r = int(round(gz))
    c = int(round(gx))
    r = (_grid_rows - 1 - grid_r)
    if r < 0 or c < 0 or r >= _grid_rows or c >= _grid_cols:
        return None
    return (r,c)

def _is_passable_rc(r,c):
    if r is None or c is None: return True
    if r < 0 or c < 0 or r >= _grid_rows or c >= _grid_cols: return False
    row = _grid[r]
    tile = row[c] if c < len(row) else None
    return tile in PASSABLE_EMOJIS

def _cell_center_world(r,c):
    if r is None or c is None: return None
    grid_r = (_grid_rows - 1 - r)
    cx = _grid_origin_x + c * CELL_SIZE
    cz = _grid_origin_z + grid_r * CELL_SIZE
    return (cx, cz)

# -----------------------------
# Smooth Collision System
# -----------------------------
def _world_to_grid_continuous(x,z):
    """Return continuous grid coordinates (not rounded) for smoother collision."""
    if _grid_rows == 0 or _grid_cols == 0:
        return None
    gx = (x - _grid_origin_x) / CELL_SIZE
    gz = (z - _grid_origin_z) / CELL_SIZE
    return (gx, gz)

def _is_position_passable(x, z, padding=0.0):
    """Check if a world position is passable, with optional padding from cell edges."""
    if _grid_rows == 0 or _grid_cols == 0:
        return True
    
    # Check the cell at this position
    rc = _world_to_grid(x, z)
    if rc is None:
        return False
    if not _is_passable_rc(*rc):
        return False
    
    # If padding is requested, check nearby cells too
    if padding > 0:
        # Check cells in a small radius
        for dx in [-padding, 0, padding]:
            for dz in [-padding, 0, padding]:
                if dx == 0 and dz == 0:
                    continue
                test_rc = _world_to_grid(x + dx, z + dz)
                if test_rc is None:
                    continue
                # If test cell is different and not passable, we're too close to a wall
                if test_rc != rc and not _is_passable_rc(*test_rc):
                    # Check if we're actually close enough to care
                    cc = _cell_center_world(*test_rc)
                    if cc:
                        wall_cx, wall_cz = cc
                        dist_to_wall = math.hypot(x - wall_cx, z - wall_cz)
                        if dist_to_wall < (CELL_SIZE * 0.5 + padding):
                            return False
    return True

def _resolve_wall_collision(x, z, new_x, new_z, radius):
    """Resolve collision with walls using smooth sliding.
    
    Returns the corrected (x, z) position that doesn't penetrate walls.
    Uses a sliding approach to allow movement along walls without getting stuck.
    """
    if _grid_rows == 0 or _grid_cols == 0:
        return new_x, new_z
    
    # Check if new position is valid
    rc_new = _world_to_grid(new_x, new_z)
    if rc_new is not None and _is_passable_rc(*rc_new):
        # Additional check: ensure we're not too close to adjacent walls
        final_x, final_z = new_x, new_z
        
        # Check all 4 adjacent cells for walls and push away if too close
        current_rc = _world_to_grid(new_x, new_z)
        if current_rc:
            r, c = current_rc
            cell_center = _cell_center_world(r, c)
            if cell_center:
                cc_x, cc_z = cell_center
                
                # Check adjacent cells and push player away from walls
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    adj_r, adj_c = r + dr, c + dc
                    if not _is_passable_rc(adj_r, adj_c):
                        # This adjacent cell is a wall
                        wall_center = _cell_center_world(adj_r, adj_c)
                        if wall_center:
                            wall_x, wall_z = wall_center
                            # Distance from player to wall center
                            dist = math.hypot(final_x - wall_x, final_z - wall_z)
                            # Minimum safe distance (half cell + player radius)
                            safe_dist = CELL_SIZE * 0.5 + radius
                            if dist < safe_dist and dist > 0:
                                # Push player away from wall
                                push_x = (final_x - wall_x) / dist
                                push_z = (final_z - wall_z) / dist
                                push_amount = (safe_dist - dist)
                                final_x += push_x * push_amount
                                final_z += push_z * push_amount
        
        return final_x, final_z
    
    # New position is blocked - try sliding along walls
    # Try X movement only
    rc_x = _world_to_grid(new_x, z)
    x_ok = rc_x is not None and _is_passable_rc(*rc_x)
    
    # Try Z movement only  
    rc_z = _world_to_grid(x, new_z)
    z_ok = rc_z is not None and _is_passable_rc(*rc_z)
    
    if x_ok and z_ok:
        # Both work, pick the one with larger movement
        if abs(new_x - x) > abs(new_z - z):
            return new_x, z
        else:
            return x, new_z
    elif x_ok:
        return new_x, z
    elif z_ok:
        return x, new_z
    else:
        # Can't move at all, stay in place
        return x, z

def _get_camera_safe_distance(target_x, target_y, target_z, cam_x, cam_y, cam_z):
    """Calculate safe camera distance to prevent clipping through walls.
    
    Uses ray-marching through the grid to find the first wall intersection.
    Returns the safe distance factor (0.0 to 1.0) to multiply with desired distance.
    """
    if not CAMERA_COLLISION_ENABLED or _grid_rows == 0 or _grid_cols == 0:
        return 1.0
    
    # Direction from target to camera
    dx = cam_x - target_x
    dy = cam_y - target_y
    dz = cam_z - target_z
    total_dist = math.sqrt(dx*dx + dy*dy + dz*dz)
    
    if total_dist < 0.01:
        return 1.0
    
    # Normalize direction
    dx /= total_dist
    dz /= total_dist
    
    # March along the ray checking for walls
    step_size = CELL_SIZE * 0.25  # Check every quarter cell
    num_steps = int(total_dist / step_size) + 1
    
    for i in range(1, num_steps):
        t = (i * step_size) / total_dist
        if t > 1.0:
            t = 1.0
            
        check_x = target_x + dx * (i * step_size)
        check_z = target_z + dz * (i * step_size)
        
        rc = _world_to_grid(check_x, check_z)
        if rc is None or not _is_passable_rc(*rc):
            # Found a wall - return safe distance
            safe_dist = max(0.1, (i - 1) * step_size - CAMERA_COLLISION_RADIUS)
            return safe_dist / total_dist
    
    return 1.0

# Allow external launcher to inject Pac-Man AI by setting EXTERNAL_PACMAN_AI env var
if not os.environ.get('EXTERNAL_PACMAN_AI'):
    pacman_ai = None
    def _spawn_pacman_ai():
        global pacman_ai
        if pacman_ai is None:
            try:
                pacman_ai = PacManChaser(map_root=pacmap_root)
                print('[PacMan] AI spawned after 3s delay')
            except Exception as e:
                print('[PacMan] AI spawn failed:', e)
    # 3 second delayed spawn
    vizact.ontimer(3.0, _spawn_pacman_ai)
else:
    pacman_ai = None  # external launcher will create and attach

# -----------------------------
# Input
# -----------------------------
keys = {'w':False,'a':False,'s':False,'d':False}
# Extra keys used only in free cam (Q/E vertical)
keys.update({'q':False,'e':False})
def set_key(k,s): keys[k]=s
for k in ['w','a','s','d']:
    vizact.onkeydown(k,lambda kk=k:set_key(kk,True))
    vizact.onkeyup(k,lambda kk=k:set_key(kk,False))

# Bind vertical free cam keys
for k in ['q','e']:
    vizact.onkeydown(k,lambda kk=k:set_key(kk,True))
    vizact.onkeyup(k,lambda kk=k:set_key(kk,False))

def restart():
    global player_yaw, cam_yaw, cam_pitch, last_cam_pos
    player.setPosition([0,PLAYER_Y_OFFSET,0])
    player_yaw = 0.0
    cam_yaw = 0.0
    cam_pitch = 5.0
    last_cam_pos = None
vizact.onkeydown('r', restart)
vizact.onkeydown(viz.KEY_ESCAPE, lambda: viz.quit())

def toggle_mouse():
    global mouse_locked
    mouse_locked = not mouse_locked
    apply_mouse_lock()
vizact.onkeydown(viz.KEY_TAB, toggle_mouse)

def toggle_perspective():
    global FIRST_PERSON,last_cam_pos
    FIRST_PERSON = not FIRST_PERSON
    print('[Camera] FIRST_PERSON:', FIRST_PERSON, '| InvertY FP:', INVERT_Y_FP, '| InvertY TP:', INVERT_Y_TP)
    last_cam_pos = None
    player.visible(False if FIRST_PERSON else True)
vizact.onkeydown('f', toggle_perspective)

free_cam_pos = [0.0, 1.6, 0.0]  # initialized later when toggled on
def toggle_free_cam():
    global FREE_CAM, free_cam_pos
    FREE_CAM = not FREE_CAM
    if FREE_CAM:
        free_cam_pos = viz.MainView.getPosition()[:]
        print('[Camera] Free cam ENABLED')
    else:
        print('[Camera] Free cam DISABLED (returning to player camera)')
    apply_mouse_lock()
vizact.onkeydown('c', toggle_free_cam)

# Use KeyLoader's helper to point to the nearest key (keeps logic centralized)
try:
    from KeyLoader import point_to_closest_key as _kl_point_to_closest_key
except Exception:
    _kl_point_to_closest_key = None

def point_to_closest_key_handler():
    if _kl_point_to_closest_key is None:
        print('[Key] KeyLoader not available')
        return
    res = _kl_point_to_closest_key(player=player)
    if not res:
        print('[Key] No keys spawned or no valid key positions')
        return
    yaw_target = res.get('yaw', 0.0)
    dist = res.get('distance', None)
    global cam_yaw, player_yaw
    cam_yaw = yaw_target
    player_yaw = yaw_target
    try:
        player.setEuler([player_yaw, 0, 0])
    except Exception:
        pass
    if dist is not None:
        print('[Key] Pointing to nearest key at', round(dist, 2), 'units')
    else:
        print('[Key] Pointing to nearest key')

vizact.onkeydown('k', lambda: point_to_closest_key_handler())

# -----------------------------
# Camera state + mouse callback (unified FP-like control for both FP & TP)
# -----------------------------
cam_yaw   = 0.0
cam_pitch = 5.0
last_cam_pos = None

def _effective_invert_y():
    return INVERT_Y_FP if FIRST_PERSON else INVERT_Y_TP

def _on_mouse_move(e):
    if not mouse_locked: return
    dx = getattr(e,'dx',0.0); dy = getattr(e,'dy',0.0)
    if dx == 0.0 and dy == 0.0: return
    global cam_yaw, cam_pitch
    cam_yaw += dx * MOUSE_SENS_DEG
    delta_pitch = dy * MOUSE_SENS_DEG
    if not _effective_invert_y():
        delta_pitch = -delta_pitch
    cam_pitch += delta_pitch
    cam_pitch = clamp(cam_pitch, -PITCH_LIMIT, PITCH_LIMIT)
    # If mouse is locked, re-center the OS cursor to the window center so
    # subsequent mouse movement deltas continue coming from the center.
    try:
        if mouse_locked:
            # Try window-size APIs in order of likelihood
            cx = cy = None
            try:
                if hasattr(viz, 'window') and hasattr(viz.window, 'getSize'):
                    sz = viz.window.getSize()
                    if sz and len(sz) >= 2:
                        cx = float(sz[0]) * 0.5
                        cy = float(sz[1]) * 0.5
            except Exception:
                cx = cy = None
            try:
                if (cx is None or cy is None) and hasattr(viz, 'getWindowSize'):
                    sz = viz.getWindowSize()
                    if sz and len(sz) >= 2:
                        cx = float(sz[0]) * 0.5
                        cy = float(sz[1]) * 0.5
            except Exception:
                cx = cy = None

            if cx is not None and cy is not None:
                try:
                    # viz.mouse.setPosition expects a 2-tuple/list [x,y]
                    if hasattr(viz.mouse, 'setPosition'):
                        viz.mouse.setPosition([cx, cy])
                    else:
                        # some builds expose as viz.setMousePosition
                        if hasattr(viz, 'setMousePosition'):
                            viz.setMousePosition([cx, cy])
                except Exception:
                    pass
    except Exception:
        pass

if hasattr(viz,'MOUSE_MOVE_EVENT'):
    viz.callback(viz.MOUSE_MOVE_EVENT, _on_mouse_move)
else:
    print('[Mouse] viz.MOUSE_MOVE_EVENT not available; mouselook needs that event.')

# -----------------------------
# Camera update (TP uses same yaw/pitch "view" as FP, just offset back)
# -----------------------------
_last_safe_cam_factor = 1.0  # Track last safe camera distance factor for smooth transitions

def update_camera(dt):
    global last_cam_pos, free_cam_pos, _last_safe_cam_factor
    yaw_rad   = math.radians(cam_yaw)
    pitch_rad = math.radians(cam_pitch)

    # View direction from yaw/pitch (same for FP & TP)
    dir_x = math.sin(yaw_rad) * math.cos(pitch_rad)
    dir_y = math.sin(pitch_rad)
    dir_z = math.cos(yaw_rad) * math.cos(pitch_rad)

    # Horizontal forward (ignore pitch) for movement/facing
    hfx = math.sin(yaw_rad)
    hfz = math.cos(yaw_rad)

    if FREE_CAM:
        # Free camera: position independent of player, treat like FP without player reference
        desired = free_cam_pos[:]
        look_at = [desired[0] + dir_x*3.0, desired[1] + dir_y*3.0, desired[2] + dir_z*3.0]
    else:
        px,py,pz = player.getPosition()
        if FIRST_PERSON:
            target = [px, py + CAMERA_HEIGHT_FP, pz]
            desired = target[:]  # camera at eye
            look_at = [target[0] + dir_x*3.0, target[1] + dir_y*3.0, target[2] + dir_z*3.0]
        else:
            # FP-like control: same yaw/pitch direction; camera is just pulled back by fixed distance
            target = [px, py + CAMERA_HEIGHT_TP, pz]
            
            # Calculate desired camera position
            cam_x = target[0] - dir_x * CAMERA_DISTANCE_TP
            cam_y = target[1] - dir_y * CAMERA_DISTANCE_TP
            cam_z = target[2] - dir_z * CAMERA_DISTANCE_TP
            cam_y = max(cam_y, CAMERA_MIN_HEIGHT_TP)  # keep slightly above floor
            
            # Apply camera collision to prevent clipping through walls
            if CAMERA_COLLISION_ENABLED:
                safe_factor = _get_camera_safe_distance(
                    target[0], target[1], target[2],
                    cam_x, cam_y, cam_z
                )
                # Smooth the camera distance adjustment to prevent jitter
                if safe_factor < _last_safe_cam_factor:
                    # Moving closer (hitting wall) - respond quickly
                    _last_safe_cam_factor = lerp(_last_safe_cam_factor, safe_factor, min(1.0, dt * CAMERA_COLLISION_SMOOTH * 2))
                else:
                    # Moving farther (leaving wall) - respond smoothly
                    _last_safe_cam_factor = lerp(_last_safe_cam_factor, safe_factor, min(1.0, dt * CAMERA_COLLISION_SMOOTH * 0.5))
                
                # Apply the safe distance factor
                if _last_safe_cam_factor < 1.0:
                    effective_dist = CAMERA_DISTANCE_TP * _last_safe_cam_factor
                    cam_x = target[0] - dir_x * effective_dist
                    cam_y = target[1] - dir_y * effective_dist
                    cam_z = target[2] - dir_z * effective_dist
                    cam_y = max(cam_y, CAMERA_MIN_HEIGHT_TP)
            
            desired = [cam_x, cam_y, cam_z]
            look_at = [target[0] + dir_x*0.01, target[1] + dir_y*0.01, target[2] + dir_z*0.01]

    if last_cam_pos is None:
        last_cam_pos = desired[:]

    cam_pos = desired
    if (not FIRST_PERSON) and CAMERA_SMOOTH_TP:
        t = 1.0 - math.exp(-CAMERA_DAMPING_TP * dt)
        last_cam_pos = lerp([last_cam_pos[i] for i in range(3)], desired, t) if False else [last_cam_pos[i] + (desired[i]-last_cam_pos[i]) * t for i in range(3)]
        cam_pos = last_cam_pos

    viz.MainView.setPosition(cam_pos)
    viz.MainView.lookat(look_at)
    return hfx,hfz  # horizontal forward for movement

# -----------------------------
# Frame update
# -----------------------------
def on_update():
    dt = viz.getFrameElapsed()
    hfx,hfz = update_camera(dt)

    if FREE_CAM:
        # Free camera movement (WASD horizontal, Q/E vertical)
        right_x = hfz
        right_z = -hfx
        mx = (1 if keys['d'] else 0) - (1 if keys['a'] else 0)
        mz = (1 if keys['w'] else 0) - (1 if keys['s'] else 0)
        vy = (1 if keys['e'] else 0) - (1 if keys['q'] else 0)
        if mx or mz or vy:
            vx = right_x*mx + hfx*mz
            vz = right_z*mx + hfz*mz
            l = math.hypot(vx,vz) or 1.0
            if mx or mz:
                vx /= l; vz /= l
            speed = FREE_CAM_SPEED
            free_cam_pos[0] += vx*speed*dt
            free_cam_pos[2] += vz*speed*dt
            free_cam_pos[1] += vy*FREE_CAM_VERTICAL_SPEED*dt
    else:
        # Player movement (horizontal only)
        right_x = hfz
        right_z = -hfx

        mx = (1 if keys['d'] else 0) - (1 if keys['a'] else 0)
        mz = (1 if keys['w'] else 0) - (1 if keys['s'] else 0)

        moved = False
        if mx or mz:
            vx = right_x*mx + hfx*mz
            vz = right_z*mx + hfz*mz
            l = math.hypot(vx,vz) or 1.0
            vx /= l; vz /= l
            x,y,z = player.getPosition()
            if PLAYER_COLLISION_ENABLED:
                # Smooth grid-based collision with wall sliding
                nx = x + vx*PLAYER_SPEED*dt
                nz = z + vz*PLAYER_SPEED*dt
                
                if COLLISION_SMOOTH:
                    # Use smooth collision resolution that allows wall sliding
                    final_x, final_z = _resolve_wall_collision(x, z, nx, nz, PLAYER_RADIUS + COLLISION_PADDING)
                    if abs(final_x - x) > 0.001 or abs(final_z - z) > 0.001:
                        moved = True
                    x, z = final_x, final_z
                else:
                    # Original hard collision logic
                    rc_full = _world_to_grid(nx,nz)
                    if rc_full is None or _is_passable_rc(*rc_full):
                        x, z = nx, nz
                        moved = True
                    else:
                        # try X only
                        rc_x = _world_to_grid(nx,z)
                        if rc_x is not None and _is_passable_rc(*rc_x):
                            x = nx; moved = True
                        # try Z only
                        rc_z = _world_to_grid(x,nz)
                        if rc_z is not None and _is_passable_rc(*rc_z):
                            z = nz; moved = True
            else:
                # Free movement (no grid collisions)
                x += vx*PLAYER_SPEED*dt
                z += vz*PLAYER_SPEED*dt
                moved = True
            player.setPosition([x,y,z])

        # Push player away from walls when too close (prevents getting stuck)
        if PLAYER_COLLISION_ENABLED and COLLISION_SMOOTH:
            x_cur,y_cur,z_cur = player.getPosition()
            rc = _world_to_grid(x_cur,z_cur)
            if rc is not None and _is_passable_rc(*rc):
                r, c = rc
                # Check adjacent cells for walls and push away if too close
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    adj_r, adj_c = r + dr, c + dc
                    if not _is_passable_rc(adj_r, adj_c):
                        wall_center = _cell_center_world(adj_r, adj_c)
                        if wall_center:
                            wall_x, wall_z = wall_center
                            dist = math.hypot(x_cur - wall_x, z_cur - wall_z)
                            safe_dist = CELL_SIZE * 0.5 + PLAYER_RADIUS + COLLISION_PADDING
                            if dist < safe_dist and dist > 0.01:
                                # Gently push away from wall
                                push_x = (x_cur - wall_x) / dist
                                push_z = (z_cur - wall_z) / dist
                                push_amount = (safe_dist - dist) * 0.15  # Gentle push to avoid jitter
                                x_cur += push_x * push_amount
                                z_cur += push_z * push_amount
                                player.setPosition([x_cur, y_cur, z_cur])

        global player_yaw
        if not FIRST_PERSON:
            if FACE_STRAFE_ONLY and mx != 0 and mz == 0:
                if mx < 0:
                    player_yaw = cam_yaw - STRAFE_FACE_OFFSET
                else:
                    player_yaw = cam_yaw + STRAFE_FACE_OFFSET
                player.setEuler([player_yaw,0,0])
            elif moved:
                player_yaw = math.degrees(math.atan2(vx,vz))
                player.setEuler([player_yaw,0,0])

    # Update Pac-Man chaser AI
    # Update Pac-Man chaser AI (still based on player position, even in free cam)
    try:
        px, py, pz = player.getPosition()
        pacman_ai.update(dt, (px, py, pz))
        if pacman_ai.collides_with_point((px, py, pz), radius=PLAYER_RADIUS):
            print('[PacMan] Collision: player caught!')
    except Exception:
        pass

vizact.ontimer(0,on_update)

# -----------------------------
# Info
# -----------------------------
print('Controls:')
print('  Move: W A S D')
print('  Restart: R')
print('  Quit:    Esc')
print('  Mouse lock ON/OFF: Tab')
print('  FP/TP toggle: F (InvertY FP:', INVERT_Y_FP, ', InvertY TP:', INVERT_Y_TP, ')')
print('  Free Cam toggle: C (WASD move, Q/E vertical)')
print('Assets:', ASSET_PLAYER_GLTF)