---
name: brick-instructions
description: Design LEGO-style brick builds and generate validated step-by-step instruction booklets (HTML/PDF/LDraw). Use when the user asks for LEGO instructions, brick versions of objects/buildings/landmarks, buildable models from photos or descriptions, or "what can I build with these pieces". Scales from desk toys to thousands-of-pieces showcase builds with real BrickLink parts, glass, foliage, and chaptered sections.
license: MIT
metadata:
  author: daem0ndev
  repo: https://github.com/daem0ndev/brick-instructions-skill
---

# Brick Build Instructions

Generate LEGO-style, step-by-step building instructions and renderings from flexible inputs: text descriptions, reference photos/diagrams, real-world buildings — optionally constrained by a piece inventory. This file is the agent-facing skill definition; everything it references lives in this repo (`scripts/`, `references/`, `assets/`, `examples/`).

**Core principle: `build.json` is the single source of truth.** Every output (HTML booklet, PDF, LDraw) derives from it deterministically. Iterate by editing the JSON — or, for large builds, the generator script that emits it — never the outputs.

## Tools

- `scripts/render_instructions.py` — pure-stdlib Python 3: `validate`, `render` (HTML), `pdf` (native vector PDF), `ldr`. Runs anywhere, including the ChatGPT code-interpreter sandbox (mobile included).
- `scripts/render-instructions.ts` — Bun/TypeScript equivalent: `validate`, `render`, `ldr` (PDF via the Python renderer).
- `scripts/mesh2build.py` — converts BrickGPT `mesh2brick` output into a build.json massing draft when the input is a 3D model instead of photos/text. Full recipe (setup, Gurobi patch, material sampling): `references/mesh-input.md`.
- **PDF rule:** always produce PDFs with the Python renderer. Its Form-XObject reuse keeps thousand-piece PDFs in single-digit MB; printing the HTML via headless Chrome flattens SVG reuse and balloons ~15× on large builds.

## Workflow

1. **Intake.** Subject, reference imagery, color palette, inventory constraints. Study reference photos carefully for the *actual* massing (e.g. is that tower a shape's silhouette extruded as a slab, or a stacked solid?) before designing anything.
2. **Scale tier — ask the user (multiple-choice) for any non-trivial subject**, with piece estimates computed from the subject's real or photo-estimated dimensions (state which):
   - **A) Desk Mini** (~50–200 pieces) — icon-level silhouette
   - **B) Display** (~300–900) — real proportions, coarse detail
   - **C) Showcase** (~1,500–5,000) — volumetric massing, per-story detail, landscaping; recommend for real buildings/complexes
   - **D) True minifig** (1 stud ≈ 1 ft, ~8–10 bricks/story; often 10,000+ — warn)
   Never silently default to a small model for a large subject. Estimation rules: `references/brick-design-guide.md` §Scale Planning.
3. **Decompose into `sections`** for anything large/sprawling (foundation → primary structures → connecting → landscaping). Chapters, TOC, and ghosted-context step rendering come free. Guide §Large-Scale Decomposition.
4. **Design bottom-up** on the stud grid per the guide's structural rules (stagger seams, every brick overlaps support, overhangs ≤2 studs, solid-fill stories at scale). At Showcase+ tiers, generate `build.json` programmatically — see `examples/gen_rockwater_true_shape.py` for the full pattern: fill helpers, cosine-interpolated silhouette tables, stamped sub-units, bond courses tying facade skins into the mass, column back-fills.
5. **Detail pass** — what separates a massing study from something that reads like a genuine set. Use the shape system (`shape`: `tile`, `slope`, `curved`, `cheese`, `round`, `panel`, `window`, `foliage`; default `box`), `trans-*` colors (render as glass), and the `part` field to reference any exact BrickLink part number. Patterns and the BrickLink category map (Window/Glass 81, Plant 25, Trees 95, Curved Slopes 438, Fences 13): `references/part-registry.md`. Never invent part numbers.
6. **Camera orientation:** the isometric camera shows the **+y and +x faces**. Detailed skins (glazing, banding, strings, fretboards) go on the y_max row / x_max column — a "front" at y_min is invisible in every render.
7. **Validate:** `python3 scripts/render_instructions.py validate build.json [--inventory inv.json]`. Fix every ERROR (collisions, floating bricks, order, inventory); treat warnings (flat structures, unsectioned large builds, interleaved sections) as design smells. BrickGPT-style rollback: a change that breaks validation gets reverted, not accumulated.
8. **Render and verify visually** (headless screenshot or PDF page inspection — never ship on file-existence alone). Compare against the reference imagery and iterate.
9. **Interop:** `… ldr build.json` exports LDraw for BrickLink Studio / LPub3D / LeoCAD.

## build.json schema (summary)

```jsonc
{ "title": str, "subtitle"?: str, "colors"?: {name: "#hex"},
  "sections"?: [{"id","title","note"?}],
  "bricks": [{ "size": [w_studs, d_studs, h_plates],   // brick=3 plates, plate=1
               "pos": [x, y, z_plates],                 // z=0 ground
               "rot"?: 0|90,                            // swaps w/d + slope direction
               "color": str,                            // named, #hex, or trans-*
               "shape"?: "box|tile|slope|curved|cheese|round|panel|window|foliage",
               "part"?: "BrickLink part number override",
               "section"?: str, "step"?: int, "note"?: str }] }
```

Steps auto-assign per section, adaptively: ≤8 pieces/step small, 16 above 300 bricks, 24 above 1,000. Inventory format (`--inventory`): `[{"size":"2x4","kind":"brick"|"plate","color":str,"qty":int}]`; shortfalls are hard errors.

## ChatGPT deployment

`references/chatgpt-work-setup.md` is the end-user guide: upload the Python renderer + references into a ChatGPT Project, paste the provided instructions block (it encodes this whole workflow), and PDFs come back inline-previewable on mobile. The `START-HERE.md` in release ZIPs is the non-technical version.

## Quality bar

- Zero validation errors; warnings justified or fixed.
- Scale honest to the subject (tier chosen by the user, minifig-scale math shown).
- Hero structures volumetric and faithful to the real massing; facade skins on camera-visible faces, tied in with bond courses at expansion shoulders.
- Detail pass applied: glazing, cornices, contours, at least one subject-signature detail, landscaping where the site has any.
- Booklet reads like a real set manual: consistent camera, parts callouts, chapters with TOC, notes on tricky placements.
