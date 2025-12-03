import viz
import vizact

_game_over_active = False
_game_over_text = None
_countdown_text = None

def show_game_over_and_close():
    global _game_over_active, _game_over_text, _countdown_text
    
    if _game_over_active:
        return  
    
    _game_over_active = True
    print('[GameOver] Player squished by Pac-Man!')
    
    try:
        import Ambience
        Ambience.play_death_sound()
    except Exception:
        pass
    
    try:
        _game_over_text = viz.addText('You have been squished by Pac-Man!', parent=viz.SCREEN)
        _game_over_text.setPosition(0.5, 0.6)  
        _game_over_text.alignment(viz.ALIGN_CENTER_TOP)
        _game_over_text.fontSize(42)
        _game_over_text.color(viz.RED)
        _countdown_text = viz.addText('Closing in 3...', parent=viz.SCREEN)
        _countdown_text.setPosition(0.5, 0.5) 
        _countdown_text.alignment(viz.ALIGN_CENTER_TOP)
        _countdown_text.fontSize(32)
        _countdown_text.color(viz.WHITE)
    except Exception as e:
        print(f'[GameOver] Failed to create text: {e}')
        import traceback
        traceback.print_exc()
    
    countdown_values = [3, 2, 1]
    
    def update_countdown(count_index):
        if count_index < len(countdown_values):
            try:
                if _countdown_text:
                    _countdown_text.message(f'Closing in {countdown_values[count_index]}...')
            except Exception:
                pass
            vizact.ontimer(1.0, update_countdown, count_index + 1)
        else:
            try:
                if _countdown_text:
                    _countdown_text.message('Closing...')
            except Exception:
                pass
            vizact.ontimer(0.5, close_window)
    
  
    update_countdown(0)

def close_window():
    """Close the Vizard window (same as ESC key)."""
    print('[GameOver] Closing Vizard window...')
    viz.quit()

def is_game_over():
    """Check if game over has been triggered."""
    return _game_over_active
