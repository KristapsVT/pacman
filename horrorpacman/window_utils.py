"""Window helper utilities extracted from `horrorpackman.py`.

This module exposes a `_maximize_window()` helper that attempts to
request fullscreen from the Vizard `viz` runtime and perform a
platform-specific hint on Windows.
"""
def _maximize_window():
    try:
        import platform
        import os
        # `viz` is expected to be provided by the runtime environment.
        # Import locally so this module doesn't require `viz` until called.
        try:
            import viz
        except Exception:
            return

        if hasattr(viz, 'setOption'):
            # ask Vizard to open fullscreen if supported (do this before viz.go to avoid flicker)
            try:
                viz.setOption('viz.fullscreen', 1)
            except Exception:
                pass
        # On Windows we can also try to set environment variable to hint fullscreen
        if platform.system() == 'Windows':
            try:
                os.environ['VIZ_FULLSCREEN'] = '1'
            except Exception:
                pass
    except Exception:
        pass
