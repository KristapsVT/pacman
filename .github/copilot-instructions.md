[//]: # "Concise Copilot instructions merged and simplified for quick AI onboarding"

# AI Coding Agent Instructions — pacman (concise)

This file contains the minimal, actionable knowledge an AI coding agent needs to be immediately productive in this Vizard-based Pac‑Man prototype.

**Big picture:** single-process runtime driven by `horrorpackman/horrorpackman.py`. Per-frame updates (AI, input, camera, animation) run from `vizact.ontimer(0, on_update)`.

**Key files:**

- `horrorpackman/horrorpackman.py`: entry, constants (top of file), `on_update()`, `update_camera(dt)`.
- `MapLoader.py`: parses `Map_Grid.txt` and spawns maze and colliders.
- `KeyLoader.py`: input handlers and `keys` dict used by `on_update()`.
- `PacMan_exe.py` and `PacManLoaderAndAnimations.py`: model-loading patterns and fallbacks.

**Project conventions (must follow):**

- Constants: change only at the top of `horrorpackman.py` in UPPER_SNAKE_CASE.
- Model loads: always wrap external asset loads in `try/except` and provide primitive fallbacks (see `PacMan_exe.py`).
- Entities: create a wrapper group (`viz.addGroup()`), attach model children, and transform the wrapper (avoid transforming children directly).
- Timing: do NOT create per-entity timers; put deterministic updates for movement/AI/animation inside `on_update()`.
- Logging: use short bracketed tags like `[Model]`, `[Camera]`, `[Map]`, `[Ghost]`; avoid per-frame prints.

**Where to change behavior:**

- Camera math/smoothing: edit `update_camera(dt)` (it returns a horizontal forward vector used for movement).
- Movement / AI / collisions / animation: edit `on_update()` in `horrorpackman.py`.
- Map layout / spawn rules: edit `Map_Grid.txt` and `MapLoader.build_map(parent)`.

**Runtime & debug:**

- Start (PowerShell): `python horrorpackman\\horrorpackman.py` (requires Vizard available in Python environment).
- In-session keys: `R` restart, `Esc` quit, `W/A/S/D` move, `F` toggle camera view.

**Concrete patterns / examples:**

- Add a ghost: `g = viz.addGroup()`; load model in `try/except`; log `[Ghost] init`; update wrapper position/yaw from `on_update()`.
- Model fallback: if `assets/` model missing, create a primitive (sphere/box) to preserve tests and iteration speed.
- Camera smoothing: tune `exp_smooth_factor` inside `update_camera`, do not re-smooth movement elsewhere.

If anything in this concise guide is unclear or you want extra examples (e.g., add a sample ghost spawn + `on_update()` patch), say which area to expand.
