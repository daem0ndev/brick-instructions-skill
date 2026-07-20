# brick-instructions

**Turn any subject — from a rubber duck to a 1,900-piece resort complex — into LEGO®-style, step-by-step building instructions**, rendered as a polished HTML booklet or PDF from a single canonical `build.json`. Designed to be driven by an AI assistant (ChatGPT Work, Claude, or any agent with a Python or Bun sandbox), with validation that keeps the AI honest: collisions, floating bricks, bad build order, flat "cardboard cutout" structures, and piece-inventory shortfalls are all caught mechanically.

<p align="center"><em>build.json → validate → HTML / PDF / LDraw — iterate by editing JSON, never by redrawing.</em></p>

## Quick start for ChatGPT Work users (incl. mobile)

The renderer's Python implementation is pure stdlib — no pip, no network, no browser — exactly matching ChatGPT's code-interpreter sandbox, and its PDF output uses Form-XObject reuse so even thousand-piece builds stay in single-digit MB.

1. Create a **Project** (or custom GPT) in ChatGPT Work.
2. Upload as project knowledge:
   - `scripts/render_instructions.py`
   - `references/brick-design-guide.md`
   - `templates/example-duck.build.json`, `templates/example-hotel.build.json`
   - `examples/gen_rockwater_grand.py`
3. Enable **Code Interpreter**, then paste the instructions block from [`references/chatgpt-work-setup.md`](references/chatgpt-work-setup.md) into the Project instructions.
4. Ask for a build ("make me the Sydney Opera House"). The assistant will ask which **scale tier** you want — Desk Mini (~50–200 pieces), Display (~300–900), Showcase (~1,500–5,000), or true minifig scale — with piece estimates computed from the subject's real dimensions, then design, validate, and hand you a PDF.

On mobile, PDFs preview inline in the ChatGPT app; iterate by replying ("make the tower taller") — the assistant edits the JSON and re-renders.

## Local use (Bun or Python)

```bash
# validate (collisions, floating bricks, build order, flat structures, inventory)
bun scripts/render-instructions.ts validate build.json [--inventory inv.json]
python3 scripts/render_instructions.py validate build.json

# HTML booklet (cover, hero render, parts list, TOC, chaptered steps)
bun scripts/render-instructions.ts render build.json -o instructions.html

# PDF — native vector writer, zero dependencies; REQUIRED for large builds
python3 scripts/render_instructions.py pdf build.json -o instructions.pdf

# LDraw export (opens in BrickLink Studio / LPub3D / LeoCAD)
python3 scripts/render_instructions.py ldr build.json
```

> **Large-build note:** don't print the HTML to PDF via headless Chrome for 300+ piece builds — Chrome flattens the SVG `<use>` reuse and the PDF balloons (82 MB where the native writer produces 5.6 MB). Use the Python `pdf` subcommand.

## build.json schema

```jsonc
{
  "title": "Classic Duck",
  "subtitle": "optional",
  "colors": { "custom-name": "#AABBCC" },        // optional palette overrides
  "sections": [                                   // optional chapters for large builds
    { "id": "podium", "title": "Podium", "note": "Ground deck." }
  ],
  "bricks": [
    { "size": [2, 4, 3],      // [width_x studs, depth_y studs, height PLATES] (brick=3, plate=1)
      "pos": [0, 0, 0],       // [x, y, z] — z in plate-levels, 0 = ground
      "rot": 0,               // 90 swaps width/depth
      "color": "yellow",      // named palette or #hex
      "section": "podium",    // optional chapter id
      "step": 1,              // optional; auto-assigned per layer/section if omitted
      "note": "optional tip shown under the step" }
  ]
}
```

## What makes it hold up at scale

- **Sections as chapters** — tag bricks with `section`, get a table of contents, chapter dividers, and per-chapter step runs; everything outside the active chapter renders as a ghosted gray silhouette so each step stays readable.
- **Linear output size** — each step's geometry is emitted once (SVG `<symbol>`/`<use>` in HTML, PDF Form XObjects in the native PDF) and referenced by every later step. A 1,909-piece model renders in <1 s to a ~4 MB HTML / ~6 MB 29-page PDF.
- **Adaptive pacing** — 8 pieces per step for small builds, 16 above 300, 24 above 1,000, matching how real LEGO booklets pace bigger sets.
- **Scale discipline** — the design guide requires computing true minifig-scale size from the subject's real dimensions and asking the user to choose a tier, instead of silently shipping a toy-sized model; a validator warning flags tall structures built as 1-stud-deep flat walls.
- **Physical honesty** — validation implements the connectivity heuristic from CMU's [BrickGPT](https://github.com/AvaLovelace1/BrickGPT) (ICCV 2025 Best Paper): every brick must trace support to the ground, steps must be buildable in order, and inventory constraints are hard errors.

## Repo layout

| Path | What |
|---|---|
| `scripts/render-instructions.ts` | Bun/TypeScript renderer (HTML, validate, LDraw) |
| `scripts/render_instructions.py` | Pure-stdlib Python port (adds native PDF; ChatGPT-sandbox-ready) |
| `references/brick-design-guide.md` | Geometry, structural rules, scale planning, large-scale decomposition |
| `references/chatgpt-work-setup.md` | ChatGPT Work deployment guide + paste-in instructions block |
| `templates/` | Small worked examples (duck; 192-piece multi-section hotel) + inventory format |
| `examples/` | 1,909-piece "Rockwater Resort" grand-scale build: generator script, build.json, finished PDF |

## Credits & prior art

Validation approach inspired by **BrickGPT** (CMU, MIT-licensed; formerly LegoGPT); inventory-constrained mode inspired by **Brickit**. LDraw part numbering per the [LDraw](https://www.ldraw.org) open standard. LEGO® is a trademark of the LEGO Group, which does not sponsor, authorize, or endorse this project.

MIT © Asif Rahman
