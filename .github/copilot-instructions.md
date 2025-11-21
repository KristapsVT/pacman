[//]: # "Concise Copilot instructions merged and simplified for quick AI onboarding"
[//]: # "Concise Copilot instructions for quick AI onboarding"

# AI Coding Agent Instructions — pacman (concise)

This repository is a small Vizard-based Pac‑Man prototype. Below are the minimal, concrete patterns an AI agent needs to be productive.

**Big picture:** single-process runtime. The main loop is in `horrorpackman/horrorpackman.py` and executes per-frame logic via `vizact.ontimer(0, on_update)`.

**Key files (jump here first):**

- `horrorpackman/horrorpackman.py` — application entry, top-level UPPER_SNAKE_CASE constants, `on_update()` (movement/AI/animation), `update_camera(dt)` (camera math).
- `MapLoader.py` — loads maze parts from `assets/`, provides `load_pacmap()` and caches `_pacmap_center`/\_bounds used by `KeyLoader`.
- `KeyLoader.py` — reads `Map_Grid.txt` (purple cell emoji `🟪`) and spawns keys with `spawn_keys_on_map()`; returns nodes or logical positions.
- `PacMan_exe.py` — lightweight launcher that imports the runtime, then builds the map, keys and initializes `KeyCollector`.

**Project-specific conventions (follow exactly):**

- Constants: change only at the very top of `horrorpackman.py` (UPPER_SNAKE_CASE).
- Model loads: always wrap external asset loads in `try/except` and provide primitive fallbacks (see `load_model()` in `horrorpackman.py` and `_load_key_model()` in `KeyLoader.py`).
- Entities: create a wrapper group via `viz.addGroup()`, attach child visuals, and transform the wrapper (avoid transforming children directly).
- Timing: put all deterministic updates (movement, AI, animation) in `on_update()` — do NOT create per-entity timers.
- Logging: use short bracketed tags like `[Model]`, `[Map]`, `[Key]`, `[Camera]`; avoid printing every frame.

**Where to change behavior (common edit points):**

- Camera smoothing/math: `update_camera(dt)` in `horrorpackman.py` (returns horizontal forward vector used by movement).
- Player movement / AI / collisions / animation: `on_update()` in `horrorpackman.py`.
- Map layout: `Map_Grid.txt` (root) and `MapLoader.build_map()` for which assets to use.
- Key placement: `KeyLoader.spawn_keys_on_map()` — parameters: `grid_path`, `cell_size`, `num_keys`, `spawn_chance`, `attach_to_map`.

**Runtime & debugging commands (PowerShell):**

- Run main runtime directly: `python horrorpackman\\horrorpackman.py` (use when iterating camera/player code).
- Run the launcher that also builds map/keys: `python horrorpackman\\PacMan_exe.py`.
- In-session keys: `W/A/S/D` move, `R` restart, `Esc` quit, `Tab` toggle mouse lock, `F` toggle FP/TP, `K` points camera/player to nearest key.

**Concrete examples / code patterns:**

- Model fallback: `load_model(asset_path, scale, tint)` returns a `viz.addGroup()` wrapper; if the file is missing it creates primitives (sphere/cylinder) so scenes remain testable.
- Wrapper + centering: many loaders call helper `_center_glb_local_in_wrapper(raw)` to align model pivot and bottom-align to floor — reuse this when adding models.
- Map-key alignment: `MapLoader.load_pacmap()` computes `_pacmap_center`; `KeyLoader.spawn_keys_on_map()` uses that center and `Map_Grid.txt` to place keys consistently.

If any part is unclear or you want an example patch (e.g., add a sample ghost spawn + `on_update()` patch), tell me which area to expand and I will add it.
