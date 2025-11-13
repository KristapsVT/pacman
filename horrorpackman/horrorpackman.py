# First/Third-person movement + rotation with true vertical orbit in TP:
# - Third-person pitch now rotates camera up/down (no zoom-in effect)
# - First-person unchanged (eye position)
# - Movement ignores pitch (horizontal plane only)
# Controls: W A S D move, R restart, Esc quit, Tab toggle mouse lock, F toggle FP/TP

import viz
import vizact
import vizshape
import math
import os

# -----------------------------
# Config
# -----------------------------
ARENA_SIZE          = 20.0
PLAYER_SPEED        = 4.0
PLAYER_RADIUS       = 0.22
PLAYER_MODEL_SCALE  = 0.35
PLAYER_Y_OFFSET     = 0.35
ASSET_PLAYER_GLTF   = os.path.join('assets','Person.glb')

FIRST_PERSON        = True
CAMERA_DISTANCE_TP  = 5.5
CAMERA_HEIGHT_FP    = 1.3
CAMERA_HEIGHT_TP    = 1.3          # Base (target) height the camera looks at in TP
CAMERA_MIN_HEIGHT_TP= 0.25          # Prevent TP camera dipping below ground

PITCH_LIMIT         = 85.0

MOUSE_SENS_DEG      = 0.15
INVERT_Y            = True if FIRST_PERSON else False   # FP invert, TP normal

CAMERA_SMOOTH_TP    = True
CAMERA_DAMPING_TP   = 14.0

mouse_locked        = True

# Shadow
SHADOW_Y            = 0.01
SHADOW_OFFSET_XZ    = (0.0, 0.0)

# Facing behavior
FACE_STRAFE_ONLY    = True
STRAFE_FACE_OFFSET  = 90.0  # degrees offset for left/right strafe facing

# -----------------------------
# Helpers
# -----------------------------
def clamp(v,a,b): return max(a,min(v,b))
def lerp(a,b,t): return a + (b-a)*t
def lerp3(a,b,t): return [lerp(a[i],b[i],t) for i in range(3)]
def exp_smooth_factor(damping, dt):
    try: return 1.0 - math.exp(-damping*dt)
    except: return min(1.0, damping*dt)

def within_arena(node, radius=PLAYER_RADIUS):
    x,y,z = node.getPosition()
    half = ARENA_SIZE*0.5 - radius
    x = clamp(x,-half,half)
    z = clamp(z,-half,half)
    node.setPosition([x,y,z])

def _get_sphere_center(raw):
    try:
        sx,sy,sz,sr = raw.getBoundingSphere()
        return sx,sy,sz
    except:
        return None

def _center_glb_local_in_wrapper(raw):
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

def load_player_model():
    if os.path.exists(ASSET_PLAYER_GLTF):
        try:
            wrapper = viz.addGroup()
            raw = viz.addChild(ASSET_PLAYER_GLTF)
            raw.setParent(wrapper)
            raw.setScale([PLAYER_MODEL_SCALE]*3)
            _center_glb_local_in_wrapper(raw)
            print('[Model] Loaded:', ASSET_PLAYER_GLTF)
            return wrapper
        except Exception as e:
            print('[Model] Load error:', e)
    else:
        print('[Model] Not found, using primitive ->', ASSET_PLAYER_GLTF)
    g = viz.addGroup()
    head = vizshape.addSphere(radius=PLAYER_RADIUS,slices=24,stacks=18)
    head.color(0.9,0.85,0.15); head.setParent(g)
    body = vizshape.addCylinder(height=0.5,radius=0.15,axis=vizshape.AXIS_Y)
    body.color(0.2,0.6,1.0); body.setParent(g); body.setPosition([0,-0.3,0])
    return g

# -----------------------------
# Init
# -----------------------------
viz.setMultiSample(4)
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

# Lighting & arena
light = viz.addLight(); light.position(0,8,0); light.color(1,1,1); light.enable()
try:
    viz.addAmbientLight(color=[0.35,0.35,0.38])
except:
    pass

floor = vizshape.addPlane(size=[ARENA_SIZE,ARENA_SIZE], axis=vizshape.AXIS_Y)
floor.color(0.30,0.31,0.32)

border_thick = 0.1
for x in [-ARENA_SIZE/2,ARENA_SIZE/2]:
    w = vizshape.addBox([border_thick,0.6,ARENA_SIZE])
    w.setPosition([x,0.3,0]); w.color(0.15,0.15,0.15)
for z in [-ARENA_SIZE/2,ARENA_SIZE/2]:
    w = vizshape.addBox([ARENA_SIZE,0.6,border_thick])
    w.setPosition([0,0.3,z]); w.color(0.15,0.15,0.15)

# -----------------------------
# Player & Shadow
# -----------------------------
player = load_player_model()
player.setPosition([0,PLAYER_Y_OFFSET,0])
player_yaw = 0.0
player.visible(False if FIRST_PERSON else True)

shadow = vizshape.addCircle(radius=0.34,axis=vizshape.AXIS_Y,slices=48)
shadow.color(0,0,0); shadow.alpha(0.30); shadow.disable(viz.LIGHTING)
shadow.setPosition([0,SHADOW_Y,0])

# -----------------------------
# Input
# -----------------------------
keys = {'w':False,'a':False,'s':False,'d':False}
def set_key(k,s): keys[k]=s
for k in ['w','a','s','d']:
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
    global FIRST_PERSON,last_cam_pos,INVERT_Y
    FIRST_PERSON = not FIRST_PERSON
    INVERT_Y = True if FIRST_PERSON else False
    print('[Camera] FIRST_PERSON:', FIRST_PERSON, '| INVERT_Y:', INVERT_Y)
    last_cam_pos = None
    player.visible(False if FIRST_PERSON else True)
vizact.onkeydown('f', toggle_perspective)

# -----------------------------
# Camera state + mouse callback
# -----------------------------
cam_yaw   = 0.0
cam_pitch = 5.0
last_cam_pos = None

def _on_mouse_move(e):
    if not mouse_locked: return
    dx = getattr(e,'dx',0.0); dy = getattr(e,'dy',0.0)
    if dx == 0.0 and dy == 0.0: return
    global cam_yaw, cam_pitch
    cam_yaw += dx * MOUSE_SENS_DEG
    delta_pitch = dy * MOUSE_SENS_DEG
    if not INVERT_Y:
        delta_pitch = -delta_pitch
    cam_pitch += delta_pitch
    cam_pitch = clamp(cam_pitch, -PITCH_LIMIT, PITCH_LIMIT)

if hasattr(viz,'MOUSE_MOVE_EVENT'):
    viz.callback(viz.MOUSE_MOVE_EVENT, _on_mouse_move)
else:
    print('[Mouse] viz.MOUSE_MOVE_EVENT not available; mouselook needs that event.')

# -----------------------------
# Camera update
# -----------------------------
def update_camera(dt):
    global last_cam_pos
    yaw_rad   = math.radians(cam_yaw)
    pitch_rad = math.radians(cam_pitch)

    # 3D direction (for camera orbit & FP look)
    dir_x = math.sin(yaw_rad) * math.cos(pitch_rad)
    dir_y = math.sin(pitch_rad)
    dir_z = math.cos(yaw_rad) * math.cos(pitch_rad)

    # Horizontal forward (ignore pitch) for movement/facing
    hfx = math.sin(yaw_rad)
    hfz = math.cos(yaw_rad)

    px,py,pz = player.getPosition()

    if FIRST_PERSON:
        target = [px, py + CAMERA_HEIGHT_FP, pz]
        desired = target[:]  # camera at eye
        look_at = [target[0] + dir_x*3.0, target[1] + dir_y*3.0, target[2] + dir_z*3.0]
    else:
        # TP: orbit using full pitch (spherical), constant distance
        target = [px, py + CAMERA_HEIGHT_TP, pz]
        cam_x = target[0] - dir_x * CAMERA_DISTANCE_TP
        cam_y = target[1] - dir_y * CAMERA_DISTANCE_TP
        cam_z = target[2] - dir_z * CAMERA_DISTANCE_TP
        # Prevent camera going below a floor threshold
        cam_y = max(cam_y, CAMERA_MIN_HEIGHT_TP)
        desired = [cam_x, cam_y, cam_z]
        look_at = target

    if last_cam_pos is None:
        last_cam_pos = desired[:]

    cam_pos = desired
    if (not FIRST_PERSON) and CAMERA_SMOOTH_TP:
        t = exp_smooth_factor(CAMERA_DAMPING_TP, dt)
        last_cam_pos = lerp3(last_cam_pos, desired, t)
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

    # Horizontal basis
    right_x = hfz
    right_z = -hfx

    mx = (1 if keys['d'] else 0) - (1 if keys['a'] else 0)   # strafe
    mz = (1 if keys['w'] else 0) - (1 if keys['s'] else 0)   # forward/back

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
            # Pure strafe left/right facing
            if mx < 0:
                player_yaw = cam_yaw - STRAFE_FACE_OFFSET
            else:
                player_yaw = cam_yaw + STRAFE_FACE_OFFSET
            player.setEuler([player_yaw,0,0])
        elif moved:
            # Face movement direction
            player_yaw = math.degrees(math.atan2(vx,vz))
            player.setEuler([player_yaw,0,0])

    within_arena(player, PLAYER_RADIUS)

    # Shadow follows player
    px,py,pz = player.getPosition()
    offx, offz = SHADOW_OFFSET_XZ
    shadow.setPosition([px + offx, SHADOW_Y, pz + offz])

vizact.ontimer(0,on_update)

# -----------------------------
# Info
# -----------------------------
print('Controls:')
print('  Move: W A S D')
print('  A/D pure strafe faces left/right (TP), W/S faces movement direction.')
print('  Restart: R')
print('  Quit:    Esc')
print('  Mouse lock ON/OFF: Tab')
print('  FP/TP toggle: F (FP invertY=True, TP invertY=False)')
print('Model:', ASSET_PLAYER_GLTF)
print('Sensitivity (deg/pixel):', MOUSE_SENS_DEG, 'InvertY (current):', INVERT_Y)
print('TP orbit distance:', CAMERA_DISTANCE_TP, 'TP min height:', CAMERA_MIN_HEIGHT_TP)