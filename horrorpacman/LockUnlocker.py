import time
import math
import os
import viz
import vizact

try:
    import KeyCollector as _KC
except Exception:
    _KC = None

try:
    import KeyLoader as _KL
except Exception:
    _KL = None

_player = None
_map_root = None
_pick_distance = None
_locks_cache = []
_on_unlock_callback = None
_unlock_sound = None


def _load_unlock_sound():
    global _unlock_sound
    if _unlock_sound is not None:
        return _unlock_sound
    try:
        base = os.path.dirname(__file__)
        path = os.path.join(base, 'assets', 'lock-unlocking.mp3')
        if not os.path.exists(path):
            for alt in ('lock-unlock.mp3', 'lock_unlock.mp3', 'unlock.mp3'):
                p2 = os.path.join(base, 'assets', alt)
                if os.path.exists(p2):
                    path = p2
                    break
        try:
            _unlock_sound = viz.addAudio(path)
        except Exception:
            try:
                viz.playSound(path)
                _unlock_sound = None
            except Exception:
                _unlock_sound = None
        return _unlock_sound
    except Exception:
        _unlock_sound = None
        return None


def _iter_children(root):
    stack = [root]
    while stack:
        n = stack.pop()
        yield n
        try:
            children = n.getChildren()
        except Exception:
            children = []
        if children:
            for c in children:
                stack.append(c)


def _get_node_color(node):
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

        for attr in ('name', '_name', 'type', 'key_color', 'color_name'):
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


def _scan_locks():
    global _locks_cache, _map_root
    _locks_cache = []
    if _map_root is None:
        return
    try:
        for n in _iter_children(_map_root):
            try:
                if getattr(n, '_is_lock', False):
                    color = _get_node_color(n)
                    _locks_cache.append((n, color))
            except Exception:
                continue
    except Exception:
        pass


def _find_nearby_lock():
    global _player, _pick_distance
    if _player is None:
        return None, None
    try:
        px, py, pz = _player.getPosition()
    except Exception:
        return None, None
    if _pick_distance is None:
        try:
            _pick_distance = float(getattr(_KL, 'DEFAULT_CELL_SIZE', 3.0)) * 0.6
        except Exception:
            _pick_distance = 1.8

    best = None
    best_dist = float('inf')
    for node, color in list(_locks_cache):
        if not node:
            continue
        try:
            lx, ly, lz = node.getPosition()
        except Exception:
            continue
        dx = lx - px
        dz = lz - pz
        d = math.hypot(dx, dz)
        if d <= _pick_distance and d < best_dist:
            best_dist = d
            best = (node, color)
    if best:
        return best
    return None, None


def _try_remove_node(node):
    try:
        node.remove()
        return True, 'node.remove()'
    except Exception:
        pass
    try:
        viz.remove(node)
        return True, 'viz.remove()'
    except Exception:
        pass
    try:
        node.visible(False)
        node.setParent(None)
        return True, 'hide()'
    except Exception:
        pass
    return False, None


def _attempt_unlock():
    global _locks_cache, _KC, _on_unlock_callback
    _scan_locks()
    node, color = _find_nearby_lock()
    if node is None:
        try:
            print('[LockUnlocker] No nearby lock to unlock')
        except Exception:
            pass
        return False

    req = (color or 'unknown').lower()
    if _KC is None:
        try:
            print('[LockUnlocker] KeyCollector not available; cannot check keys')
        except Exception:
            pass
        return False

    try:
        owned = _KC.get_collected_sequence()
    except Exception:
        owned = []

    owned_lower = [str(x).lower() for x in (owned or [])]
    if req not in owned_lower:
        try:
            print('[LockUnlocker] Player lacks key for lock (need=%s owned=%s)' % (req, owned_lower))
        except Exception:
            pass
        return False

    ok, method = _try_remove_node(node)
    if ok:
        try:
            print('[LockUnlocker] Unlocked %s lock using %s' % (req, method))
        except Exception:
            pass
        try:
            snd = _load_unlock_sound()
            if snd is not None:
                snd.play()
        except Exception:
            pass
        try:
            _scan_locks()
        except Exception:
            pass
        try:
            if _on_unlock_callback is not None:
                _on_unlock_callback(req, node)
        except Exception:
            pass
        return True

    try:
        print('[LockUnlocker] Failed to remove lock node')
    except Exception:
        pass
    return False


def init(player, map_root=None, pick_distance=None, on_unlock=None):
    global _player, _map_root, _pick_distance, _on_unlock_callback
    _player = player
    _map_root = map_root
    _on_unlock_callback = on_unlock
    try:
        if pick_distance is not None:
            _pick_distance = float(pick_distance)
        else:
            _pick_distance = float(getattr(_KL, 'DEFAULT_CELL_SIZE', 3.0)) * 0.6
    except Exception:
        _pick_distance = 1.8

    try:
        _scan_locks()
    except Exception:
        pass

    try:
        vizact.onkeydown('e', lambda: _attempt_unlock())
    except Exception:
        try:
            vizact.onkeydown('E', lambda: _attempt_unlock())
        except Exception:
            pass

    try:
        vizact.ontimer(1.0, _scan_locks)
    except Exception:
        pass

    try:
        print('[LockUnlocker] initialized; pick_distance=', _pick_distance)
    except Exception:
        pass


if __name__ == '__main__':
    print('LockUnlocker module - call init(player, map_root) to enable unlocking')
