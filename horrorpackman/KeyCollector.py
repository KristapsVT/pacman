"""Key collection helper: allow the player to look at keys and click to pick them up.

Usage: call `KeyCollector.init(player)` from `Player.py` after the `player` node
is created (and after keys have been spawned). The module will create a small HUD
showing collected keys and will remove key nodes when collected.

This is intentionally self-contained and defensive: it tolerates missing Vizard
APIs and missing KeyLoader state.
"""
import math
import time
import viz
import vizact

# Prefer importing the KeyLoader module so we can read its DEFAULT_CELL_SIZE
try:
    import KeyLoader as _KL
    get_last_spawned_keys = getattr(_KL, 'get_last_spawned_keys', None)
    _DEFAULT_CELL = getattr(_KL, 'DEFAULT_CELL_SIZE', 3.0)
except Exception:
    _KL = None
    get_last_spawned_keys = None
    _DEFAULT_CELL = 3.0


# internal state
_player = None
_pick_distance = None
_angle_threshold = None  # not used with grid-based pickup
_hud = None
_collected_count = 0
_highlighted = None
_flash_until = 0.0
_player_flash_until = 0.0
_player_orig_color = None
_on_collect_callback = None
_collected_sequence = []


def _angle_diff(a):
    """Normalize angle difference to [-180,180]"""
    a = (a + 180.0) % 360.0 - 180.0
    return a


def _update_hud(message=None):
    # HUD/text disabled per user request — no on-screen text will be shown.
    return


def _show_popup(message, duration=1.8):
    # popup disabled — no on-screen popup will be shown.
    # Keep player flash as visual feedback (handled elsewhere).
    return


def _find_nearby_key():
    """Return the nearest key node that is on the same grid cell (proximity) as the player.

    This function uses a proximity threshold derived from KeyLoader.DEFAULT_CELL_SIZE
    to decide whether the player is "on the same grid" as a key.
    Returns (node, distance) or (None, None).
    """
    global _player, _pick_distance
    if _player is None or get_last_spawned_keys is None:
        return None, None

    try:
        px, py, pz = _player.getPosition()
    except Exception:
        return None, None

    # Determine proximity threshold: default to KeyLoader cell size * 0.6
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
    """Attempt to pick up a nearby key (keyboard- or code-triggerable)."""
    try:
        key, _ = _find_nearby_key()
    except Exception:
        return False
    if key is None:
        return False
    # determine key color (try before removal since removal may destroy node)
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
        _flash_until = time.time() + 2.0
        _update_hud('Collected!')
        try:
            _show_popup('Key Collected!')
        except Exception:
            pass
        # trigger external callback if provided (e.g., PacMan_exe popup)
        try:
            if _on_collect_callback is not None:
                try:
                    # send count, a textual message describing removal, and the collected sequence
                    msg = '[KeyCollector] removed node using %s' % (removed_by if removed_by is not None else 'unknown')
                    _on_collect_callback((_collected_count, msg, list(_collected_sequence)))
                except Exception:
                    pass
        except Exception:
            pass
        return True
    return False


def _try_remove_node(node):
    """Try a few safe removal methods for a viz node."""
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
            # attempt to hide if can't remove
            node.visible(False)
            node.setParent(None)
            removed_by = 'hide()'
            ok = True
        except Exception:
            ok = False

    # If we removed the node, also try to remove it from KeyLoader's cache
    if ok:
        try:
            if _KL is not None and hasattr(_KL, '_last_spawned'):
                try:
                    lst = getattr(_KL, '_last_spawned')
                    # remove all occurrences
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
    """Attempt to determine a key's color name (e.g. 'green','yellow','white').

    This is defensive: try common methods/properties and fall back to 'unknown'.
    """
    try:
        # Try common APIs that return color tuples
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

        # If we have an RGB(A) tuple/list, normalize and map to nearest named color
        if isinstance(col, (list, tuple)) and len(col) >= 3:
            try:
                r, g, b = float(col[0]), float(col[1]), float(col[2])
                # normalize if given in 0-255 range
                if max(r, g, b) > 1.5:
                    r, g, b = r / 255.0, g / 255.0, b / 255.0
                # simple nearest-color matching
                named = {
                    'green': (0.0, 1.0, 0.0),
                    'yellow': (1.0, 1.0, 0.0),
                    'white': (1.0, 1.0, 1.0),
                    'red': (1.0, 0.0, 0.0),
                    'blue': (0.0, 0.0, 1.0),
                    'cyan': (0.0, 1.0, 1.0),
                    'magenta': (1.0, 0.0, 1.0),
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

        # Look for textual hints in common attributes
        for attr in ('name', '_name', 'key_color', 'color_name', 'type'):
            try:
                v = getattr(node, attr, None)
            except Exception:
                v = None
            if isinstance(v, str):
                s = v.lower()
                for color in ('green', 'yellow', 'white', 'red', 'blue', 'cyan', 'magenta'):
                    if color in s:
                        return color

    except Exception:
        pass
    return 'unknown'


def _update(dt=0):
    """Run each frame: highlight key in view and handle click-to-pick."""
    global _highlighted, _collected_count, _flash_until

    # find key near player (same grid cell)
    key, dist = _find_nearby_key()

    # (no debug prints)

    # update highlighting
    try:
        if _highlighted is not None and _highlighted is not key:
            # restore scale
            try:
                orig = getattr(_highlighted, '_kc_orig_scale', None)
                if orig is not None:
                    _highlighted.setScale(orig)
            except Exception:
                pass
            _highlighted = None

        if key is not None and key is not _highlighted:
            try:
                # store original scale and enlarge slightly
                orig = key.getScale()
                key._kc_orig_scale = list(orig) if orig else [1.0, 1.0, 1.0]
                s = [orig[0] * 1.25, orig[1] * 1.25, orig[2] * 1.25]
                key.setScale(s)
                _highlighted = key
            except Exception:
                _highlighted = None
    except Exception:
        pass

    # (mouse click disabled — use keyboard 'E' to pick up)

    # handle HUD flashing timeout
    if _flash_until and time.time() > _flash_until:
        _flash_until = 0.0
        _update_hud()

    # popups disabled — no on-screen popup timeout handling
    # restore player color if we flashed it
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
                    # attempt to reset visibility/alpha by re-coloring to default
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
    """Initialize the collector with the `player` node.

    Call this from `Player.py` after `player` is created. Example:

        import KeyCollector
        KeyCollector.init(player)

    """
    global _player, _pick_distance, _angle_threshold
    _player = player
    _pick_distance = float(pick_distance)
    _angle_threshold = float(angle_threshold)
    global _on_collect_callback
    _on_collect_callback = on_collect
    _update_hud()
    try:
        # register update loop
        vizact.ontimer(0, _update)
    except Exception:
        # fallback: try a slower timer
        try:
            vizact.ontimer(1/30.0, _update)
        except Exception:
            pass
    # mouse callbacks removed — use keyboard ('E') to pick up keys
    # Register keyboard pickup ('e') as a reliable fallback
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
    """Return a copy of the collected key color sequence (ordered oldest->newest)."""
    try:
        return list(_collected_sequence)
    except Exception:
        return []


def reset_collected():
    """Clear collected count and sequence (useful for restarting a level)."""
    global _collected_count, _collected_sequence
    try:
        _collected_count = 0
    except Exception:
        pass
    try:
        _collected_sequence = []
    except Exception:
        pass
