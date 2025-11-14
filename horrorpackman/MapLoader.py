import os
import viz
import vizshape

# Pac-Man maze parts (floor + layered walls). Update filenames to match your assets.
# These are relative to the existing `assets` directory.
PACMAP_PARTS = {
	'floor': 'PacMan_Floor.glb',      # floor mesh
	'walls': [                        # layered slices (cake segments)
		'PacMan_Wall_1.glb',
		'PacMan_Wall_2.glb',
		'PacMan_Wall_3.glb',
		'PacMan_Wall_4.glb'
	]
}

MAP_GROUP_NAME = 'pacman_root'

def _full_path(name):
	return os.path.join('assets', name)

def _safe_add_child(path):
	try:
		if os.path.exists(path):
			n = viz.addChild(path)
			print('[Map] Loaded', path)
			return n
		else:
			print('[Map] Missing asset ->', path)
	except Exception as e:
		print('[Map] Load error', path, e)
	return None

def _fallback_floor():
	f = vizshape.addPlane(size=[20,20], axis=vizshape.AXIS_Y)
	f.color(0.25,0.05,0.05)
	print('[Map] Fallback floor primitive created')
	return f

def _fallback_wall(i):
	h = 2.0
	w = vizshape.addBox([1.0,h,0.2])
	w.setPosition([i*1.2 - 2.4, h/2.0, 0])
	w.color(0.05 + i*0.02, 0.05, 0.05)
	print('[Map] Fallback wall primitive', i)
	return w

def _style_pacmap(floor, walls):
	for n in ([floor] + list(walls)):
		if not n:
			continue
		try:
			n.disable(viz.LIGHTING)
		except Exception:
			pass
	try:
		if floor:
			floor.color(1.0, 0.1, 0.1)
	except Exception:
		pass
	for i, n in enumerate(walls):
		try:
			if i % 2 == 0:
				n.color(0.00, 0.80, 1.00)
			else:
				n.color(0.02, 0.02, 0.02)
		except Exception:
			pass

def load_pacmap(parent=None, apply_style=True):
	"""Load the pacman maze parts (floor + layered walls).

	Returns (group, floor_node, wall_nodes_list)
	- parent: optional existing group to attach to.
	- apply_style: whether to recolor using _style_pacmap.

	Update PACMAP_PARTS at top if filenames differ.
	"""
	group = viz.addGroup() if parent is None else parent
	try:
		# Some Vizard versions expose different group APIs; guard against missing method
		group.name(MAP_GROUP_NAME)
	except Exception:
		try:
			group.setName(MAP_GROUP_NAME)
		except Exception:
			pass

	floor_path = _full_path(PACMAP_PARTS['floor']) if PACMAP_PARTS.get('floor') else None
	floor_node = _safe_add_child(floor_path) if floor_path else None
	if floor_node:
		floor_node.setParent(group)
	else:
		floor_node = _fallback_floor()
		floor_node.setParent(group)

	wall_nodes = []
	for i, wfile in enumerate(PACMAP_PARTS.get('walls', [])):
		path = _full_path(wfile)
		node = _safe_add_child(path)
		if not node:
			node = _fallback_wall(i)
		node.setParent(group)
		wall_nodes.append(node)

	if apply_style:
		_style_pacmap(floor_node, wall_nodes)

	return group, floor_node, wall_nodes

# Optional quick build helper used by main script (import and call early):
def build_and_attach_map():
	g, f, walls = load_pacmap(apply_style=True)
	print('[Map] Build complete. Parts:', 'floor=ok' if f else 'floor=missing', 'walls', len(walls))
	return g

# Usage in horrorpackman.py after arena floor/border creation:
# from MapLoader import build_and_attach_map
# pacmap_root = build_and_attach_map()