"""
Ambience module: handles fog effects and ambient sound for atmospheric game experience.
Call init() after viz.go() to enable fog and sound.
"""
import viz
import vizact
import os

# Resolve asset paths relative to this module so running from repo root works
BASE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
def _asset_path(name):
    try:
        return os.path.normpath(os.path.join(ASSETS_DIR, name))
    except Exception:
        return name

# -----------------------------
# Fog Configuration
# -----------------------------
FOG_ENABLED         = True      # Enable/disable fog effect
FOG_START           = 6.0       # Distance where fog starts (units) - clear near player
FOG_END             = 25.0      # Distance where fog is fully opaque (units) - covers far map
FOG_DENSITY         = 0.15      # Fog density (0.0-1.0, only used for exponential fog)
FOG_COLOR           = [0.0, 0.0, 0.0]  # Fog color - must match viz.clearcolor exactly
FOG_MODE            = 'LINEAR'  # 'LINEAR' or 'EXPONENTIAL' - exponential may avoid floor issues

# -----------------------------
# Sound Configuration
# -----------------------------
SOUND_ENABLED       = True      # Enable/disable ambient sound
AMBIENT_SOUND_FILE  = _asset_path('horror-bg.mp3')  # Absolute path to ambient sound
AMBIENT_VOLUME      = 0.15      # Volume (0.0-1.0)
AMBIENT_LOOP        = True      # Loop the ambient sound
AMBIENT_PITCH       = 1.0       # Pitch multiplier (1.0 = normal)

# Additional sound files (optional)
FOOTSTEP_SOUND_FILE = _asset_path('footstep.wav')  # Footstep sound
DEATH_SOUND_FILE    = _asset_path('crunch.mp3')     # Death/caught sound
FOOTSTEP_VOLUME     = 0.2
DEATH_VOLUME        = 0.5

# -----------------------------
# Internal state
# -----------------------------
_ambient_sound = None
_footstep_sound = None
_death_sound = None
_fog_active = False
_sound_active = False


def init():
    """
    Initialize fog and sound effects.
    Call this after viz.go() has been called.
    """
    global _fog_active, _sound_active
    
    # Setup fog
    if FOG_ENABLED:
        _fog_active = setup_fog()
    else:
        print('[Ambience] Fog disabled')
    
    # Setup sound
    if SOUND_ENABLED:
        _sound_active = setup_sound()
    else:
        print('[Ambience] Sound disabled')


def setup_fog():
    """
    Configure and enable fog effects using viz.MainScene.
    Returns True if successful, False otherwise.
    """
    try:
        # Set fog color using viz.MainScene.fogColor
        viz.MainScene.fogColor(FOG_COLOR)
        print(f'[Ambience] Setting fog color: {FOG_COLOR}')
        
        # Enable fog with proper Vizard API
        if FOG_MODE == 'LINEAR':
            # Linear fog: viz.MainScene.fog(start, end)
            viz.MainScene.fog(FOG_START, FOG_END)
            print(f'[Ambience] Fog enabled: LINEAR mode, start={FOG_START}m, end={FOG_END}m')
        else:
            # Exponential fog: viz.MainScene.fog(density)
            viz.MainScene.fog(FOG_DENSITY)
            print(f'[Ambience] Fog enabled: EXPONENTIAL mode, density={FOG_DENSITY}')
        
        return True
    except Exception as e:
        print(f'[Ambience] Failed to setup fog: {e}')
        import traceback
        traceback.print_exc()
        return False


def setup_sound():
    """
    Load and start ambient sound effects.
    Returns True if successful, False otherwise.
    """
    global _ambient_sound, _footstep_sound, _death_sound
    
    try:
        # Load ambient background sound (absolute path)
        try:
            exists = os.path.exists(AMBIENT_SOUND_FILE)
            if not exists:
                print(f"[Ambience] Ambient path not found: {AMBIENT_SOUND_FILE} (cwd={os.getcwd()})")
            _ambient_sound = viz.addAudio(AMBIENT_SOUND_FILE)
            _ambient_sound.volume(AMBIENT_VOLUME)
            _ambient_sound.pitch(AMBIENT_PITCH)
            if AMBIENT_LOOP:
                _ambient_sound.loop(viz.ON)
            _ambient_sound.play()
            print(f'[Ambience] Ambient sound loaded and playing: {AMBIENT_SOUND_FILE}')
        except Exception as e:
            print(f'[Ambience] Could not load ambient sound via addAudio ({AMBIENT_SOUND_FILE}): {e}')
            # Fallback: try alternative filenames and viz.playSound
            alt_candidates = [
                _asset_path('horror-bg.wav'),
                _asset_path('ambient.wav'),
                _asset_path('ambient.mp3'),
            ]
            started = False
            for cand in alt_candidates:
                try:
                    if os.path.exists(cand):
                        _snd = viz.addAudio(cand)
                        _snd.volume(AMBIENT_VOLUME)
                        if AMBIENT_LOOP:
                            _snd.loop(viz.ON)
                        _snd.play()
                        _ambient_sound = _snd
                        print(f'[Ambience] Ambient fallback loaded: {cand}')
                        started = True
                        break
                except Exception:
                    continue
            if not started:
                try:
                    # Last resort: immediate play using viz.playSound
                    viz.playSound(AMBIENT_SOUND_FILE, viz.LOOP)
                    print(f'[Ambience] Ambient started with viz.playSound loop: {AMBIENT_SOUND_FILE}')
                    started = True
                except Exception as e2:
                    print(f'[Ambience] viz.playSound failed: {e2}')
            if not started:
                print('[Ambience] No ambient audio could be started. Check assets folder.')
        
        # Load footstep sound (for playing on movement)
        try:
            _footstep_sound = viz.addAudio(FOOTSTEP_SOUND_FILE)
            _footstep_sound.volume(FOOTSTEP_VOLUME)
            print(f'[Ambience] Footstep sound loaded: {FOOTSTEP_SOUND_FILE}')
        except Exception as e:
            print(f'[Ambience] Could not load footstep sound ({FOOTSTEP_SOUND_FILE}): {e}')
        
        # Load death sound (for game over)
        try:
            _death_sound = viz.addAudio(DEATH_SOUND_FILE)
            _death_sound.volume(DEATH_VOLUME)
            print(f'[Ambience] Death sound loaded: {DEATH_SOUND_FILE}')
        except Exception as e:
            print(f'[Ambience] Could not load death sound ({DEATH_SOUND_FILE}): {e}')
        
        return True
    except Exception as e:
        print(f'[Ambience] Failed to setup sound: {e}')
        import traceback
        traceback.print_exc()
        return False


def disable_fog():
    """Disable fog effects."""
    global _fog_active
    try:
        viz.MainScene.fog(1000.0, 2000.0)  # Push fog far away
        _fog_active = False
        print('[Ambience] Fog disabled')
    except Exception as e:
        print(f'[Ambience] Failed to disable fog: {e}')


def enable_fog():
    """Re-enable fog with current settings."""
    global _fog_active
    if setup_fog():
        _fog_active = True


def set_fog_distance(start, end):
    """
    Update fog start and end distances (for linear fog).
    
    Args:
        start: Distance where fog begins
        end: Distance where fog is fully opaque
    """
    global FOG_START, FOG_END
    FOG_START = start
    FOG_END = end
    
    if _fog_active and FOG_MODE == 'LINEAR':
        try:
            viz.MainScene.fog(FOG_START, FOG_END)
            print(f'[Ambience] Fog distance updated: start={FOG_START}m, end={FOG_END}m')
        except Exception as e:
            print(f'[Ambience] Failed to update fog distance: {e}')


def set_fog_density(density):
    """
    Update fog density (for exponential fog).
    
    Args:
        density: Fog density value (0.0-1.0)
    """
    global FOG_DENSITY
    FOG_DENSITY = density
    
    if _fog_active and FOG_MODE != 'LINEAR':
        try:
            viz.MainScene.fog(FOG_DENSITY)
            print(f'[Ambience] Fog density updated: {FOG_DENSITY}')
        except Exception as e:
            print(f'[Ambience] Failed to update fog density: {e}')


def play_footstep():
    """Play footstep sound effect."""
    if _sound_active and _footstep_sound is not None:
        try:
            _footstep_sound.play()
        except Exception:
            pass


def play_death_sound():
    """Play death/caught sound effect."""
    if _sound_active and _death_sound is not None:
        try:
            _death_sound.play()
        except Exception:
            pass


def stop_ambient_sound():
    """Stop the ambient background sound."""
    if _ambient_sound is not None:
        try:
            _ambient_sound.stop()
            print('[Ambience] Ambient sound stopped')
        except Exception:
            pass


def set_ambient_volume(volume):
    """
    Change ambient sound volume.
    
    Args:
        volume: Volume level (0.0-1.0)
    """
    global AMBIENT_VOLUME
    AMBIENT_VOLUME = volume
    
    if _ambient_sound is not None:
        try:
            _ambient_sound.volume(AMBIENT_VOLUME)
            print(f'[Ambience] Ambient volume set to {AMBIENT_VOLUME}')
        except Exception:
            pass


def is_fog_active():
    """Check if fog is currently active."""
    return _fog_active


def is_sound_active():
    """Check if sound is currently active."""
    return _sound_active


def disable_fog_on_node(node):
    """
    Disable fog effect on a specific node (like the floor).
    Call this after init() to exclude specific objects from fog.
    
    Args:
        node: The viz node to disable fog on
    """
    try:
        node.disable(viz.FOG)
        print(f'[Ambience] Fog disabled on node: {node}')
    except Exception as e:
        print(f'[Ambience] Failed to disable fog on node: {e}')


def enable_fog_on_node(node):
    """
    Re-enable fog effect on a specific node.
    
    Args:
        node: The viz node to enable fog on
    """
    try:
        node.enable(viz.FOG)
        print(f'[Ambience] Fog enabled on node: {node}')
    except Exception as e:
        print(f'[Ambience] Failed to enable fog on node: {e}')
