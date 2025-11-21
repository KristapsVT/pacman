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

# -----------------------------
# Config
# -----------------------------
PLAYER_SPEED        = 12.0
PLAYER_RADIUS       = 0.22
PLAYER_MODEL_SCALE  = 0.35
PLAYER_Y_OFFSET     = 0.35
ASSET_PLAYER_GLTF   = os.path.join('assets','Person.glb')

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

try: from window_utils import _maximize_window; _maximize_window()
except Exception: _maximize_window = lambda: None

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
# Allow external launcher to inject Pac-Man AI by setting EXTERNAL_PACMAN_AI env var
if not os.environ.get('EXTERNAL_PACMAN_AI'):
    pacman_ai = PacManChaser(map_root=pacmap_root)
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
            player.setPosition([x + vx*PLAYER_SPEED*dt, y, z + vz*PLAYER_SPEED*dt])
            moved = True

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