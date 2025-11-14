# AI Coding Agent Instructions for `pacman`

Concise, project-specific guidance to make productive, low-noise contributions. Focus on existing patterns; avoid generic boilerplate.

## 1. Purpose & Entry Point

Prototype Pac-Man style sandbox in Vizard (modules: `viz`, `vizact`, `vizshape`). Single runtime script: `horrorpackman/horrorpackman.py`. No packaging, no test suite, no extra build steps.

## 2. High-Level Architecture

Single process, frame timer loop (`vizact.ontimer(0, on_update)`). Responsibilities split:

- Config constants (top of file) govern movement, camera, arena.
- Player assembly (`load_player_model`) returns a group wrapper; transformations apply to wrapper not raw child.
- Camera logic isolated in `update_camera(dt)`; movement logic in `on_update()` consumes horizontal forward vector returned by camera.
- Bounds enforcement via `within_arena(node, radius)` (axis-aligned clamp in X/Z).
- Input captured by key state dict (`keys`) updated via `vizact.onkeydown/onkeyup` lambdas.
  Data flow per frame: input states -> movement vector -> player position clamp -> camera recompute -> view transform.

## 3. Runtime & Commands

Run with PowerShell (Vizard installed and importable):

```powershell
python horrorpackman\horrorpackman.py
```

No arguments currently. Restart in-session uses key `R`. If `assets/Person.glb` absent, primitive fallback auto-builds (non-fatal).

## 4. Core Patterns & Conventions

- Constants: UPPER_SNAKE_CASE; extend here (e.g. add `GHOST_SPEED`) rather than scattering magic numbers.
- Assets: Always relative via `os.path.join`; keep additions centralized as constants.
- Pure helpers (math, smoothing) side-effect free; keep new math utilities similar.
- Group wrappers for composite models (player, future ghosts) to avoid per-child transforms.
- Perspective toggling: global `FIRST_PERSON` plus visibility flip; mirror pattern for additional modes (e.g. cinematic) via boolean flags.
- Facing logic decoupled with `FACE_STRAFE_ONLY`; introduce new orientation styles through flags, not deep branching.

## 5. Camera & Movement

`update_camera` calculates yaw/pitch, derives a horizontal forward (ignores pitch) for movement. Third-person uses spherical offset with optional exponential smoothing (`exp_smooth_factor`). Maintain separation: do not merge camera interpolation into movement code. Clamp pitch with `PITCH_LIMIT` and floor with `CAMERA_MIN_HEIGHT_TP`.

## 6. Map / Level Extension (`MapLoader.py`)

Currently empty. Recommended pattern: symbolic grid -> iterate -> spawn walls via `vizshape.addBox`. Provide a `build_map(parent)` function returning a group. Integrate directly after floor/border creation. For collision beyond rectangular boundary, add spatial test before calling `within_arena` (keep clamp as fallback).

## 7. Adding Entities (Ghosts, Pellets)

Ghost template:

1. Create group wrapper.
2. Load model or primitives (with color tag). Log `[Ghost]` messages.
3. Track local yaw; update in shared `on_update()` (batch updates) rather than multiple timers.
4. Reuse `within_arena` for coarse bounds; refine with future maze collision.
   Pellets: lightweight spheres; maintain a list; simple AABB or radial overlap with player each frame.

## 8. Logging & Diagnostics

Use short bracketed tags: `[Model]`, `[Camera]`, `[Map]`, `[Ghost]`. Avoid per-frame prints. Only log one-time initialization, mode toggles, load errors.

## 9. Error Handling & Fallbacks

Model load wrapped in `try/except`; continue on failure with primitives. Follow same pattern for new optional assets. Never terminate runtime for missing cosmetic assets.

## 10. Performance Notes

Single timer loop—keep new per-frame work minimal (basic math only). Batch entity updates; avoid creating additional high-frequency timers. Cache expensive geometry queries (bounding boxes) at load time only.

## 11. Safe Modification Guidelines

- Do not rename existing constants unless updating all references.
- Preserve function boundaries: camera math stays in `update_camera`; player movement stays in `on_update`.
- Maintain relative paths; no absolute Windows paths.
- Add new flags rather than altering existing semantics (e.g., keep `FIRST_PERSON` meaning consistent).

## 12. Quick Reference Keys

W/A/S/D move | R restart | Esc quit | Tab mouse lock toggle | F FP/TP toggle (also flips invert Y)

## 13. Pre-Commit Checklist

1. Script runs without import errors (Vizard available).
2. Player loads (fallback acceptable) and camera toggles with no jitter.
3. Bounds clamping still effective after changes.
4. New entities respect clamp or custom collision.

## 14. Areas for Clarification

Map format & collision abstraction unimplemented; pellet & scoring system absent. Provide feedback if formalizing these would help future contributions.

---

Feedback welcome: note unclear sections (e.g. desired maze representation) for iterative refinement.
