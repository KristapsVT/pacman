# Collision System Documentation

## Overview
The collision system uses **raycast-based collision detection** with **sliding collision response** to prevent glitching, screen shaking, and wall penetration in Vizard.

## Key Features

### 1. **Raycast-Based Collision Detection**
- Uses `viz.intersect()` to cast rays from the player position toward the desired movement direction
- Checks multiple heights (feet, waist, head) for robust detection
- Uses a **cone of rays** (8 rays by default) spread ±45° around the main direction for better corner detection
- Maintains a `COLLISION_BUFFER` (0.3 units) to prevent penetration

### 2. **Sliding Collision Response**
- When direct movement is blocked, tries moving along X and Z axes separately
- Allows smooth "sliding" along walls instead of stopping completely
- Prevents the player from getting stuck in corners
- Chooses the axis that allows the most movement

### 3. **Camera Collision**
- In third-person mode, prevents the camera from going through walls
- Casts a ray from player to camera position
- Pulls camera forward if it would be inside a wall
- Maintains smooth camera positioning without jitter

## Configuration Constants

```python
# Raycast collision settings
USE_RAYCAST_COLLISION = True     # Enable raycast collision (recommended)
COLLISION_BUFFER = 0.3           # Distance from walls (prevent penetration)
COLLISION_RAYS = 8               # Number of rays for detection (more = smoother)
CAMERA_COLLISION_ENABLED = True  # Prevent camera wall penetration

# Legacy grid collision (can be disabled)
PLAYER_COLLISION_ENABLED = False # Old grid-based collision
```

## How It Works

### Player Movement
1. **Calculate desired position** based on input (WASD) and frame time
2. **Cast rays** from current position to desired position
3. **Detect collision** - if any ray hits geometry, calculate safe distance
4. **Apply sliding** - if blocked, try X-only and Z-only movement separately
5. **Move player** to the safest position that allows maximum movement

### Camera Collision (Third-Person)
1. **Calculate camera position** based on player position and camera offset
2. **Cast ray** from player to camera position
3. **If ray hits wall**, place camera at hit point minus buffer distance
4. **Apply smoothing** (optional) for smooth camera transitions

## Advantages Over Other Methods

### vs. Grid-Based Collision
- ✅ Works with any geometry (not limited to grid-aligned walls)
- ✅ No screen shaking from discrete grid cells
- ✅ Smooth sliding along diagonal walls
- ✅ No "sticky corners" from grid quantization

### vs. Physics Engine Collision
- ✅ Lightweight (no physics overhead)
- ✅ Deterministic and predictable
- ✅ No bouncing/jittering from physics simulation
- ✅ Easy to tune (single buffer parameter)

### vs. Bounding Box Collision
- ✅ More accurate collision detection
- ✅ Works with complex geometry
- ✅ No penetration issues from small timesteps
- ✅ Predictive (checks before moving)

## Performance

- **Raycast count per frame**: ~24 rays (8 directions × 3 heights) when moving
- **CPU cost**: Very low (raycasts are hardware-accelerated in Vizard)
- **No impact on physics engine** (pure geometric queries)

## Testing & Tuning

### If player is too far from walls:
- Decrease `COLLISION_BUFFER` (e.g., 0.2 or 0.15)

### If player still penetrates walls:
- Increase `COLLISION_BUFFER` (e.g., 0.4 or 0.5)
- Increase `COLLISION_RAYS` (e.g., 12 or 16)

### If movement feels sluggish near walls:
- Decrease `COLLISION_RAYS` (e.g., 4 or 6)
- Adjust `PLAYER_SPEED` for faster response

### If camera jitters in tight spaces:
- Enable `CAMERA_SMOOTH_TP = True`
- Increase `CAMERA_DAMPING_TP` (e.g., 18.0 or 20.0)
- Adjust `COLLISION_BUFFER` for camera

## Code Structure

### Main Functions

1. **`check_collision_raycast(from_pos, to_pos, check_height)`**
   - Returns: `(collided, safe_pos)`
   - Casts multiple rays to detect walls
   - Calculates safe position along movement path

2. **`slide_collision(from_pos, desired_pos, check_height)`**
   - Returns: `final_position`
   - Tries direct movement first
   - Falls back to X/Z-only movement if blocked
   - Implements sliding behavior

3. **`check_camera_collision(cam_pos, target_pos)`**
   - Returns: `safe_cam_pos`
   - Prevents camera from penetrating walls
   - Pulls camera forward if needed

## Usage in Update Loop

```python
# In on_update() function:
if mx or mz:
    # Calculate movement
    vx = right_x*mx + hfx*mz
    vz = right_z*mx + hfz*mz
    
    # Get current position
    x, y, z = player.getPosition()
    
    # Calculate desired position
    desired_pos = [x + vx*PLAYER_SPEED*dt, y, z + vz*PLAYER_SPEED*dt]
    
    # Apply collision detection with sliding
    final_pos = slide_collision([x,y,z], desired_pos, check_height=CAMERA_HEIGHT_FP)
    
    # Move player to safe position
    player.setPosition(final_pos)
```

## Troubleshooting

### Problem: Player still goes through walls
- Check that `USE_RAYCAST_COLLISION = True`
- Verify wall geometry has collision enabled
- Increase `COLLISION_BUFFER` and `COLLISION_RAYS`

### Problem: Screen shaking/jittering
- Make sure `CAMERA_SMOOTH_TP = True` in third-person
- Increase `CAMERA_DAMPING_TP`
- Check that `CAMERA_COLLISION_ENABLED = True`

### Problem: Player gets stuck in corners
- The sliding system should prevent this
- If it happens, increase `COLLISION_BUFFER` slightly
- Check that both X and Z sliding attempts are working

### Problem: Camera pops through walls
- Enable `CAMERA_COLLISION_ENABLED = True`
- The ray from player to camera should prevent this
- Increase buffer if still occurring

## Best Practices

1. **Always use raycast collision** (`USE_RAYCAST_COLLISION = True`)
2. **Keep COLLISION_BUFFER between 0.2-0.4** for best results
3. **Use 6-8 rays** for good performance/accuracy balance
4. **Enable camera collision** in third-person mode
5. **Test in tight corridors** and corners to verify sliding works
6. **Tune smoothing** for your desired camera feel

## Legacy Systems

The old grid-based collision (`PLAYER_COLLISION_ENABLED`) is kept for backward compatibility but should remain disabled. The raycast system is superior in every way.
