# Pac‑Man Prototype (Vizard)

Vizard-based Pac‑Man with player movement, map loading, keys/locks, Pac‑Man AI, ambience.

## Quick Start
- Prerequisite: Install WorldViz Vizard (provides the `viz`/`vizact` APIs).
- Simplest way (Vizard app): Open `horrorpackman\PacMan_exe.py` in Vizard and press Run.
- From repo root (PowerShell) with Vizard's Python:
	- Run full launcher (map + keys + locks + delayed Pac‑Man spawn):
		- `Pacman/horrorpackman\PacMan_exe.py`

## Controls
- Move: `W/A/S/D`
- Quit: `Esc`
- Toggle mouse lock: `Tab`
- Toggle First/Third person: `F`
- Free cam toggle: `C` (then `W/A/S/D`, `Q/E` up/down)

## Project Structure
- `horrorpackman/Player.py`: Main runtime (camera, input, single update loop).
- `horrorpackman/PacMan_exe.py`: Launcher (builds map, spawns keys/locks, schedules Pac‑Man).
- `horrorpackman/MapLoader.py`: Loads floor/walls and caches map center/bounds.
- `horrorpackman/KeyLoader.py`: Spawns keys from `Map_Grid.txt` (🟪 cells).
- `horrorpackman/LockLoader.py` + `LockUnlocker.py`: Simple lock placement/unlock logic.
- `horrorpackman/PacManAI.py`: Pac‑Man chaser logic and helpers.
- `horrorpackman/PacManLoaderAndAnimations.py`: Pac‑Man model/animation loading.
- `horrorpackman/KeyCollector.py`: Key pickup logic (init after player exists).
- `horrorpackman/GameOver.py`: Shows game-over message + countdown, then closes.
- `horrorpackman/Ambience.py`: Fog + background/death audio control.
- `Map_Grid.txt`: Emoji grid that defines map layout and valid key cells.

## Ambience (Fog + Audio)
- File: `horrorpackman/Ambience.py`.
- Fog settings:
	- `FOG_ENABLED`: Enable/disable fog.
	- `FOG_MODE`: `'LINEAR'` or `'EXPONENTIAL'`.
	- `FOG_START`, `FOG_END` (linear), `FOG_DENSITY` (exponential), `FOG_COLOR`.
- Audio settings:
	- Ambient file: `assets/horror-bg.mp3` (looped).
	- Death sound: `assets/death.wav` (falls back to `crunch.*`).
	- Trim the start of death sound: `DEATH_TRIM_START_SEC`.
	- Change volumes with `AMBIENT_VOLUME`, `DEATH_VOLUME`.

## Game Over
- Trigger: Pac‑Man collides with player.
- Behavior: Prints `[GameOver] Player squished by Pac-Man!`, plays death sound, shows on-screen message + countdown, then closes Vizard.

## Pac‑Man AI
- Spawns after a short delay in `PacMan_exe.py`.
- Uses grid from `Map_Grid.txt` and the cached map center/bounds.
- Collision sensitivity can be adjusted via radii in `PacManAI.py` and `Player.py`.

## Keys & Locks
- Keys are spawned on 🟪 cells from `Map_Grid.txt` using `KeyLoader.spawn_keys_on_map(...)`.
- Locks are spawned by `LockLoader.spawn_locks_on_map(...)` and can be unlocked with collected keys via `LockUnlocker`.
- Initialize pickup system after player exists: `KeyCollector.init(player)`.

## Troubleshooting
- Missing `viz`/`vizact` errors: run inside a Vizard environment.
- No ambient audio: ensure file exists under `horrorpackman/assets/`.
- Fog issues: match `FOG_COLOR` to `viz.clearcolor` and tune `FOG_START/END` or switch to `'EXPONENTIAL'`.

## Notes
- Single-process runtime with a single `vizact.ontimer(0, on_update)` update loop.
- Asset loads are defensive; fallbacks are used if assets are missing.
