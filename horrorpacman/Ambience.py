import viz
import vizact
import os


BASE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
def _asset_path(name):
    try:
        return os.path.normpath(os.path.join(ASSETS_DIR, name))
    except Exception:
        return name

FOG_ENABLED         = True      
FOG_START           = 6.0      
FOG_END             = 35.0      
FOG_DENSITY         = 0.15      
FOG_COLOR           = [0.0, 0.0, 0.0]  
FOG_MODE            = 'LINEAR' 

SOUND_ENABLED       = True      
AMBIENT_SOUND_FILE  = _asset_path('horror-bg.mp3')  
DEATH_SOUND_FILE    = _asset_path('crunch.mp3')     
KEY_PICKUP_SOUND_FILE = _asset_path('key-get.mp3')   
LOCK_UNLOCK_SOUND_FILE = _asset_path('lock-unlock.mp3')   
AMBIENT_VOLUME      = 0.15      
AMBIENT_LOOP        = True      
AMBIENT_PITCH       = 1.0       
DEATH_VOLUME        = 0.5

_ambient_sound = None
_death_sound = None
_fog_active = False
_sound_active = False

def init():
    global _fog_active, _sound_active
    
    if FOG_ENABLED:
        _fog_active = setup_fog()
    else:
        print('[Ambience] Fog disabled')
    
    if SOUND_ENABLED:
        _sound_active = setup_sound()
    else:
        print('[Ambience] Sound disabled')

def setup_fog():
    try:
        viz.MainScene.fogColor(FOG_COLOR)
        print(f'[Ambience] Setting fog color: {FOG_COLOR}')

        if FOG_MODE == 'LINEAR':
            viz.MainScene.fog(FOG_START, FOG_END)
            print(f'[Ambience] Fog enabled: LINEAR mode, start={FOG_START}m, end={FOG_END}m')
        else:
            viz.MainScene.fog(FOG_DENSITY)
            print(f'[Ambience] Fog enabled: EXPONENTIAL mode, density={FOG_DENSITY}')
        
        return True
    except Exception as e:
        print(f'[Ambience] Failed to setup fog: {e}')
        import traceback
        traceback.print_exc()
        return False

def setup_sound():
    global _ambient_sound, _footstep_sound, _death_sound
    
    try:
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

                    viz.playSound(AMBIENT_SOUND_FILE, viz.LOOP)
                    print(f'[Ambience] Ambient started with viz.playSound loop: {AMBIENT_SOUND_FILE}')
                    started = True
                except Exception as e2:
                    print(f'[Ambience] viz.playSound failed: {e2}')
            if not started:
                print('[Ambience] No ambient audio could be started. Check assets folder.')

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
 
    global _fog_active
    try:
        viz.MainScene.fog(1000.0, 2000.0)  
        _fog_active = False
        print('[Ambience] Fog disabled')
    except Exception as e:
        print(f'[Ambience] Failed to disable fog: {e}')

def enable_fog():

    global _fog_active
    if setup_fog():
        _fog_active = True

def set_fog_distance(start, end):
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

    global FOG_DENSITY
    FOG_DENSITY = density
    
    if _fog_active and FOG_MODE != 'LINEAR':
        try:
            viz.MainScene.fog(FOG_DENSITY)
            print(f'[Ambience] Fog density updated: {FOG_DENSITY}')
        except Exception as e:
            print(f'[Ambience] Failed to update fog density: {e}')


def play_death_sound():
    global _death_sound
    try:
        
        if _death_sound is None:
            if os.path.exists(DEATH_SOUND_FILE):
                try:
                    _death_sound = viz.addAudio(DEATH_SOUND_FILE)
                    _death_sound.volume(DEATH_VOLUME)
                except Exception:
                    _death_sound = None
        if _death_sound is not None:
            _death_sound.play()
        else:

            try:
                viz.playSound(DEATH_SOUND_FILE)
            except Exception:
                pass
    except Exception:
        pass


def stop_ambient_sound():
    if _ambient_sound is not None:
        try:
            _ambient_sound.stop()
            print('[Ambience] Ambient sound stopped')
        except Exception:
            pass


def set_ambient_volume(volume):

    global AMBIENT_VOLUME
    AMBIENT_VOLUME = volume
    
    if _ambient_sound is not None:
        try:
            _ambient_sound.volume(AMBIENT_VOLUME)
            print(f'[Ambience] Ambient volume set to {AMBIENT_VOLUME}')
        except Exception:
            pass


def is_fog_active():
    return _fog_active

def is_sound_active():
    return _sound_active

def disable_fog_on_node(node):
    try:
        node.disable(viz.FOG)
        print(f'[Ambience] Fog disabled on node: {node}')
    except Exception as e:
        print(f'[Ambience] Failed to disable fog on node: {e}')

def enable_fog_on_node(node):
    try:
        node.enable(viz.FOG)
        print(f'[Ambience] Fog enabled on node: {node}')
    except Exception as e:
        print(f'[Ambience] Failed to enable fog on node: {e}')
