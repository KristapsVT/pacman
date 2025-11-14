# First/Third-person movement + rotation with unified FP-like camera control in TP
# - TP camera uses the same yaw/pitch control as FP (mouse deltas), with constant follow distance
# - Pac-Man (assets/PacMan.glb) moves ONLY by jumping (no ground gliding); edge reflection to avoid "teleports"
# - Shadows removed
# - Pac-Man squash & stretch now driven procedurally every frame (no vizact.sizeTo):
#     * Anticipation before takeoff (squat -> stretch -> settle)
#     * Damped, multi-bounce squish on landing using a decayed sinusoid
#     This avoids 1-frame snapping and gives smooth, continuous animation.
# Controls: W A S D move, R restart, Esc quit, Tab toggle mouse lock, F toggle FP/TP

import viz
import vizact
import vizshape
import math
import os
import random

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
CAMERA_HEIGHT_TP    = 1.3
CAMERA_MIN_HEIGHT_TP= 0.25

PITCH_LIMIT         = 85.0
MOUSE_SENS_DEG      = 0.15

# Invert settings per mode (saved previously)
INVERT_Y_FP         = True   # FP: inverted (mouse up looks down)
INVERT_Y_TP         = True   # TP: inverted

# TP camera smoothing (keep instant by default)
CAMERA_SMOOTH_TP    = False
CAMERA_DAMPING_TP   = 14.0

mouse_locked        = True

# Facing behavior for TP
FACE_STRAFE_ONLY    = True
STRAFE_FACE_OFFSET  = 90.0  # degrees offset for left/right strafe facing

# -----------------------------
# Pac-Man NPC config (jump-only locomotion) — saved settings + small base lift
# -----------------------------
ASSET_PACMAN_GLTF       = os.path.join('assets','PacMan.glb')
PACMAN_MODEL_SCALE      = 0.30
PACMAN_TINT             = (1.0, 1.0, 0.0)
PACMAN_Y_OFFSET         = 1.4
PACMAN_BASE_LIFT        = 0.20     # slight lift so he sits a bit higher
PACMAN_TURN_INTERVAL    = (1.5, 3.0)
PACMAN_JUMP_INTERVAL    = (1.2, 2.2)
PACMAN_HOP_SPEED        = 4.0      # horizontal speed while airborne
PACMAN_JUMP_VEL         = 3.2
PACMAN_GRAVITY          = 9.5
PACMAN_WANDER_MARGIN    = 0.5

# "Saved" squish amounts used as targets; we convert them to spring parameters
PACMAN_SQUISH_IN_TIME   = 1.0
PACMAN_SQUISH_HOLD_TIME = 0.10
PACMAN_SQUISH_OUT_TIME  = 0.300
PACMAN_SQUISH_SCALE     = [1.25, 0.5, 1.25]  # target peak squash factors

# Anticipation before jump (procedural)
PACMAN_ANT_SQUASH_TIME   = 0.14
PACMAN_ANT_STRETCH_TIME  = 0.12
PACMAN_ANT_SETTLE_TIME   = 0.10
PACMAN_ANT_SQUASH_SCALE  = [1.10, 0.86, 1.10]
PACMAN_ANT_STRETCH_SCALE = [0.95, 1.10, 0.95]

# Landing squish procedural spring params (damped sinusoid)
LAND_TOTAL_MIN     = 0.90  # seconds minimum total visible landing animation
LAND_DECAY         = 2.8   # larger = faster damping
LAND_FREQ_HZ       = 3.0   # bounces per second
TWOPI              = 2.0 * math.pi

# -----------------------------
# Helpers
# -----------------------------
def clamp(v,a,b): return max(a,min(v,b))
def lerp(a,b,t): return a + (b-a)*t

def ease_in(t): return t*t
def ease_out(t): 
    u = 1.0 - t
    return 1.0 - u*u
def ease_in_out(t):
    # smoothstep-like
    return t*t*(3.0 - 2.0*t)

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
    """Center raw model inside wrapper so wrapper origin is near visual center (XZ) and bottom aligned."""
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
        raw.setPosition([-cx, desiredBottom - minY, -cz])
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
                wrapper.color(*tint)
            print('[Model] Loaded:', asset_path)
            return wrapper
        except Exception as e:
            print('[Model] Load error for', asset_path, ':', e)
    else:
        print('[Model] Not found, using primitive ->', asset_path)
    g = viz.addGroup()
    head = vizshape.addSphere(radius=PLAYER_RADIUS,slices=24,stacks=18)
    base_color = tint if tint is not None else fallback_color
    head.color(*base_color); head.setParent(g)
    body = vizshape.addCylinder(height=0.5,radius=0.15,axis=vizshape.AXIS_Y)
    body.color(0.2,0.6,1.0); body.setParent(g); body.setPosition([0,-0.3,0])
    g.setScale([scale]*3)
    if tint is not None:
        g.color(*tint)
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
# Player
# -----------------------------
player = load_model(ASSET_PLAYER_GLTF, PLAYER_MODEL_SCALE)
player.setPosition([0,PLAYER_Y_OFFSET,0])
player_yaw = 0.0
player.visible(False if FIRST_PERSON else True)

# -----------------------------
# Pac-Man NPC (jump-only locomotion) with procedural squash/stretch
# -----------------------------
pacman = load_model(ASSET_PACMAN_GLTF, PACMAN_MODEL_SCALE, tint=PACMAN_TINT, fallback_color=(1.0,1.0,0.0))
pacman.setPosition([2.0, PACMAN_Y_OFFSET + PACMAN_BASE_LIFT, 0.0])
pacman.setScale([PACMAN_MODEL_SCALE]*3)

# Motion state
pacman_yaw = random.uniform(0,360)
pacman_vx = 0.0
pacman_vz = 0.0
pacman_airborne = False
pacman_vy = 0.0
pacman_height = 0.0
pacman_next_turn = viz.getFrameTime() + random.uniform(*PACMAN_TURN_INTERVAL)
pacman_next_jump = viz.getFrameTime() + random.uniform(*PACMAN_JUMP_INTERVAL)
pacman_pending_jump = False
pacman_jump_start_time = 0.0

# Procedural scale state
PAC_BASE = PACMAN_MODEL_SCALE
pac_scale_cur = [PAC_BASE, PAC_BASE, PAC_BASE]

# Animation FSM
pac_anim_mode = 'idle'   # 'idle' | 'anticipation' | 'land'
pac_anim_t    = 0.0
# Precompute deltas from saved squish scale to drive spring amplitude
SQUISH_XZ_AMP = PACMAN_SQUISH_SCALE[0] - 1.0   # 0.25 -> +25% stretch
SQUISH_Y_AMP  = 1.0 - PACMAN_SQUISH_SCALE[1]   # 0.50 -> 50% squash

def pac_set_scale(sx, sy, sz):
    pacman.setScale([sx, sy, sz])

def pac_reset_scale():
    global pac_scale_cur
    pac_scale_cur = [PAC_BASE, PAC_BASE, PAC_BASE]
    pac_set_scale(*pac_scale_cur)

def pac_start_anticipation():
    global pac_anim_mode, pac_anim_t
    pac_anim_mode = 'anticipation'
    pac_anim_t = 0.0

def pac_start_land():
    global pac_anim_mode, pac_anim_t
    pac_anim_mode = 'land'
    pac_anim_t = 0.0

def pac_update_anim(dt):
    global pac_anim_mode, pac_anim_t, pac_scale_cur
    pac_anim_t += dt

    if pac_anim_mode == 'anticipation':
        # Timeline: [0..t1]=base->squat, [t1..t1+t2]=squat->stretch, [..t1+t2+t3]=stretch->base
        t1 = PACMAN_ANT_SQUASH_TIME
        t2 = PACMAN_ANT_STRETCH_TIME
        t3 = PACMAN_ANT_SETTLE_TIME
        total = t1 + t2 + t3
        bx, by, bz = PAC_BASE, PAC_BASE, PAC_BASE
        sqx, sqy, sqz = [PAC_BASE * s for s in PACMAN_ANT_SQUASH_SCALE]
        stx, sty, stz = [PAC_BASE * s for s in PACMAN_ANT_STRETCH_SCALE]

        t = pac_anim_t
        if t <= t1:
            u = ease_out(t/t1) if t1 > 0 else 1.0
            sx = lerp(bx, sqx, u); sy = lerp(by, sqy, u); sz = lerp(bz, sqz, u)
        elif t <= t1 + t2:
            u = ease_in_out((t - t1)/t2) if t2 > 0 else 1.0
            sx = lerp(sqx, stx, u); sy = lerp(sqy, sty, u); sz = lerp(sqz, stz, u)
        elif t <= total:
            u = ease_in((t - t1 - t2)/t3) if t3 > 0 else 1.0
            sx = lerp(stx, bx, u); sy = lerp(sty, by, u); sz = lerp(stz, bz, u)
        else:
            sx, sy, sz = bx, by, bz
            pac_anim_mode = 'idle'
            pac_anim_t = 0.0

        pac_scale_cur = [sx, sy, sz]
        pac_set_scale(*pac_scale_cur)

    elif pac_anim_mode == 'land':
        # Damped sinusoid around base; phase so t=0 hits peak squash instantly (no snap)
        # Amplitudes derive from saved squish targets
        dur_hint = max(LAND_TOTAL_MIN, PACMAN_SQUISH_IN_TIME + PACMAN_SQUISH_HOLD_TIME + PACMAN_SQUISH_OUT_TIME)
        t = pac_anim_t
        k = LAND_DECAY
        w = TWOPI * LAND_FREQ_HZ
        phase = math.pi/2.0  # start at peak

        # Decayed sine
        decay = math.exp(-k * t)
        osc = math.sin(w * t + phase) * decay

        ax = SQUISH_XZ_AMP  # positive stretch on X/Z
        ay = SQUISH_Y_AMP   # positive means squash amount on Y

        sx = PAC_BASE * (1.0 + ax * osc)
        sy = PAC_BASE * (1.0 - ay * osc)
        sz = PAC_BASE * (1.0 + ax * osc)

        pac_scale_cur = [sx, sy, sz]
        pac_set_scale(*pac_scale_cur)

        if t >= dur_hint or decay < 0.02:
            pac_reset_scale()
            pac_anim_mode = 'idle'
            pac_anim_t = 0.0

    else:
        # idle: ensure base
        # no-op, but keep last computed scale
        pass

def pick_new_jump_heading():
    global pacman_yaw, pacman_vx, pacman_vz
    pacman_yaw = random.uniform(0,360)
    yaw_rad = math.radians(pacman_yaw)
    fwd_x = math.sin(yaw_rad)
    fwd_z = math.cos(yaw_rad)
    pacman_vx = fwd_x * PACMAN_HOP_SPEED
    pacman_vz = fwd_z * PACMAN_HOP_SPEED
    pacman.setEuler([pacman_yaw,0,0])

def reflect_if_hitting_edges(x, z):
    global pacman_vx, pacman_vz, pacman_yaw
    half = ARENA_SIZE*0.5 - PACMAN_WANDER_MARGIN
    hit = False
    if x < -half:
        x = -half; pacman_vx = abs(pacman_vx); hit = True
    elif x > half:
        x = half; pacman_vx = -abs(pacman_vx); hit = True
    if z < -half:
        z = -half; pacman_vz = abs(pacman_vz); hit = True
    elif z > half:
        z = half; pacman_vz = -abs(pacman_vz); hit = True
    if hit:
        if abs(pacman_vx) + abs(pacman_vz) > 1e-6:
            pacman_yaw = math.degrees(math.atan2(pacman_vx, pacman_vz))
            pacman.setEuler([pacman_yaw,0,0])
    return x, z

def update_pacman(dt):
    global pacman_airborne, pacman_height, pacman_vy, pacman_next_jump
    global pacman_pending_jump, pacman_jump_start_time

    tnow = viz.getFrameTime()

    # Schedule a jump with anticipation while grounded
    if not pacman_airborne:
        if (not pacman_pending_jump) and (tnow >= pacman_next_jump):
            pick_new_jump_heading()
            pac_start_anticipation()
            pacman_pending_jump = True
            pacman_jump_start_time = tnow + (PACMAN_ANT_SQUASH_TIME + PACMAN_ANT_STRETCH_TIME + PACMAN_ANT_SETTLE_TIME)

        if pacman_pending_jump and tnow >= pacman_jump_start_time:
            pacman_airborne = True
            pacman_vy = PACMAN_JUMP_VEL
            pacman_height = 0.0
            pacman_pending_jump = False
            pacman_next_jump = tnow + random.uniform(*PACMAN_JUMP_INTERVAL)

    x,y,z = pacman.getPosition()

    if pacman_airborne:
        # Horizontal movement only while airborne
        x += pacman_vx * dt
        z += pacman_vz * dt
        x, z = reflect_if_hitting_edges(x, z)

        # Vertical motion
        pacman_height += pacman_vy * dt
        pacman_vy -= PACMAN_GRAVITY * dt

        # Land check
        if pacman_height <= 0.0:
            pacman_height = 0.0
            pacman_vy = 0.0
            if pacman_airborne:
                pacman_airborne = False
                pac_start_land()
    # Apply position (base + jump height)
    pacman.setPosition([x, PACMAN_Y_OFFSET + PACMAN_BASE_LIFT + pacman_height, z])

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
    global pacman_yaw, pacman_height, pacman_vy, pacman_airborne
    global pacman_next_turn, pacman_next_jump, pacman_vx, pacman_vz
    global pacman_pending_jump, pacman_jump_start_time, pac_anim_mode, pac_anim_t, pac_scale_cur

    # Player
    player.setPosition([0,PLAYER_Y_OFFSET,0])
    player_yaw = 0.0
    cam_yaw = 0.0
    cam_pitch = 5.0
    last_cam_pos = None

    # Pac-Man
    pacman.setPosition([2.0, PACMAN_Y_OFFSET + PACMAN_BASE_LIFT, 0.0])
    pacman_yaw = random.uniform(0,360)
    pacman.setEuler([pacman_yaw,0,0])
    pacman_height = 0.0
    pacman_vy = 0.0
    pacman_airborne = False
    pacman_vx = 0.0
    pacman_vz = 0.0
    pacman_pending_jump = False
    pacman_jump_start_time = 0.0
    pac_anim_mode = 'idle'
    pac_anim_t = 0.0
    pac_reset_scale()
    now = viz.getFrameTime()
    pacman_next_turn = now + random.uniform(*PACMAN_TURN_INTERVAL)
    pacman_next_jump = now + random.uniform(*PACMAN_JUMP_INTERVAL)

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

if hasattr(viz,'MOUSE_MOVE_EVENT'):
    viz.callback(viz.MOUSE_MOVE_EVENT, _on_mouse_move)
else:
    print('[Mouse] viz.MOUSE_MOVE_EVENT not available; mouselook needs that event.')

# -----------------------------
# Camera update (TP uses same yaw/pitch "view" as FP, just offset back)
# -----------------------------
def update_camera(dt):
    global last_cam_pos
    yaw_rad   = math.radians(cam_yaw)
    pitch_rad = math.radians(cam_pitch)

    # View direction from yaw/pitch (same for FP & TP)
    dir_x = math.sin(yaw_rad) * math.cos(pitch_rad)
    dir_y = math.sin(pitch_rad)
    dir_z = math.cos(yaw_rad) * math.cos(pitch_rad)

    # Horizontal forward for movement/facing
    hfx = math.sin(yaw_rad)
    hfz = math.cos(yaw_rad)

    px,py,pz = player.getPosition()

    if FIRST_PERSON:
        target = [px, py + CAMERA_HEIGHT_FP, pz]
        desired = target[:]
        look_at = [target[0] + dir_x*3.0, target[1] + dir_y*3.0, target[2] + dir_z*3.0]
    else:
        target = [px, py + CAMERA_HEIGHT_TP, pz]
        cam_x = target[0] - dir_x * CAMERA_DISTANCE_TP
        cam_y = target[1] - dir_y * CAMERA_DISTANCE_TP
        cam_z = target[2] - dir_z * CAMERA_DISTANCE_TP
        cam_y = max(cam_y, CAMERA_MIN_HEIGHT_TP)
        desired = [cam_x, cam_y, cam_z]
        look_at = [target[0] + dir_x*0.01, target[1] + dir_y*0.01, target[2] + dir_z*0.01]

    if last_cam_pos is None:
        last_cam_pos = desired[:]

    cam_pos = desired
    if (not FIRST_PERSON) and CAMERA_SMOOTH_TP:
        t = 1.0 - math.exp(-CAMERA_DAMPING_TP * dt)
        last_cam_pos = [lerp(last_cam_pos[i], desired[i], t) for i in range(3)]
        cam_pos = last_cam_pos

    viz.MainView.setPosition(cam_pos)
    viz.MainView.lookat(look_at)
    return hfx,hfz

# -----------------------------
# Frame update
# -----------------------------
def on_update():
    dt = viz.getFrameElapsed()
    hfx,hfz = update_camera(dt)

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

    within_arena(player, PLAYER_RADIUS)

    # Update Pac-Man
    update_pacman(dt)
    pac_update_anim(dt)

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
print('  FP/TP toggle: F (InvertY FP:', INVERT_Y_FP, ', InvertY TP:', INVERT_Y_TP, ')')
print('Assets:', ASSET_PLAYER_GLTF, '| Pac-Man:', ASSET_PACMAN_GLTF)
print('Sensitivity (deg/pixel):', MOUSE_SENS_DEG)
print('TP orbit distance:', CAMERA_DISTANCE_TP, 'TP min height:', CAMERA_MIN_HEIGHT_TP)
print('Pac-Man model scale:', PACMAN_MODEL_SCALE, ' | Base lift:', PACMAN_BASE_LIFT)