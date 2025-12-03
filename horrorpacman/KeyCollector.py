import math
import time
import os
import viz
import vizact

try:
    import KeyLoader as _KL
    get_last_spawned_keys = getattr(_KL, 'get_last_spawned_keys', None)
    _DEFAULT_CELL = getattr(_KL, 'DEFAULT_CELL_SIZE', 3.0)
except Exception:
    _KL = None
    get_last_spawned_keys = None
    _DEFAULT_CELL = 3.0


_player = None
_pick_distance = None
_angle_threshold = None 
_hud = None
_collected_count = 0
_highlighted = None
_flash_until = 0.0
_player_flash_until = 0.0
_player_orig_color = None
_on_collect_callback = None
_collected_sequence = []
_pickup_sound = None 


def _load_pickup_sound():
    global _pickup_sound
    if _pickup_sound is not None:
        return _pickup_sound
    try:
        base = os.path.dirname(__file__)
        path = os.path.join(base, 'assets', 'key-get.mp3')
        if not os.path.exists(path):
            for alt in ('key-get.wav', 'key_get.mp3', 'key.mp3'):
                p2 = os.path.join(base, 'assets', alt)
                if os.path.exists(p2):
                    path = p2
                    break
        try:
            _pickup_sound = viz.addAudio(path)
        except Exception:
            try:
                viz.playSound(path)
                _pickup_sound = None
            except Exception:
                _pickup_sound = None
        return _pickup_sound
    except Exception:
        _pickup_sound = None
        return None


def _angle_diff(a):
    a = (a + 180.0) % 360.0 - 180.0
    return a


def _update_hud(message=None):
    return


def _show_popup(message, duration=1.8):
    return


def _find_nearby_key():
    global _player, _pick_distance
    if _player is None or get_last_spawned_keys is None:
        return None, None

    try:
        px, py, pz = _player.getPosition()
    except Exception:
        return None, None

    if _pick_distance is None:
        try:
            _pick_distance = float(_DEFAULT_CELL) * 0.6
        except Exception:
            _pick_distance = 1.8

    best = None
    best_dist = float('inf')
    for k in get_last_spawned_keys() or []:
        if not k or isinstance(k, dict):
            continue
        try:
            kx, ky, kz = k.getPosition()
        except Exception:
            continue
        dx = kx - px
        dz = kz - pz
        dist = math.hypot(dx, dz)
        if dist <= _pick_distance and dist < best_dist:
            best_dist = dist
            best = k

    if best is not None:
        return best, best_dist
    return None, None


def _attempt_pick():
    try:
        key, _ = _find_nearby_key()
    except Exception:
        return False
    if key is None:
        return False
    try:
        color_name = _get_key_color(key)
    except Exception:
        color_name = 'unknown'

    ok, removed_by = _try_remove_node(key)
    global _collected_count, _flash_until, _collected_sequence
    if ok:
        _collected_count += 1
        try:
            _collected_sequence.append(color_name)
        except Exception:
            pass
        try:
            snd = _load_pickup_sound()
            if snd is not None:
                snd.play()
        except Exception:
            pass
        _flash_until = time.time() + 2.0
        _update_hud('Collected!')
        try:
            if _on_collect_callback is not None:
                try:
                    msg = '[KeyCollector] removed node using %s' % (removed_by if removed_by is not None else 'unknown')
                    _on_collect_callback((_collected_count, msg, list(_collected_sequence)))
                except Exception:
                    pass
        except Exception:
            pass
        return True
    return False


def _try_remove_node(node):
    try:
        node.remove()
        removed_by = 'node.remove()'
        ok = True
    except Exception:
        ok = False
        removed_by = None
    if not ok:
        try:
            viz.remove(node)
            removed_by = 'viz.remove()'
            ok = True
        except Exception:
            ok = False
    if not ok:
        try:
            node.visible(False)
            node.setParent(None)
            removed_by = 'hide()'
            ok = True
        except Exception:
            ok = False

    if ok:
        try:
            if _KL is not None and hasattr(_KL, '_last_spawned'):
                try:
                    lst = getattr(_KL, '_last_spawned')
                    while node in lst:
                        lst.remove(node)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            print('[KeyCollector] removed node using', removed_by)
        except Exception:
            pass
        return True, removed_by
    return False, None


def _get_key_color(node):
    try:
        col = None
        if hasattr(node, 'getColor'):
            try:
                col = node.getColor()
            except Exception:
                col = None
        if col is None and hasattr(node, 'color'):
            try:
                c = node.color
                col = c() if callable(c) else c
            except Exception:
                col = None

        if isinstance(col, (list, tuple)) and len(col) >= 3:
            try:
                r, g, b = float(col[0]), float(col[1]), float(col[2])
                if max(r, g, b) > 1.5:
                    r, g, b = r / 255.0, g / 255.0, b / 255.0

                named = {
                    'green': (70.0/255.0, 183.0/255.0, 73.0/255.0),
                    'yellow': (255.0/255.0, 221.0/255.0, 26.0/255.0),
                    'white': (221.0/255.0, 226.0/255.0, 228.0/255.0),
                }
                best_name = 'unknown'
                best_d = float('inf')
                for name, (nr, ng, nb) in named.items():
                    d = math.hypot(r - nr, g - ng, b - nb)
                    if d < best_d:
                        best_d = d
                        best_name = name
                return best_name
            except Exception:
                pass

        for attr in ('name', '_name', 'key_color', 'color_name', 'type'):
            try:
                v = getattr(node, attr, None)
            except Exception:
                v = None
            if isinstance(v, str):
                s = v.lower()
                for color in ('green', 'yellow', 'white'):
                    if color in s:
                        return color

    except Exception:
        pass
    return 'unknown'


def _update(dt=0):
    global _highlighted, _collected_count, _flash_until

    key, dist = _find_nearby_key()

    try:
        if _highlighted is not None and _highlighted is not key:
            try:
                orig = getattr(_highlighted, '_kc_orig_scale', None)
                if orig is not None:
                    _highlighted.setScale(orig)
            except Exception:
                pass
            _highlighted = None

        if key is not None and key is not _highlighted:
            try:
                orig = key.getScale()
                key._kc_orig_scale = list(orig) if orig else [1.0, 1.0, 1.0]
                s = [orig[0] * 1.25, orig[1] * 1.25, orig[2] * 1.25]
                key.setScale(s)
                _highlighted = key
            except Exception:
                _highlighted = None
    except Exception:
        pass

    if _flash_until and time.time() > _flash_until:
        _flash_until = 0.0
        _update_hud()

    try:
        global _player_flash_until, _player_orig_color
        if _player is not None and _player_flash_until and time.time() > _player_flash_until:
            try:
                if _player_orig_color is not None and (isinstance(_player_orig_color, (list, tuple))):
                    try:
                        _player.color(*_player_orig_color)
                    except Exception:
                        pass
                else:
                    try:
                        _player.color(1.0, 1.0, 1.0)
                    except Exception:
                        pass
            except Exception:
                pass
            _player_flash_until = 0.0
            _player_orig_color = None
    except Exception:
        pass


def init(player, pick_distance=4.0, angle_threshold=20.0, on_collect=None):
    global _player, _pick_distance, _angle_threshold
    _player = player
    _pick_distance = float(pick_distance)
    _angle_threshold = float(angle_threshold)
    global _on_collect_callback
    _on_collect_callback = on_collect
    _update_hud()
    try:
        vizact.ontimer(0, _update)
    except Exception:
        try:
            vizact.ontimer(1/30.0, _update)
        except Exception:
            pass
    try:
        vizact.onkeydown('e', lambda: _attempt_pick())
    except Exception:
        try:
            vizact.onkeydown('E', lambda: _attempt_pick())
        except Exception:
            pass
    print('[KeyCollector] initialized; pick_distance=', _pick_distance)


if __name__ == '__main__':
    print('KeyCollector module - import and call init(player) to enable collection')


def get_collected_sequence():
    try:
        return list(_collected_sequence)
    except Exception:
        return []


def reset_collected():
    global _collected_count, _collected_sequence
    try:
        _collected_count = 0
    except Exception:
        pass
    try:
        _collected_sequence = []
    except Exception:
        pass
