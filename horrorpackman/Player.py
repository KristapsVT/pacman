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
PLAYER_SPEED        = 6.0
PLAYER_RADIUS       = 0.22
PLAYER_MODEL_SCALE  = 0.35
PLAYER_Y_OFFSET     = 0 # raised from 0.35 to prevent feet clipping through floor
ASSET_PLAYER_GLTF   = os.path.join('assets','Person.glb')
CELL_SIZE           = 3.0  # grid cell size (must match PacManAI/KeyLoader)
PASSABLE_EMOJIS     = {'🟨','🟪','🟦'}  # tiles player can occupy / move through
CENTERING_STRENGTH  = 6.0  # higher pulls player faster toward cell center
PLAYER_COLLISION_ENABLED = False  # set True to re-enable grid collisions/centering

# Raycast-based collision (smooth, no glitching)
USE_RAYCAST_COLLISION = True  # raycast-based wall collision (recommended)
COLLISION_BUFFER    = 0.3  # distance from walls (reduced to prevent weird pushing)
COLLISION_RAYS      = 3    # 3=good balance, 1=fastest but less smooth corners
CAMERA_COLLISION_ENABLED = True  # prevent camera from going through walls
COLLISION_SIMPLE_MODE = False  # True = only 1 ray (ultra fast), False = 2-3 rays

# Debug: Set to True to disable collision temporarily (press 'V' to toggle at runtime)
DEBUG_DISABLE_COLLISION = False

# Free camera testing mode (toggle with 'C')
FREE_CAM            = False
FREE_CAM_SPEED      = 18.0  # movement speed for free cam
FREE_CAM_VERTICAL_SPEED = 12.0  # Q/E up/down

FIRST_PERSON        = True
CAMERA_DISTANCE_TP  = 6.5  # Increased from 5.5 to keep camera further back
CAMERA_HEIGHT_FP    = 1.3
CAMERA_HEIGHT_TP    = 1.6
CAMERA_MIN_HEIGHT_TP= 0.8  # Increased minimum to prevent camera from going too low

PITCH_LIMIT         = 85.0
MOUSE_SENS_DEG      = 0.15

INVERT_Y_FP         = True
INVERT_Y_TP         = True

CAMERA_SMOOTH_TP    = False
CAMERA_DAMPING_TP   = 14.0

mouse_locked        = True

# Facing behavior for TP (disabled - now uses FP-style movement)
FACE_STRAFE_ONLY    = False    # False = player faces camera direction like FP
STRAFE_FACE_OFFSET  = 90.0

# Smooth movement in third person (disabled - now matches FP exactly)
PLAYER_ROTATION_SMOOTH = False  # False = instant rotation like FP
PLAYER_ROTATION_SPEED = 12.0   # rotation speed (not used when smooth=False)
PLAYER_ACCEL_TIME = 0.15       # time to reach full speed (not used)

# Pac-Man AI Configuration
PACMAN_JUMP_DISTANCE = 3.0  # Pac-Man jump distance in units (default CELL_SIZE)

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
        # Shift player to the right by adjusting X offset
        x_offset = cx - 0.5  # Added -0.5 to shift right
        raw.setPosition([x_offset,liftY,-cz])
    except:
        raw.setPosition([-0.5,1.75,0])  # Also shift fallback position right


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
player_target_yaw = 0.0  # target yaw for smooth rotation
player_velocity = 0.0    # current velocity for smooth acceleration
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
# Raycast-based Collision Detection (Optimized for Performance)
# -----------------------------
def check_collision_raycast(from_pos, to_pos, check_height=1.0):
    """Check if movement from from_pos to to_pos would collide with walls using raycasts.
    Returns: (collided, safe_pos) - safe_pos is the furthest safe position along the path.
    OPTIMIZED: Uses only 2-3 raycasts instead of 24 for 10x+ performance improvement.
    """
    if not USE_RAYCAST_COLLISION or DEBUG_DISABLE_COLLISION:
        return False, to_pos
    
    fx, fy, fz = from_pos
    tx, ty, tz = to_pos
    
    # Calculate movement vector
    dx = tx - fx
    dz = tz - fz
    move_dist = math.hypot(dx, dz)
    
    if move_dist < 1e-6:
        return False, to_pos
    
    # Normalize direction
    dir_x = dx / move_dist
    dir_z = dz / move_dist
    
    collided = False
    min_safe_fraction = 1.0
    
    # Test at player center height (not too low to avoid floor, not too high)
    test_y = fy + 0.8  # Fixed height above player base to avoid floor
    
    # Main forward ray (most important)
    ray_start = [fx, test_y, fz]
    ray_end = [tx, test_y, tz]
    
    try:
        info = viz.intersect(ray_start, ray_end)
        if info.valid:
            hit_point = info.point
            # Ignore hits that are below or above player (likely floor/ceiling)
            hit_height = hit_point[1]
            if abs(hit_height - test_y) < 0.8:  # Increased tolerance to catch walls better
                # Hit something at player level - calculate safe distance
                hit_dist = math.hypot(hit_point[0] - fx, hit_point[2] - fz)
                safe_dist = max(0, hit_dist - COLLISION_BUFFER)
                safe_fraction = safe_dist / move_dist if move_dist > 0 else 0
                min_safe_fraction = safe_fraction
                collided = True
    except Exception as e:
        # If raycast fails, allow movement (better than being stuck)
        pass
    
    # Only add side rays if we have budget for it (reduces from 8 to 2)
    if COLLISION_RAYS > 1 and not collided and not COLLISION_SIMPLE_MODE:
        # Just check left and right at ±30 degrees for corners
        for angle_offset in [-30.0, 30.0]:
            angle_rad = math.radians(angle_offset)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            rotated_x = dir_x * cos_a - dir_z * sin_a
            rotated_z = dir_x * sin_a + dir_z * cos_a
            
            ray_length = move_dist + COLLISION_BUFFER
            ray_end_rot = [fx + rotated_x * ray_length, test_y, fz + rotated_z * ray_length]
            
            try:
                info = viz.intersect(ray_start, ray_end_rot)
                if info.valid:
                    hit_point = info.point
                    hit_height = hit_point[1]
                    # Only count hits at similar height (not floor/ceiling)
                    if abs(hit_height - test_y) < 0.8:
                        hit_dist = math.hypot(hit_point[0] - fx, hit_point[2] - fz)
                        safe_dist = max(0, hit_dist - COLLISION_BUFFER)
                        safe_fraction = safe_dist / move_dist if move_dist > 0 else 0
                        min_safe_fraction = min(min_safe_fraction, safe_fraction)
                        collided = True
                        break  # Stop after first hit for speed
            except:
                pass
    
    if collided and min_safe_fraction < 1.0:
        # Calculate safe position
        safe_x = fx + dir_x * (move_dist * min_safe_fraction)
        safe_z = fz + dir_z * (move_dist * min_safe_fraction)
        return True, [safe_x, ty, safe_z]
    
    return collided, to_pos

def slide_collision(from_pos, desired_pos, check_height=1.0):
    """Try to move to desired_pos. If blocked, try sliding along the wall.
    Returns: final_position after collision resolution.
    OPTIMIZED: Only does extra raycasts if actually needed.
    """
    # First try direct movement (1 raycast)
    collided, safe_pos = check_collision_raycast(from_pos, desired_pos, check_height)
    
    if not collided:
        return desired_pos
    
    # Only if blocked, try sliding (adds 1-2 more raycasts)
    fx, fy, fz = from_pos
    dx, dy, dz = desired_pos
    
    # Calculate how much we moved with safe_pos
    moved_dist = math.hypot(safe_pos[0] - fx, safe_pos[2] - fz)
    
    # If we moved at least a little, use that
    if moved_dist > 0.01:
        return safe_pos
    
    # If we barely moved, try sliding along axes
    # Try X-only movement (1 raycast)
    x_only_pos = [dx, fy, fz]
    x_collided, x_safe = check_collision_raycast(from_pos, x_only_pos, check_height)
    if not x_collided:
        return x_only_pos
    
    # Try Z-only movement (1 raycast)
    z_only_pos = [fx, fy, dz]
    z_collided, z_safe = check_collision_raycast(from_pos, z_only_pos, check_height)
    if not z_collided:
        return z_only_pos
    
    # Use whichever partial movement is better
    x_dist = abs(x_safe[0] - fx)
    z_dist = abs(z_safe[2] - fz)
    if x_dist > z_dist and x_dist > 0.005:
        return x_safe
    elif z_dist > 0.005:
        return z_safe
    
    # Last resort: return safe_pos even if minimal movement
    return safe_pos

def check_camera_collision(cam_pos, target_pos):
    """Check if camera position would be inside a wall. Returns adjusted safe position."""
    if not CAMERA_COLLISION_ENABLED:
        return cam_pos
    
    # First ensure camera maintains minimum distance from player
    tx, ty, tz = target_pos
    cx, cy, cz = cam_pos
    
    # Calculate distance from player
    dist_to_player = math.sqrt((cx-tx)**2 + (cy-ty)**2 + (cz-tz)**2)
    min_distance = 0  # Minimum camera distance from player
    
    if dist_to_player < min_distance:
        # Push camera away to maintain minimum distance
        if dist_to_player > 0.01:
            scale = min_distance / dist_to_player
            cx = tx + (cx - tx) * scale
            cy = ty + (cy - ty) * scale
            cz = tz + (cz - tz) * scale
        else:
            # Camera is exactly at player, push back
            cx = tx
            cy = ty + 1.0
            cz = tz - min_distance
        cam_pos = [cx, cy, cz]
    
    try:
        # Cast ray from target (player) to camera position
        info = viz.intersect(target_pos, cam_pos)
        if info.valid:
            # Hit wall between player and camera - pull camera forward
            hit_point = info.point
            # Place camera slightly in front of the hit point
            hx, hy, hz = hit_point
            
            # Direction from target to hit
            dx = hx - tx
            dy = hy - ty
            dz = hz - tz
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)
            
            if dist > 0.01:
                # Normalize and pull back by buffer
                dx /= dist
                dy /= dist
                dz /= dist
                
                safe_dist = max(min_distance, dist - COLLISION_BUFFER)
                return [tx + dx * safe_dist, ty + dy * safe_dist, tz + dz * safe_dist]
    except:
        pass
    
    return cam_pos

# Allow external launcher to inject Pac-Man AI by setting EXTERNAL_PACMAN_AI env var
if not os.environ.get('EXTERNAL_PACMAN_AI'):
    pacman_ai = None
    def _spawn_pacman_ai():
        global pacman_ai
        if pacman_ai is None:
            try:
                # Pass jump distance from Player config to Pac-Man AI
                pacman_ai = PacManChaser(map_root=pacmap_root)
                # Update jump distance if Pac-Man has animation
                if hasattr(pacman_ai, 'node') and pacman_ai.node:
                    try:
                        # Try to update jump distance on the animation node
                        if hasattr(pacman_ai.node, '_jump_forward'):
                            pacman_ai.node._jump_forward = PACMAN_JUMP_DISTANCE
                    except:
                        pass
                print('[PacMan] AI spawned after 3s delay (jump distance: %.1f)' % PACMAN_JUMP_DISTANCE)
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

def toggle_collision_debug():
    global DEBUG_DISABLE_COLLISION
    DEBUG_DISABLE_COLLISION = not DEBUG_DISABLE_COLLISION
    print('[Debug] Collision', 'DISABLED' if DEBUG_DISABLE_COLLISION else 'ENABLED')
vizact.onkeydown('v', toggle_collision_debug)

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
def update_camera(dt):
    global last_cam_pos, free_cam_pos
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
            cam_x = target[0] - dir_x * CAMERA_DISTANCE_TP
            cam_y = target[1] - dir_y * CAMERA_DISTANCE_TP
            cam_z = target[2] - dir_z * CAMERA_DISTANCE_TP
            cam_y = max(cam_y, CAMERA_MIN_HEIGHT_TP)  # keep slightly above floor
            
            # Apply camera collision to prevent going through walls
            raw_cam_pos = [cam_x, cam_y, cam_z]
            desired = check_camera_collision(raw_cam_pos, target)
            
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
    # Check if game over has been triggered
    try:
        import GameOver
        if GameOver.is_game_over():
            return  # Stop all updates if game over
    except Exception:
        pass
    
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
            
            # Calculate desired new position
            desired_x = x + vx*PLAYER_SPEED*dt
            desired_z = z + vz*PLAYER_SPEED*dt
            desired_pos = [desired_x, y, desired_z]
            
            if USE_RAYCAST_COLLISION and not DEBUG_DISABLE_COLLISION:
                # Use raycast collision with sliding
                from_pos = [x, y, z]
                final_pos = slide_collision(from_pos, desired_pos, check_height=CAMERA_HEIGHT_FP)
                # Only update if actually moved
                if abs(final_pos[0] - x) > 1e-6 or abs(final_pos[2] - z) > 1e-6:
                    player.setPosition(final_pos)
                    moved = True
            elif PLAYER_COLLISION_ENABLED:
                # Grid-based collision attempt (legacy)
                nx = desired_x
                nz = desired_z
                rc_full = _world_to_grid(nx,nz)
                if rc_full is None or _is_passable_rc(*rc_full):
                    player.setPosition([nx, y, nz])
                    moved = True
                else:
                    # try X only
                    rc_x = _world_to_grid(nx,z)
                    if rc_x is not None and _is_passable_rc(*rc_x):
                        player.setPosition([nx, y, z])
                        moved = True
                    # try Z only
                    rc_z = _world_to_grid(x,nz)
                    if rc_z is not None and _is_passable_rc(*rc_z):
                        player.setPosition([x, y, nz])
                        moved = True
            else:
                # Free movement (no collisions)
                player.setPosition([desired_x, y, desired_z])
                moved = True

        # Optional centering only when collisions are enabled
        if PLAYER_COLLISION_ENABLED:
            x_cur,y_cur,z_cur = player.getPosition()
            rc = _world_to_grid(x_cur,z_cur)
            if rc is not None and _is_passable_rc(*rc):
                cc = _cell_center_world(*rc)
                if cc:
                    cx, cz = cc
                    dx = cx - x_cur
                    dz = cz - z_cur
                    dist = math.hypot(dx,dz)
                    if dist > 1e-6:
                        pull = CENTERING_STRENGTH * dt
                        if pull > 1.0: pull = 1.0
                        px_new = x_cur + dx * pull
                        pz_new = z_cur + dz * pull
                        player.setPosition([px_new,y_cur,pz_new])

        global player_yaw, player_target_yaw, player_velocity
        if not FIRST_PERSON:
            # Rotate player to face movement direction (only if moving)
            # Rotation happens AFTER position update to prevent drift
            if moved and (mx != 0 or mz != 0):
                # Calculate direction player is moving
                movement_yaw = math.degrees(math.atan2(vx, vz))
                player_yaw = movement_yaw
                # Set rotation without affecting position
                player.setEuler([player_yaw, 0, 0])

    # Update Pac-Man chaser AI
    # Update Pac-Man chaser AI (still based on player position, even in free cam)
    try:
        px, py, pz = player.getPosition()
        pacman_ai.update(dt, (px, py, pz))
        if pacman_ai.collides_with_point((px, py, pz), radius=PLAYER_RADIUS):
            print('[PacMan] Collision: player caught!')
            # Play death sound (defensive import)
            try:
                import Ambience
                Ambience.play_death_sound()
            except Exception:
                pass
            # Trigger game over sequence
            try:
                import GameOver
                GameOver.show_game_over_and_close()
            except Exception as e:
                print('[Player] Failed to trigger game over:', e)
    except Exception:
        pass

vizact.ontimer(0,on_update)

# -----------------------------
# Info
# -----------------------------
print('Controls:')
print('  Move: W A S D')
print('  Quit:    Esc')
print('  Mouse lock ON/OFF: Tab')
print('  FP/TP toggle: F (InvertY FP:', INVERT_Y_FP, ', InvertY TP:', INVERT_Y_TP, ')')
print('  Free Cam toggle: C (WASD move, Q/E vertical)')
print('Assets:', ASSET_PLAYER_GLTF)
