[//]: # "Concise Copilot instructions merged and simplified for quick AI onboarding"
[//]: # "Concise Copilot instructions for quick AI onboarding"

# AI Coding Agent Instructions — pacman (concise)

This is a small Vizard-based Pac‑Man prototype. The notes below capture the concrete, repo-specific patterns an AI coding agent should follow to be productive quickly.

**Big picture:** single-process runtime. The main per-frame loop lives in `horrorpackman/horrorpackman.py` and is driven by `vizact.ontimer(0, on_update)`. Most game logic (movement, AI, animation, collisions, camera math) runs inside `on_update()`.

**Key files (jump here first):**

- `horrorpackman/horrorpackman.py` — application entry; top-level UPPER_SNAKE_CASE constants; `on_update()` (movement/AI/animation); `update_camera(dt)` (camera math).
- `horrorpackman/MapLoader.py` — builds the maze from `assets/` and `Map_Grid.txt`; computes `_pacmap_center` and bounds used by key placement.
- `horrorpackman/KeyLoader.py` — parses `Map_Grid.txt` and provides `spawn_keys_on_map()`; uses the map center to align keys.
- `horrorpackman/KeyCollector.py` — runtime component attached to the player for key pickup logic.
- `horrorpackman/PacMan_exe.py` — launcher that assembles the map, spawns keys, and starts the runtime (use this for end-to-end testing).
- `horrorpackman/PacManAI.py` and `PacManLoaderAndAnimations.py` — AI helpers and model/animation loading patterns.

**Project-specific conventions (follow exactly):**

- Constants: change only at the very top of `horrorpackman.py` (UPPER_SNAKE_CASE). Other files expect those values.
- Model loads: always wrap external asset loads in `try/except` and provide primitive fallbacks (see `load_model()` in `horrorpackman.py` and `_load_key_model()` in `KeyLoader.py`).
- Entity wrappers: create a wrapper group via `viz.addGroup()`, attach visuals to that group, and transform the wrapper (do not transform children directly).
- Timing: put all deterministic updates (movement, AI, animation) in `on_update()` — do NOT create per-entity timers. This ensures consistent single-threaded updates.
- Logging: use short bracketed tags like `[Model]`, `[Map]`, `[Key]`, `[Camera]`. Avoid high-frequency prints (e.g., per-frame) to prevent console spam.

**Where to change behavior (common edit points):**

- Camera smoothing/math: `update_camera(dt)` in `horrorpackman.py` (this returns forward/horizontal vectors used by movement code).
- Player movement / AI / collisions / animation: `on_update()` in `horrorpackman.py` and supporting functions in `PacManAI.py`.
- Map layout: edit `Map_Grid.txt` (root) and adjust `MapLoader.build_map()` to choose assets for different characters.
- Key placement: `KeyLoader.spawn_keys_on_map(grid_path, cell_size, num_keys, spawn_chance, attach_to_map)` — use these params when tuning spawn behavior.

**Runtime & debugging (PowerShell):**

- Run the core runtime for camera/player iteration: `python horrorpackman\\horrorpackman.py`.
- Run the full launcher (map + keys): `python horrorpackman\\PacMan_exe.py`.
- In-session keys: `W/A/S/D` move, `R` restart, `Esc` quit, `Tab` toggle mouse lock, `F` toggle FP/TP, `K` point camera/player to nearest key.

**Assets & dependencies:**

- Assets live in `horrorpackman/assets/`. Asset loads must tolerate missing files via fallbacks so the scene remains testable.
- The project expects the `viz` (Vizard) environment. If not present, many modules will fail — prefer running inside the developer's Vizard setup.

**Concrete code patterns to reuse:**

- Model fallback: `load_model(asset_path, scale, tint)` returns a `viz.addGroup()` wrapper and falls back to primitives when files are missing.
- Centering helper: use `_center_glb_local_in_wrapper(raw)` (used across loaders) to align model pivots and bottom-align to the floor.
- Map-key alignment: `MapLoader.load_pacmap()` computes `_pacmap_center`; `KeyLoader.spawn_keys_on_map()` uses that center and the emoji-grid in `Map_Grid.txt` (look for `🟪`) to position keys.

If any part is unclear or you want an example patch (for example, add a ghost spawn in `on_update()`), tell me which area to expand and I'll prepare a focused change.
