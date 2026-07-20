# Brick Design Guide

Geometry constants, structural rules, decomposition methodology, and research background for the brick-instructions skill.

## Units & geometry

- Stud pitch: 8 mm → **1 stud = 1 x/y unit** in build.json.
- Plate height: 3.2 mm → **z is measured in plates**; brick = 3 plates (9.6 mm), so a brick is 1.2× as tall as a stud is wide.
- Stud: 4.8 mm diameter (r = 0.3 stud units), 1.8 mm tall (0.5625 plates).
- Renderer projection (isometric-ish, affine): `screen_x = (x − y)·√3/2`, `screen_y = (x + y)/2 − z·0.4`. Under this map a circle on a top face becomes a screen-aligned ellipse with semi-axes 1.22r (horizontal) and 0.71r (vertical) — that's why studs are drawn as un-rotated ellipses.
- Painter's algorithm sort: draw by ascending z, then ascending (x + y). Correct for layer-oriented builds; pathological tall-front/behind-high-back overlaps are rare in practice.

## Part catalog (extend in BOTH renderers' LDRAW_PART maps and here)

Bricks (h=3): 1x1 3005, 1x2 3004, 1x3 3622, 1x4 3010, 1x6 3009, 1x8 3008, 2x2 3003, 2x3 3002, 2x4 3001, 2x6 2456, 2x8 3007.
Plates (h=1): 1x1 3024, 1x2 3023, 1x3 3623, 1x4 3710, 1x6 3666, 1x8 3460, 2x2 3022, 2x3 3021, 2x4 3020, 2x6 3795, 2x8 3034, 4x4 3031, 4x6 3032, 4x8 3035, 6x8 3036.

Colors (name → hex, LDraw code): red #C91A09/4, blue #0055BF/1, yellow #F2CD37/14, green #237841/2, white #F4F4F4/15, black #1B2A34/0, tan #E4CD9E/19, light-gray #A0A5A9/71, dark-gray #6C6E68/72, orange #FE8A18/25, brown #583927/6, lime #BBE90B/27, dark-blue #0A3463/272, dark-red #720E0F/320, pink #FC97AC/13, purple #81007B/5, sand-green #A0BCAC/378, azure #36AEBF/322.

## Structural design rules (distilled from BrickGPT + AFOL practice)

1. **Bottom-up, layer by layer.** Design z=0 first; every brick must overlap ≥1 stud in plan with something at the level directly below (or sit on the ground).
2. **Interlock like brickwork.** Stagger vertical seams between layers; a seam running unbroken through 3+ layers is a structural crack. Bridge seams with the layer above.
3. **Largest bricks first.** Fewer, bigger parts = stronger, cheaper, simpler instructions. Fill structure with 2x4/2x6, detail with small parts.
4. **Cantilever limit.** Overhangs ≤2 studs without support; longer overhangs need a column or counterweight above the fulcrum.
5. **Tower proportions.** Freestanding height should stay under ~3× the smallest footprint dimension, or widen the base.
6. **Rollback discipline** (BrickGPT's key inference trick): after every design change run `validate`; if it introduces errors, revert to the last valid state and take a different approach — never accumulate broken state.
7. **Recognizability at stud resolution:** silhouette first, then color blocking, then 2–3 signature details. Don't chase curves; suggest them with steps of plates.

## Scale Planning (do this before designing anything)

For a real-world subject, decide the target scale *before* laying a single brick — a naive "make it small enough to build quickly" default routinely undersells the subject and flattens depth out of the model.

### Ask the user to pick a scale tier — every time the subject is non-trivial

Present this as a multiple-choice question (locally: an option prompt; in ChatGPT: a lettered list) before designing. Include the estimated piece count for THIS subject at each tier so the choice is informed:

| Tier | Piece count | What it is | Best for |
|---|---|---|---|
| **Desk Mini** | ~50–200 | Icon-level microscale; silhouette + color blocking only | Quick gifts, desk toys, first drafts |
| **Display** | ~300–900 | Small showcase; real proportions, coarse detail | Shelf models, single buildings |
| **Showcase** | ~1,500–5,000 | Large showcase; volumetric massing, per-story detail, landscaping | Landmark architecture, sprawling sites — **recommend this for real buildings/complexes** |
| **True minifig** | often 10,000+ | 1 stud ≈ 1 ft in plan, ~8–10 bricks per story | Serious MOC projects; quote the estimate honestly and warn about size |

Estimating for the question: from the subject's real dimensions (or an estimate from the reference photo — say which), compute plan footprint in studs at each tier, multiply by height, and assume roughly 1 brick per 8–12 studs of solid volume (or per 4–6 studs of shell surface). Round to the nearest order of magnitude — the user is choosing a tier, not auditing arithmetic.

1. **Minifig scale (~1:38 to 1:42, the AFOL default).** Rule of thumb: **1 stud in plan ≈ 30 cm (1 ft)**; a minifig-scale story is **~8–10 bricks (24–30 plates) tall**. A real 36-story tower is ~300 bricks tall at this scale — usually impractical, but it's the reference point you scale down FROM, stated openly, not hidden.
2. **Showcase/microscale (what official LEGO Architecture skyline sets use).** Preserve the real subject's ratios (height:width:depth, relative story counts between structures) at a total size that's practical; derive every dimension from those ratios so the model reads correctly at a glance.

**Always state the reasoning, not just the result.** Compute the true minifig-scale size and the practical tier sizes, present them, and let the user choose — never silently ship a token-conserving toy-sized model and call it done.

**Depth is not optional for hero structures.** A 1-stud-deep wall of plates standing up in a contour is a *silhouette*, not a volume — it looks like a cardboard cutout from any angle but straight-on. Reserve flat 1-stud construction for genuinely thin real elements (a sign, a fin, a canopy edge); every primary/hero structure should have real thickness — as a floor, footprint depth ≥3-4 studs, tapering with the silhouette rather than staying constant, so features like a waist or neck read as changes in both width *and* depth. `validate` flags this automatically: any section taller than 15 plates built entirely from 1-stud-deep bricks gets a "flat structure" warning.

### Construction + tooling at Showcase/minifig tiers (1,000+ pieces)

- **Generate `build.json` programmatically** (a short script emitting the JSON), never by hand — see `examples/` for the generator pattern: `fill()`-style helpers tiling footprints, silhouette band tables for curved masses, repeated sub-units stamped at offsets.
- **Solid-fill stories** (every tile has a tile directly beneath it) unless you're prepared to design real internal support columns — hollow shells with unsupported interior floor tiles fail the floating-brick check, and rightly so.
- **Small parts, not giant slabs.** Tiling with 2x2/1x2-class parts is both more realistic (that's what real MOCs are made of) and what makes the count honest instead of 4x8-slab token-golf.
- The renderers handle this scale by design: step geometry is emitted once (SVG `<symbol>`/`<use>` in HTML, Form XObjects in the native PDF) and referenced thereafter, so output size is linear in bricks, and auto-stepping widens to 16 pieces/step above 300 bricks and 24 above 1,000. A 1,900-piece build renders to a ~4 MB HTML and ~6 MB, ~30-page PDF in well under a second.
- **PDF for large builds must come from the native renderer** (`python3 scripts/render_instructions.py pdf`): headless-Chrome print-to-pdf does not preserve SVG `<use>` sharing (it flattens each step), which turns a 4 MB HTML into an 80 MB PDF at this scale. The HTML itself stays fast in an actual browser.

## Large-Scale Decomposition (sprawling builds, campuses, skylines)

For anything beyond a single object — a resort, a campus, a skyline, a large vehicle with sub-assemblies — **decompose into sections before writing a single brick**. Both renderers support this natively via the optional `section` field on each brick and the top-level `sections` array (id/title/note) that names and orders the chapters. A build with more than ~120 bricks and no sections trips a validator warning nudging you to decompose.

### 1. Identify sections along functional/structural seams, not arbitrary chunks

Good section boundaries are places a real build would naturally pause: a shared foundation, a distinct tower or wing, a connecting bridge, a landscaping pass. Bad section boundaries are "the first 50 bricks, then the next 50" — that fragments a single wall into two chapters for no reason. Ask "what is this, structurally?" and let the answer name the sections.

### 2. Order sections by structural dependency, then by build logic

1. **Foundation / shared ground infrastructure first** — a podium, baseplate, or site grade every other section will sit on. Building this first means later sections just need to key off a known top surface (a shared z-level), not off each other.
2. **Primary structures next**, ordered by whichever has the most dependents, or arbitrarily among peers (e.g. two independent wings on the same podium — build either first, doesn't matter, they don't touch).
3. **Connecting structures** (bridges, walkways, shared lobbies) after the pieces they connect exist.
4. **Decorative / peripheral / landscaping last** (villas, pools, signage, trees) — these often don't even touch the primary structures and can be built any time, but placing them last keeps the booklet's narrative focused: main structure first, dressing after.

`ensureSteps` auto-steps section by section in the order they first appear (in the `sections` array if present, else first occurrence in `bricks`), and never mixes two sections into a single step — so the section order you declare *is* the chapter order in the booklet.

### 3. Design each section's interface, not its neighbors

A section should generally only need to know about **the shared ground/podium level**, not about the internals of other sections. If Section B needs to sit on top of Section A, give Section A a flat, fully-specified top surface at a known z, and start Section B there — don't reach into Section A's brick list to figure out where things are. This keeps sections independently designable (and independently regenerable) without cross-section coordination bugs. Landscaping/peripheral sections often don't need to touch anything else at all — they can sit on their own ground-level (z=0) plates entirely separately; the validator's connectivity check treats every z=0 brick as inherently grounded, so disconnected-but-grounded sections are valid.

### 4. Keep each section's own step count sane

Even inside one section, keep the same discipline as a normal build: ≤8 new pieces per step, bottom-up. A section becoming its own chapter doesn't excuse it from being a well-paced mini-instruction-booklet in its own right — the reader experiences it as "now we build the west wing," not as one undifferentiated pile.

### 5. What the renderers do with this automatically

- **Chapters:** each booklet gets a full-width divider ("Section 2 — Guitar Tower", its note, piece count, step range) at the first step of every section, plus a table of contents on the cover page.
- **Ghosting:** every step's render shows the *current* section in full color/detail and every other section as a flattened, desaturated gray silhouette (no stud detail) — so the reader always sees where the active chapter attaches to the rest of the structure without the rest of the model competing for attention.
- **Three render tiers, not two.** Ghosting alone only controls cross-section cost — it does nothing for a single large section's own step-by-step growth, and a large section redrawing full stud detail on every already-placed brick at every subsequent step is O(steps × bricks): a 190-brick single section did this and produced a 29 MB PDF before this fix. Both renderers now use three tiers per step: **new** (the brick(s) just added — full color, full stud detail, highlighted border), **built** (already-placed in the *active* section — full color, flattened, no studs), **ghost** (other sections — desaturated gray, flattened, no studs). This keeps the expensive per-stud geometry bounded by "how many bricks are new this step" (≤8) instead of "how many bricks exist so far," while every cumulative brick still renders once in full detail (in the cover/hero render and in its own step).
- **Validation:** in addition to the usual collision/connectivity/buildability checks, `validate` warns if a section's steps get interrupted by another section (steps should be contiguous per chapter), nudges any 120+ brick build with no sections to decompose, and flags any section over 15 plates tall built entirely from 1-stud-deep bricks as a flat structure (see Scale Planning above).

### Worked example

`templates/example-hotel.build.json` is a 192-brick, four-section model scaled to a real reference subject (a 450 ft / ~36-story tower next to a real 7-story low-rise wing) — a shared podium, a hotel wing, a volumetric guitar-silhouette tower with real depth (not a flat wall), and a lagoon/villas landscaping pass. It exercises every mechanic above: shared foundation, independent peer structures, a section that doesn't touch anything else, full chapter/TOC/ghosting rendering, and a footprint/depth that varies with the silhouette rather than staying a constant 1 stud. Use it as a template for scaling this pattern up further.

## Instruction booklet UX (what makes it feel like a real LEGO manual)

- ≤8 new pieces per step; one "idea" per step (a wall course, a roof layer).
- Parts callout box on every step (the dashed box with piece thumbnails + counts).
- One consistent camera for all steps (the renderer enforces this — shared viewBox).
- `note` fields for tricky placements (offsets, overhangs, symmetry).
- Cover page: hero render, piece count, step count, footprint, parts list, and (for multi-section builds) a table of contents.

## Research background (2026-07, verified)

- **BrickGPT** (formerly LegoGPT) — CMU, ICCV 2025 **Best Paper (Marr Prize)**. First approach generating physically stable brick assemblies from text. Fine-tuned Llama-3.2-1B on **StableText2Brick** (~47k stable structures, captions by GPT-4o); autoregressive next-brick prediction in text format `hxw (x,y,z)` (one brick per line — maps 1:1 to our build.json entries); **validity check + physics-aware rollback** during inference prunes colliding/unstable bricks; optional Gurobi-based force-model stability analysis (fallback: connectivity heuristic — which is what our validator implements). Outputs .txt, .ldr, .png. MIT license.
  - Paper: arxiv.org/abs/2505.05469 · Code: github.com/AvaLovelace1/BrickGPT · Dataset: huggingface.co/datasets/AvaLovelace/StableText2Brick
  - Submodules worth knowing: **mesh2brick** (3D mesh → brick structure — use for supplied meshes/CAD), **texture** (UV/per-brick coloring via FlashTex).
- **Brickit** (brickit.app) — mobile app that CV-scans a pile of loose bricks, identifies pieces, and suggests builds constrained to that inventory with step-by-step instructions. The inspiration for this skill's `--inventory` mode.
- **"Brickbuilder AI"** — no distinct product found (2026-07); the concept space is covered by the two above.
- **LDraw ecosystem** — open standard for brick models (LDU units: 1 stud = 20 LDU wide, plate = 8 LDU tall; −Y is up). Our `.ldr` export opens in BrickLink Studio, LPub3D, LeoCAD — use those for photoreal renders or when real part geometry matters (slopes, SNOT, minifigs).

## Detail Pass (making builds read as genuine sets)

After massing and sections are validated, run an explicit detail pass using the specialized part vocabulary — see `references/part-registry.md` for the full shape system, BrickLink category map (Window/Glass cat 81, Plant cats 25/95, Slopes, Tiles, Panels…), and the five detail patterns: curtain walls (trans-* glass over structural cores), tile cornices, cheese/curved-slope contours at silhouette steps, subject-specific functional details (e.g. inset strings + fretboard on a guitar-shaped tower), and landscaping (palms from round trunks + foliage canopies, hedges, trans-tile water). Structural rule of thumb for facades: glazing skins bond only vertically, so tie them into the mass with 2-deep bond courses at every width/depth-expansion shoulder — the floating-brick check enforces this.
