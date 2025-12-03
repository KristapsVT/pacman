import os
try:
    import viz
    import vizact
    import vizshape
except Exception:
    viz = None
    vizact = None
    vizshape = None

PACMAN_SIZE = 0.11
PACMAN_RADIUS = 0.5
PACMAN_Y_OFFSET = 0.35
PACMAN_JUMP_FORWARD = 3

PACMAN_JUMP_FORWARD_DIR = (0.0, 0.0, 1.0)

DEFAULT_SQUASH_FREQ_HZ = 0.55 
DEFAULT_JUMP_VEL = 2.6        
DEFAULT_GRAVITY = 8.8         

def run_pacman_animation(asset_relative='assets/PacMan.glb', base_scale=PACMAN_SIZE, freq_hz=DEFAULT_SQUASH_FREQ_HZ, width_amp=0.22, height_amp=0.22, jump_vel=DEFAULT_JUMP_VEL, gravity=DEFAULT_GRAVITY, jump_forward=PACMAN_JUMP_FORWARD, forward_dir=PACMAN_JUMP_FORWARD_DIR, position=(0,0,0), parent=None):
    if viz is None:
        print('[PacMan] Vizard not available in this environment. Cannot run animation.')
        return None
    try:
        viz.go()
    except Exception:
        pass 
    asset_path = asset_relative if os.path.isabs(asset_relative) else os.path.normpath(os.path.join(os.path.dirname(__file__), asset_relative))
    if not os.path.exists(asset_path):
        print('[PacMan] Asset not found:', asset_path)
        root = viz.addGroup()
        body = vizshape.addSphere(radius=0.5)
        body.setParent(root)
        base_scale = 1.0
    else:
        root = viz.addGroup()
        raw = viz.addChild(asset_path)
        raw.setParent(root)
        try:
            raw.setPosition([0,0,0])
        except Exception:
            pass
        try:
            raw.disable(viz.LIGHTING)
        except Exception:
            pass
        try:
            root.disable(viz.LIGHTING)
        except Exception:
            pass
        try:
            root.color(1.0, 0.9, 0.05)
        except Exception:
            pass

    if parent is not None:
        try:
            root.setParent(parent)
        except Exception:
            pass

    px, py, pz = position
    try:
        root.setPosition([px, py, pz])
    except Exception:
        pass
    root.setScale([base_scale, base_scale, base_scale])
    state = {
        'mode': 'squash',
        'time': 0.0,
        'vy': 0.0,
        'y': py,
        'start_time': viz.getFrameTime(),
        'base_x': px,
        'base_y': py,
        'base_z': pz
    }

    try:
        root._anim_params = {
            'jump_forward': jump_forward,
            'forward_dir': forward_dir,
            'jump_vel': jump_vel,
            'gravity': gravity
        }
    except Exception:
        pass

    def _set_jump_params(new_forward_dir=None, new_jump_forward=None, new_jump_vel=None, new_gravity=None):
        params = getattr(root, '_anim_params', None)
        if params is None:
            return
        if new_forward_dir is not None:
            params['forward_dir'] = new_forward_dir
        if new_jump_forward is not None:
            params['jump_forward'] = new_jump_forward
        if new_jump_vel is not None:
            params['jump_vel'] = new_jump_vel
        if new_gravity is not None:
            params['gravity'] = new_gravity
    try:
        root.set_jump_params = _set_jump_params
    except Exception:
        pass
    try:
        root._pm_state = state
    except Exception:
        pass

    import math

    def _update():
        tnow = viz.getFrameTime()
        dt = tnow - state.get('last_t', tnow)
        state['last_t'] = tnow

        if state['mode'] == 'squash':
            elapsed = tnow - state.get('start_time', tnow)
            theta = 2.0 * math.pi * freq_hz * elapsed
            val = (math.sin(theta) + 1.0) * 0.5

            sx = base_scale * (1.0 + width_amp * val)
            sy = base_scale * (1.0 - height_amp * val)
            sz = base_scale * (1.0 + width_amp * val)
            try:
                root.setScale([sx, sy, sz])
            except Exception:
                pass
            prev_phase = state.get('prev_phase', None)
            phase = math.sin(theta)
            if prev_phase is None:
                state['prev_phase'] = phase
            else:
                if state.get('passed_peak', False) is False and phase > 0.9:
                    state['passed_peak'] = True
                if state.get('passed_peak', False) and abs(phase) < 0.05:
                    state['mode'] = 'jump'
                    params = getattr(root, '_anim_params', None)
                    jf = jump_forward
                    jv = jump_vel
                    gr = gravity
                    fd = forward_dir
                    if isinstance(params, dict):
                        jf = params.get('jump_forward', jf)
                        jv = params.get('jump_vel', jv)
                        gr = params.get('gravity', gr)
                        fd = params.get('forward_dir', fd)
                    state['vy'] = jv
                    time_to_land = (2.0 * jv / gr) if gr != 0 else 0.0
                    if time_to_land > 1e-6 and jf:
                        state['forward_speed'] = float(jf) / float(time_to_land)
                    else:
                        state['forward_speed'] = 0.0
                    try:
                        fx, fy, fz = fd
                        mag = math.hypot(math.hypot(fx, fy), fz)
                        if mag > 1e-6:
                            state['forward_dir'] = (fx/mag, fy/mag, fz/mag)
                        else:
                            state['forward_dir'] = (0.0, 0.0, 1.0)
                    except Exception:
                        state['forward_dir'] = (0.0, 0.0, 1.0)
                    state['passed_peak'] = False
                    try:
                        root.setScale([base_scale, base_scale, base_scale])
                    except Exception:
                        pass
        elif state['mode'] == 'jump':
            vy = state.get('vy', 0.0)
            vy -= gravity * dt
            state['vy'] = vy
            state['y'] += vy * dt
            try:
                curx, cury, curz = root.getPosition()
            except Exception:
                curx, cury, curz = state.get('base_x', px), state.get('y', py), state.get('base_z', pz)
            fdx, fdy, fdz = state.get('forward_dir', (0.0, 0.0, 1.0))
            fs = state.get('forward_speed', 0.0)
            curx += fdx * fs * dt
            curz += fdz * fs * dt
            try:
                root.setPosition([curx, state['y'], curz])
            except Exception:
                pass
            try:
                root.setScale([base_scale, base_scale, base_scale])
            except Exception:
                pass
            base_y = state.get('base_y', py)
            if state['y'] <= base_y:

                try:
                    landed_x, _, landed_z = root.getPosition()
                except Exception:
                    landed_x, landed_z = state.get('base_x', px), state.get('base_z', pz)
                state['y'] = base_y
                state['vy'] = 0.0
                try:
                    root.setPosition([landed_x, base_y, landed_z])
                except Exception:
                    pass
                state['base_x'] = landed_x
                state['base_z'] = landed_z
                state['start_time'] = viz.getFrameTime()
                state['mode'] = 'squash'
                state['last_t'] = viz.getFrameTime()

    try:
        vizact.ontimer(0, _update)
    except Exception:
        try:
            viz.callback(viz.UPDATE_EVENT, _update)
        except Exception:
            print('[PacMan] Warning: unable to schedule animation timer')

    print('[PacMan] Running animation for', asset_path)
    return root


if __name__ == '__main__':
    node = run_pacman_animation()
    if node is None:
        print('[PacMan] Finished (no Vizard).')
    else:
        print('[PacMan] Press ESC in the Vizard window to quit.')
