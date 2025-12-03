# Pac‑Man Prototype (Vizard)

Vizard-based Pac‑Man prototype with player movement, map loading, keys/locks, Pac‑Man AI, ambience, and a raycast collision system.

## Quick Start

- Prerequisite: Install WorldViz Vizard (provides the `viz`/`vizact` APIs).
- Simplest way (Vizard app): Open `horrorpacman\PacMan_exe.py` in Vizard and press Run.
- From repo root (PowerShell) with Vizard's Python:
  - Change directory to repo root and run the launcher script.

```powershell
# Example: run via Vizard’s Python
# Replace the path below with your Vizard Python if needed
"C:\Program Files\WorldViz Vizard 7\bin\python.exe" .\horrorpacman\PacMan_exe.py
```

## Controls

- Move: `W/A/S/D`
- Quit: `Esc`
- Toggle mouse lock: `Tab`
- Toggle First/Third person: `F`

## Project Structure

- `horrorpacman/Player.py`: Main runtime (camera, input, single update loop).
- `horrorpacman/PacMan_exe.py`: Launcher (builds map, spawns keys/locks, schedules Pac‑Man).
- `horrorpacman/MapLoader.py`: Loads floor/walls and caches map center/bounds.
- `horrorpacman/KeyLoader.py`: Spawns keys from `Map_Grid.txt` (🟪 cells).
- `horrorpacman/LockLoader.py` + `LockUnlocker.py`: Simple lock placement/unlock logic.
- `horrorpacman/PacManAI.py`: Pac‑Man chaser logic and helpers.
- `horrorpacman/PacManLoaderAndAnimations.py`: Pac‑Man model/animation loading.
- `horrorpacman/KeyCollector.py`: Key pickup logic (init after player exists).
- `horrorpacman/GameOver.py`: Shows game-over message + countdown, then closes.
- `horrorpacman/Ambience.py`: Fog + background/death audio control.
- `Map_Grid.txt`: Emoji grid that defines map layout and valid key cells.

## Ambience (Fog + Audio)

- Fog config in `horrorpacman\Ambience.py`:
  - `FOG_ENABLED`, `FOG_MODE` (`'LINEAR'` or `'EXPONENTIAL'`)
  - `FOG_START`, `FOG_END` (linear) or `FOG_DENSITY` (exponential)
  - `FOG_COLOR` (match `viz.clearcolor` for best visuals)
- Audio:
  - Ambient: `horrorpacman\assets\horror-bg.mp3` (looped)
  - Death: `horrorpacman\assets\death.wav` (fallbacks to `crunch.*`)
  - `DEATH_TRIM_START_SEC`, `AMBIENT_VOLUME`, `DEATH_VOLUME`

## Game Over

- Trigger: Pac‑Man collides with player.
- Behavior: Prints `[GameOver] Player squished by Pac-Man!`, plays death sound, shows on-screen message + countdown, then closes Vizard.

## Pac‑Man AI

- Spawns after a short delay in `PacMan_exe.py`.
- Uses grid from `Map_Grid.txt` and the cached map center/bounds.
- Collision sensitivity can be adjusted via radius in `PacManAI.py` and `Player.py`.

## Keys & Locks

- Keys are spawned on 🟪 cells from `Map_Grid.txt` using `KeyLoader.spawn_keys_on_map(...)`.
- Locks are spawned by `LockLoader.spawn_locks_on_map(...)` and can be unlocked with collected keys via `LockUnlocker`.
- Initialize pickup system after player exists: `KeyCollector.init(player)`.

## Troubleshooting

- Missing `viz`/`vizact` errors: run inside a Vizard environment.
- No ambient audio: ensure file exists under `horrorpacman/assets/`.
- Fog issues: match `FOG_COLOR` to `viz.clearcolor` and tune `FOG_START/END` or switch to `'EXPONENTIAL'`.

## Collision System

- Uses raycasts with sliding to avoid wall penetration and jitter.
- See `COLLISION_SYSTEM.md` for detailed configuration and tuning.

## Notes

- Single-process runtime with `vizact.ontimer(0, on_update)` update loop.
- Defensive asset loading with fallbacks if files are missing.
