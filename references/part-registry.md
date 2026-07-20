# Part Registry — using the real LEGO part universe

The renderers draw nine geometry archetypes (`shape` field); the part tables map common sizes of each to real BrickLink/LDraw part numbers. **Any** real part beyond the built-in tables is usable: pick the closest `shape` for rendering and set `part` to the exact BrickLink number — the BOM and `.ldr` export then reference the genuine part while the booklet renders the archetype.

```jsonc
{ "size": [1,2,6], "pos": [4,0,1], "color": "trans-clear", "shape": "window", "part": "60592" }
```

## Browsing the BrickLink catalog

BrickLink's part catalog is the authoritative registry: `https://www.bricklink.com/catalogList.asp?catType=P&catString=<category>`. Categories most useful per build type:

| catString | Category | Use for |
|---|---|---|
| **81** | **Window, Glass & Shutter** | **curtain walls, glazing, skylights (`window`, `panel` + trans-* colors)** |
| **25** | **Plant** | **foliage, leaves, flowers, bushes (`foliage`)** |
| **95** | **Plant, Tree** | **whole trees, palm tops/trunks (`foliage` + `round` trunks)** |
| **438** | **Slope, Curved** | **smooth contours, bouts, aero shapes (`curved`)** |
| **13** | **Fence** | **railings, balustrades, lattices (render `panel`, set `part`)** |

(The bolded categories above are verified anchors. For anything else — plain bricks/plates, slopes, tiles, panels, round bricks, arches — search the catalog by part name or browse from `bricklink.com/catalogTree.asp?itemType=P`; verify the catString from the page itself rather than assuming.)

When a build calls for something not in the built-in tables (a lattice fence, a specific window frame, a palm top), browse the category, pick the real part, and use `shape` + `part`. Never invent part numbers — if unsure, use a built-in mapping or leave `part` unset (the `.ldr` export will flag it).

## Built-in part tables (shape:WxD-Hplates → part)

**Bricks/plates (`box`)**: 1x1–2x8 bricks (3005, 3004, 3622, 3010, 3009, 3008, 3003, 3002, 3001, 2456, 3007); 1x1–6x8 plates (3024, 3023, 3623, 3710, 3666, 3460, 3022, 3021, 3020, 3795, 3034, 3031, 3032, 3035, 3036).
**Tiles**: 1x1 3070b · 1x2 3069b · 1x3 63864 · 1x4 2431 · 1x6 6636 · 1x8 4162 · 2x2 3068b · 2x4 87079.
**Slopes 45°**: 1x2 3040 · 2x2 3039 · 2x4 3037; low slope 1x2x2⁄3 85984.
**Cheese slope**: 1x1x2⁄3 54200.
**Curved slopes**: 1x2 11477 · 1x4 (double) 93273 · 2x2 15068.
**Round**: 1x1 brick 3062b · 1x1 plate 4073.
**Panels**: 1x2x1 4865b · 1x2x2 87552 · 1x4x3 60581.
**Windows**: 1x2x2 60592 · 1x4x3 60594 (cat 81; combine with trans-* colors).
**Foliage**: leaves 4x3 2423 · leaves 6x5 2417 · bamboo 30176 (cats 25/95).

## Colors

Opaque: red 4 · blue 1 · yellow 14 · green 2 · white 15 · black 0 · tan 19 · light-gray 71 · dark-gray 72 · orange 25 · brown 6 · lime 27 · dark-blue 272 · dark-red 320 · pink 13 · purple 5 · sand-green 378 · azure 322 · dark-green 288 · reddish-brown 70.
Transparent (render as glass, 55% opacity): trans-clear 47 · trans-light-blue 43 · trans-dark-blue 33 · trans-black 40 · trans-red 36 · trans-yellow 46 · trans-green 34 · trans-neon-orange 57.

## Shape rendering + physics notes

- All shapes occupy their full bounding box for collision/support (conservative).
- `slope`/`curved`/`cheese` descend toward +y (viewer-left); `rot: 90` descends toward +x. Place them on camera-facing edges.
- `panel`/`window` render as a thin wall at the −y edge of their footprint.
- `foliage` renders an organic canopy blob; stack on `round` trunks for trees (palm = 3× round 1x1 brick + 2x2 foliage).
- Front-face skins (glazing rows) only bond vertically — at width/depth-expansion courses, tie the skin into the mass with 2-deep "bond" pieces or the floating-brick check will fail (correctly). See the worked generator in `examples/`.

## Detail-pass patterns (what makes builds read as genuine sets)

1. **Curtain wall**: replace the outermost visible-face row of each story with trans-* glass pieces over a structural core; alternate spandrel rows for banding.
2. **Cornice**: tile row (studless) along roof edges.
3. **Texture accents**: cheese slopes at silhouette steps; curved slopes on shoulders/bouts.
4. **Functional details**: model what the subject *does* — this repo's Guitar Hotel gets inset trans-clear round-brick strings, a black fretboard with light-gray fret tiles, and round tuner pegs.
5. **Landscaping**: palms (round trunks + foliage), hedge rows (foliage), water (azure base + trans-clear tile surface), pathways (tan tiles/plates).
