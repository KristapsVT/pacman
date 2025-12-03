AI Coding Agent Instructions — pacman (concise)

This repo is a small Vizard-based Pac‑Man prototype. The notes below capture the concrete, repo-specific patterns an AI coding agent should follow to be productive quickly.

Big picture

- Single-process runtime: `Player.py` is the main runtime that sets up the scene, input, and the single update loop driven by `vizact.ontimer(0, on_update)`.
- `PacMan_exe.py` is a launcher that composes the map, keys, locks, and spawns Pac‑Man (it imports `Player` and schedules delayed spawn).
- Map visuals and key placement are separate: `MapLoader.py` builds the geometry and caches `_pacmap_center`/`_pacmap_bounds`; `KeyLoader.py` reads `Map_Grid.txt` (uses `🟪` for key cells) and aligns keys to the map center.

Quick run commands (PowerShell)

- Run the full launcher: `python horrorpackman\PacMan_exe.py`
- Run the core runtime directly: `python horrorpackman\Player.py`

Project-specific conventions

- Top-level constants live in `Player.py` (e.g. `CELL_SIZE`, `PLAYER_*`, camera constants). Change them only there — other modules assume those values.
- Single update loop: put movement, AI, animation, and collision logic inside the `on_update()` timer (avoid per-entity timers).
- Asset loads must be defensive: wrap `viz.addChild()` calls in `try/except` and fall back to primitives. See `load_model()` in `Player.py` and `_load_key_model()` in `KeyLoader.py`.
- Use wrapper groups for models: create a `viz.addGroup()` wrapper, attach the raw child, then transform the wrapper. Helpers like `_center_glb_local_in_wrapper` (present in `Player.py` and `KeyLoader.py`) align pivot and bottom.

Key integration points

- MapLoader -> KeyLoader: `load_pacmap()` sets `group._pacmap_center` and `_pacmap_bounds`. `KeyLoader.spawn_keys_on_map()` reads those to place keys relative to the map.
- Player grid alignment: `Player.py` reads `Map_Grid.txt` to compute `_grid_origin_x/_z` and `_world_to_grid()` for optional grid-based collision and centering. `CELL_SIZE` must match across modules.
- External Pac-Man AI: `Player.py` honors `os.environ['EXTERNAL_PACMAN_AI']`. `PacMan_exe.py` sets this and spawns Pac‑Man visuals + AI after a delay.
- Key collection: call `KeyCollector.init(player_node)` after `player` exists to enable keyboard pickup (`E`) and HUD/collection behavior.

Common edit points

- Change map assets: edit `PACMAP_PARTS` in `MapLoader.py` or place GLB files into `horrorpackman/assets/`.
- Tweak key placement: call `spawn_keys_on_map(..., cell_size=<value>, spawn_chance=<0..1>, num_keys=<n>)` from `PacMan_exe.py` or tests.
- Re-enable grid collisions: set `PLAYER_COLLISION_ENABLED = True` in `Player.py` and ensure `Map_Grid.txt` and `CELL_SIZE` align.

Defensive patterns to follow

- Accept missing `viz` APIs and missing assets; modules use fallbacks. Mirror that approach when adding features.
- Keep visual changes localized to wrapper groups; avoid transforming model internals.
- Avoid noisy per-frame prints; use bracketed short tags like `[Map]`, `[Key]`, `[ExE]` for logging.

Files to inspect for examples

- `Player.py` — main runtime, camera math, input, constants.
- `PacMan_exe.py` — launcher orchestration and delayed spawn pattern.
- `MapLoader.py` — map part loading, fallback primitives, `_pacmap_center` caching.
- `KeyLoader.py` — grid parsing, farthest-point sampling for key spread, key model loading.
- `KeyCollector.py` — pickup logic and safe node removal (use as reference for safe viz node handling).

If something is unclear or you want a focused patch (e.g., re-enable collisions, add ghost spawn, or change key spawn behavior), say which file and I will prepare a small, focused change.
"""
AI Coding Agent Instructions — pacman (concise)

This repo is a small Vizard-based Pac‑Man prototype. The project is single-process: the Player runtime creates scene nodes and uses `vizact.ontimer`-driven updates. The guidance below captures concrete, repo-specific patterns to help an AI agent be productive immediately.

Big picture: The active runtime lives in `horrorpackman/Player.py` (imported by `PacMan_exe.py` for end-to-end runs). Map construction, key spawning, and optional Pac‑Man animation/AI are composed by the launcher `PacMan_exe.py`.

Key files (jump here first):

- `horrorpackman/Player.py` — main runtime; top-level constants and player setup.
- `horrorpackman/PacMan_exe.py` — launcher that imports `Player`, builds the map, spawns keys/locks, and schedules the Pac‑Man spawn.
- `horrorpackman/MapLoader.py` — `load_pacmap(parent=None, apply_style=True)` returns `(group, floor_node, wall_nodes)` and caches `_pacmap_center` / `_pacmap_bounds` on the group.
- `horrorpackman/KeyLoader.py` — `spawn_keys_on_map(parent, map_root, attach_to_map, visualize, grid_path, cell_size, ...)` reads `Map_Grid.txt` (use `CELL_EMOJI = '🟪'`) and returns `(group, keys)`.
- `horrorpackman/KeyCollector.py` — call `KeyCollector.init(player)` after the `player` node is created to enable pickup logic.
- `horrorpackman/PacManAI.py` & `PacManLoaderAndAnimations.py` — AI helpers and Pac‑Man visual spawn.
- `Map_Grid.txt` — emoji grid used by `KeyLoader` to pick spawn cells.

Repository conventions & patterns:

- Top-level constants: change only in `Player.py` (UPPER_SNAKE_CASE); other modules depend on these values.
- Asset loading: wrap external loads in `try/except` and provide primitive fallbacks (see `_safe_add_child()` in `MapLoader.py` and `_load_key_model()` in `KeyLoader.py`).
- Wrapper groups: create visuals inside a `viz.addGroup()` wrapper and transform the wrapper (do not transform child nodes directly).
- Single update loop: deterministic updates (movement, AI, animation) are driven by `vizact.ontimer(0, ...)` or similar timers. Avoid per-entity timers.
- Logging: use short bracketed tags like `[Map]`, `[Key]`, `[ExE]` to make console output traceable.

Common edit points:

- Map visuals / layout: edit `Map_Grid.txt` or `PACMAP_PARTS` in `MapLoader.py` to change floor/wall assets.
- Key spawning: call `spawn_keys_on_map(...)` with `cell_size`, `spawn_chance`, `num_keys` to tune placement — it uses a farthest-point sampler to spread keys.
- Pac‑Man spawn: `PacMan_exe.py` sets `os.environ['EXTERNAL_PACMAN_AI']='1'` and schedules `vizact.ontimer(3.0, _delayed_spawn)` to attach animation and `PacManChaser` AI.

Concrete code snippets & helpers (examples):

- Create/attach map: `pacmap_root, floor_node, wall_nodes = MapLoader.load_pacmap(apply_style=True)`
- Spawn keys (attach to map): `keys_group, keys = KeyLoader.spawn_keys_on_map(parent=pacmap_root, map_root=pacmap_root, attach_to_map=True)`
- Initialize collector: `KeyCollector.init(player_node)` (call after `player` exists)
- Use centering helper: `_center_glb_local_in_wrapper(raw, center_blend=0.6, desired_bottom=0.0)` is used by `KeyLoader` for model alignment.

Runtime & quick commands (PowerShell):
Run launcher from repo root (Windows PowerShell):

```
python horrorpackman\PacMan_exe.py
```

Or run Player directly for iteration:

```
python horrorpackman\Player.py
```

Notes: the project expects the `viz` (Vizard) environment. If `viz` is missing, many modules will fail; keep fallbacks in mind during edits.

If you want an example patch (e.g., add a ghost spawn in the update loop, or change key spawn logic), say which file to modify and I will prepare a focused change.
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
