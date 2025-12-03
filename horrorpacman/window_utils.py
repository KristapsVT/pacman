def _maximize_window():
    try:
        import platform
        import os
        try:
            import viz
        except Exception:
            return

        if hasattr(viz, 'setOption'):
            try:
                viz.setOption('viz.fullscreen', 1)
            except Exception:
                pass
        if platform.system() == 'Windows':
            try:
                os.environ['VIZ_FULLSCREEN'] = '1'
            except Exception:
                pass
    except Exception:
        pass
