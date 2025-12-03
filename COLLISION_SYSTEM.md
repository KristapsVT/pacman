# Collision System

The game uses raycast-based collision detection with sliding response to prevent glitching, jitter, and wall penetration in Vizard.

## Highlights

- Raycasts via `viz.intersect()` in a cone around movement.
- Multiple heights (feet/waist/head) for robust hits.
- Sliding response: try X-only and Z-only when blocked.
- Third-person camera collision with pull-forward when obstructed.

## Configuration

```python
# Raycast collision settings
USE_RAYCAST_COLLISION = True    # Enable raycast (recommended)
COLLISION_BUFFER = 0.3          # Stand-off from walls (penetration guard)
COLLISION_RAYS = 8              # Rays in the cone (accuracy/perf tradeoff)
CAMERA_COLLISION_ENABLED = True # Prevent camera wall penetration

# Legacy grid collision (disabled by default)
PLAYER_COLLISION_ENABLED = False
```

## How It Works

1. Compute desired position from input and `dt`.
2. Cast rays from current to desired position at three heights.
3. If any ray hits, compute the safe position (buffered).
4. If blocked, test X-only then Z-only movement (pick the best).
5. Move to the final safe position.

### Camera (Third-Person)

- Cast a ray from player to camera.
- If it hits, place camera at the hit point minus buffer; apply smoothing.

## Advantages

- Works with arbitrary geometry; no grid alignment required.
- Predictive, deterministic, and lightweight (no physics).
- Smooth sliding along diagonals; avoids sticky corners.

## Performance

- ~24 rays/frame while moving (8 rays × 3 heights).
- Low CPU cost (Vizard raycasts are hardware-accelerated).
- Pure geometric queries, no physics engine overhead.

## Tuning Cheatsheet

- Player too far from walls: lower `COLLISION_BUFFER` (0.2–0.15).
- Penetration occurs: raise `COLLISION_BUFFER` (0.4–0.5) or `COLLISION_RAYS` (12–16).
- Movement sluggish near walls: lower `COLLISION_RAYS` (4–6) and/or raise `PLAYER_SPEED`.
- Camera jitter: enable smoothing, raise damping, verify `CAMERA_COLLISION_ENABLED`.

## API Surface

- `check_collision_raycast(from_pos, to_pos, check_height) -> (collided, safe_pos)`
- `slide_collision(from_pos, desired_pos, check_height) -> final_position`
- `check_camera_collision(cam_pos, target_pos) -> safe_cam_pos`

## Usage in Update Loop

```python
# In on_update():
if mx or mz:
   vx = right_x*mx + hfx*mz
   vz = right_z*mx + hfz*mz

   x, y, z = player.getPosition()
   desired_pos = [x + vx*PLAYER_SPEED*dt, y, z + vz*PLAYER_SPEED*dt]

   final_pos = slide_collision([x,y,z], desired_pos, check_height=CAMERA_HEIGHT_FP)
   player.setPosition(final_pos)
```

## Troubleshooting

- Goes through walls: ensure `USE_RAYCAST_COLLISION = True`; verify wall geometry collision; increase buffer/rays.
- Screen jitter: enable camera smoothing; raise damping; confirm `CAMERA_COLLISION_ENABLED`.
- Stuck in corners: increase `COLLISION_BUFFER`; verify both X/Z slides execute.
- Camera clips: enable camera collision; increase buffer; check raycasts.

## Best Practices

- Keep `COLLISION_BUFFER` around 0.2–0.4.
- Use 6–8 rays for a good accuracy/performance balance.
- Enable camera collision in third-person.
- Test in tight corridors and corners when tuning.

## Legacy

The old grid-based collision (`PLAYER_COLLISION_ENABLED`) remains for backward compatibility but should stay disabled.
