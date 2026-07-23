"""Worked reference: mesh material sampling for the Challenger example.

Paths are hardcoded to the original run (BrickGPT checkout + exported OBJ);
adapt them to your mesh. The reusable ideas are the exterior-visibility flood
fill, the 26-neighbor visible() check, and the per-brick vote with geometric
glazing. See references/mesh-input.md.
"""
import json
import sys
from collections import Counter, deque

import numpy as np
import open3d as o3d
from gurobipy import GurobiError
from scipy.spatial import cKDTree

from mesh2brick.data import brick_structure
from mesh2brick.mesh2brick import normalize_mesh
from mesh2brick.voxel2brick import voxel2brick

_orig = brick_structure.BrickStructure.stability_scores


def safe_stability(self):
    try:
        return _orig(self)
    except GurobiError:
        return np.zeros(len(self.bricks))


brick_structure.BrickStructure.stability_scores = safe_stability

OBJ = '/tmp/challenger_mat.obj'
WORLD = 40
GLASS = 'Material.005'
TIRE = 'Material.006'
PAINT = 'Material'
BODY_RED = '#8B1616'
COLOR_MAP = {
    TIRE: 'black',
    PAINT: BODY_RED,
    'Material.001': 'black', 'Material.002': 'black',
    'Material.003': 'black', 'Material.004': 'black',
    'Material.007': '#C8C8C8', 'Material.009': '#C8C8C8', 'Cam': '#C8C8C8',
}

# Per-face material names, in OBJ face order
face_mats, cur = [], None
for line in open(OBJ):
    if line.startswith('usemtl'):
        cur = line.split(None, 1)[1].strip()
    elif line.startswith('f '):
        face_mats.append(cur)

mesh = o3d.io.read_triangle_mesh(OBJ)
mesh = normalize_mesh(mesh, x_rotation=90)
tris = np.asarray(mesh.triangles)
verts = np.asarray(mesh.vertices)
assert len(tris) == len(face_mats)
tree = cKDTree(verts[tris].mean(axis=1))

voxel_size, grid_shape = 0, [128, 128, 128]
while max(grid_shape) > WORLD:
    voxel_size += 0.01
    vg = o3d.geometry.VoxelGrid.create_from_triangle_mesh(mesh, voxel_size)
    voxels = vg.get_voxels()
    min_bound = vg.get_min_bound()
    grid_shape = np.ceil((vg.get_max_bound() - min_bound) / voxel_size).astype(int)

voxel_array = np.zeros((WORLD,) * 3, dtype=np.uint8)
vox_mat = {}
for v in voxels:
    idx = tuple(np.floor(v.grid_index).astype(int))
    voxel_array[idx] = 1
    center = min_bound + (np.array(idx) + 0.5) * voxel_size
    _, ti = tree.query(center)
    vox_mat[idx] = face_mats[ti]

# Flood-fill exterior air from the grid boundary; visible = filled cell
# with an exterior-air 6-neighbor. Interior cavity voxels never qualify.
exterior = np.zeros_like(voxel_array, dtype=bool)
q = deque()
for x in range(WORLD):
    for y in range(WORLD):
        for z in range(WORLD):
            if (x in (0, WORLD - 1) or y in (0, WORLD - 1) or z in (0, WORLD - 1)) \
                    and not voxel_array[x, y, z] and not exterior[x, y, z]:
                exterior[x, y, z] = True
                q.append((x, y, z))
while q:
    x, y, z = q.popleft()
    for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
        nx, ny, nz = x + dx, y + dy, z + dz
        if 0 <= nx < WORLD and 0 <= ny < WORLD and 0 <= nz < WORLD \
                and not voxel_array[nx, ny, nz] and not exterior[nx, ny, nz]:
            exterior[nx, ny, nz] = True
            q.append((nx, ny, nz))

def visible(x, y, z):
    # 26-neighborhood: sloped surfaces (windshield) digitize as stair-steps
    # whose open air sits diagonally, so face-adjacency misses them.
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                if dx == dy == dz == 0:
                    continue
                nx, ny, nz = x + dx, y + dy, z + dz
                if not (0 <= nx < WORLD and 0 <= ny < WORLD and 0 <= nz < WORLD):
                    return True
                if exterior[nx, ny, nz]:
                    return True
    return False

bricks = voxel2brick(voxel_array, max_failures=10)

out = []
for b in bricks.bricks:
    votes = Counter()
    vis_count = 0
    has_glass = False
    for x in range(b.x, b.x + b.h):
        for y in range(b.y, b.y + b.w):
            m = vox_mat.get((x, y, b.z))
            if m == GLASS:
                has_glass = True
            if m is None or not visible(x, y, b.z):
                continue
            vis_count += 1
            if m == GLASS:
                continue  # glass handled geometrically below
            votes[m] += 1

    if vis_count == 0:
        color = '#1A1A1A'                      # fully hidden interior brick
    elif b.z in (8, 9) and 11 <= b.x + b.h / 2 <= 27:
        color = 'trans-black'                  # greenhouse belt, cabin x-range only
    elif b.z == 7 and has_glass:
        color = 'trans-black'                  # windshield / backlight step
    elif votes:
        color = COLOR_MAP.get(votes.most_common(1)[0][0], BODY_RED)
    else:
        color = BODY_RED if b.z >= 3 else '#1A1A1A'
    out.append({'size': [b.h, b.w, 3], 'pos': [b.x, b.y, b.z * 3], 'color': color})

out.sort(key=lambda r: (r['pos'][2], r['pos'][1], r['pos'][0]))
build = {'title': 'Dodge Challenger',
         'subtitle': 'Converted from Challenger.blend — mesh2brick massing, exterior material sampling',
         'author': 'Max', 'bricks': out}
json.dump(build, open('/tmp/challenger_color.build.json', 'w'), indent=1)
print(f'DONE {len(out)} bricks', file=sys.stderr)
print(Counter(x['color'] for x in out), file=sys.stderr)

# debug glass visibility
tot = vis = 0
for (x, y, z), m in vox_mat.items():
    if m == GLASS and z >= 7:
        tot += 1
        if visible(x, y, z):
            vis += 1
print(f'glass z>=7: total={tot} visible={vis}', file=sys.stderr)
gb = [(b.h, b.w, b.x, b.y, b.z) for b in bricks.bricks if b.z >= 7]
print(f'bricks z>=7: {len(gb)}', file=sys.stderr)
