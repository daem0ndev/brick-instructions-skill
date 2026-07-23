# Mesh input: 3D model → build.json massing draft

Any triangle mesh (`.obj`, `.glb`, `.blend` via export) can seed a build with
real proportions instead of eyeballed ones. The pipeline uses BrickGPT's
`mesh2brick` converter for voxelization + brick placement, then this repo's
tools for everything else. Treat the result as a **massing draft**: correct
silhouette and proportions, but monochrome and all rectangular bricks. The
normal detail pass (colors, `trans-*` glass, shape/part system) is what makes
it read like a set.

## 1. Get mesh2brick running

```bash
git clone https://github.com/AvaLovelace1/BrickGPT.git
cd BrickGPT/src/mesh2brick
uv run mesh2brick input.obj out.txt --world_dim 40
```

`uv` installs deps on first run (open3d, networkx, gurobipy). Two gotchas:

- **Gurobi licensing.** The stability-analysis LP exceeds the bundled free
  license on anything bigger than toy meshes. The connectivity phase
  (networkx, solver-free) is what guarantees a single buildable component, and
  this repo's validator independently checks support. Patch around it:
  monkeypatch `BrickStructure.stability_scores` to return
  `numpy.zeros(len(self.bricks))` on `GurobiError` before calling the
  converter (run it as a small Python driver instead of the CLI).
- **`.blend` files** need a headless export first:
  `blender -b model.blend --python-expr "import bpy; bpy.ops.wm.obj_export(filepath='model.obj', export_triangulated_mesh=True)"`

## 2. Resolution

`--world_dim` bounds the longest axis in studs. 20 (their default) reads as an
icon; 40 reads as a real model (a 1.7M-triangle car became 345 bricks at 40).
Conversion is seconds either way. Expect an occasional stray floating 1x1 from
voxelization noise; `validate` catches it, just delete the brick.

## 3. Convert to build.json

```bash
python3 scripts/mesh2build.py out.txt draft.build.json --title "My Model"
python3 scripts/render_instructions.py validate draft.build.json
```

Mapping: `HxW (x,y,z)` → `size [H, W, 3]`, `pos [x, y, z*3]`. All bricks, one
brick-height per layer.

## 4. Detail pass

The draft is honest geometry and nothing else. From here use the standard
workflow: recolor regions (if the source mesh has materials, sample them —
see `examples/gen_challenger_color.py` for a worked approach using per-voxel
nearest-triangle lookup with an exterior-visibility flood fill), glaze the
glass regions with `trans-*`, swap wheels/slopes/tiles via the shape system,
and re-validate after every change.

Two traps the Challenger example hit, worth knowing before you sample
materials yourself: interior surfaces (seats, floorpan) outvote the painted
skin unless you count only exterior-visible voxels (flood-fill the outside
air; use 26-neighbor adjacency because sloped glass digitizes into diagonal
stair-steps), and window glass usually sits one voxel inboard of the hull, so
glazing is better applied geometrically (the belt between beltline and roof)
than by material vote.
