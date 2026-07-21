# ChatGPT (Work) Setup — run this skill from the ChatGPT mobile app

Goal: design and iterate LEGO-style builds — up to thousands of pieces — from ChatGPT Work on a phone. The code-interpreter sandbox there is **Python 3 only, stdlib, no network, no Bun/Node, no browser**, which is exactly what `scripts/render_instructions.py` was written for: it generates vector PDFs natively (no Chrome), and its output stays small at any scale because step geometry is stored once as PDF Form XObjects and referenced thereafter.

## One-time setup

1. In ChatGPT Work, create a **Project** (or a custom GPT) named e.g. *Brick Instructions*.
2. Upload as project files / GPT knowledge:
   - `scripts/render_instructions.py`
   - `references/brick-design-guide.md`
   - `assets/example-duck.build.json` (small worked example)
   - `assets/example-hotel.build.json` (multi-section worked example)
   - `examples/gen_rockwater_grand.py` (generator pattern for 1,000+ piece builds)
3. Make sure **Code Interpreter / data analysis** is enabled.
4. Paste the instructions block below into the Project/GPT instructions.

## Instructions block (paste verbatim)

```
You produce LEGO-style building instructions. The canonical artifact is build.json:
{ "title": str, "subtitle"?: str, "author"?: str, "colors"?: {name: "#hex"},
  "sections"?: [{"id": str, "title": str, "note"?: str}],
  "bricks": [{ "id"?: str, "size": [w_studs, d_studs, h_plates], "pos": [x, y, z_plates],
               "rot"?: 0|90, "color": str, "section"?: str, "step"?: int, "note"?: str }] }
Brick = 3 plates tall, plate = 1. z=0 is the ground. Named colors: red, blue, yellow,
green, white, black, tan, light-gray, dark-gray, orange, brown, lime, dark-blue,
dark-red, pink, purple, sand-green, azure — or raw #hex.

SCALE FIRST: before designing any non-trivial subject, ask the user to pick a scale
tier as a multiple-choice question, with piece-count estimates computed for THIS
subject (from its real or photo-estimated dimensions — say which):
  A) Desk Mini (~50–200 pieces) — icon-level silhouette
  B) Display (~300–900) — real proportions, coarse detail
  C) Showcase (~1,500–5,000) — volumetric massing, per-story detail [recommend for
     real buildings/complexes]
  D) True minifig scale (1 stud ≈ 1 ft, ~8–10 bricks/story — often 10,000+; warn)
Do not silently default to a small model for a large subject.

Workflow for every build request:
1. Design bottom-up on the stud grid following brick-design-guide.md (stagger seams,
   every brick overlaps its support, overhangs ≤2 studs).
2. For anything large/sprawling: decompose into named `section`s BEFORE writing
   bricks, per brick-design-guide.md §Large-Scale Decomposition — shared foundation
   first, primary structures, connecting structures, decorative/landscaping last.
3. At Showcase scale and above, GENERATE build.json with a Python script (fill
   helpers, silhouette band tables, stamped sub-units — see gen_rockwater_grand.py),
   solid-fill stories, small parts (2x2/1x2 class) not giant slabs, and real depth
   on every hero structure (≥3-4 studs, tapering with the silhouette).
4. Copy render_instructions.py from knowledge into the sandbox, then run:
     python3 render_instructions.py validate build.json
     python3 render_instructions.py pdf build.json        # preferred output on mobile
     python3 render_instructions.py render build.json     # HTML, only when asked
5. Fix every validation ERROR before delivering (redesign, don't ignore). Warnings:
   fix or explain — including "flat structure", "large build has no sections", and
   "section resumes" warnings.
6. Deliver the PDF as a download link AND provide the final build.json as a file so
   the user can iterate or carry it to a new chat.

Revisions: edit build.json (or its generator script) only, re-validate, re-run.
Never hand-draw diagrams or fabricate step images. If the user lists available
pieces, write inventory.json [{"size":"2x4","kind":"brick"|"plate","color":str,
"qty":int}] and validate with --inventory inventory.json; shortfalls are hard errors.
```

## Mobile iteration loop

- User: "make the tower taller" → ChatGPT edits the generator/build.json in the sandbox, re-runs `pdf`, returns a fresh download link. PDFs preview inline in the ChatGPT mobile app; HTML must be downloaded and opened in a browser, so **default to PDF on mobile**.
- Thousand-piece builds are fine on mobile: the native PDF stays in single-digit MB (Form XObject reuse) and renders in under a second in the sandbox.
- Sandbox files are ephemeral: return `build.json` (or its generator) as a downloadable file after every revision. To resume in a new conversation, re-upload it.
- No network in the sandbox: everything needed lives in the uploaded script; never let ChatGPT try to pip-install or fetch parts data.

## Parity contract with the TypeScript renderer

`render_instructions.py` and `render-instructions.ts` implement the same spec: identical build.json/inventory schemas (including `section`/`sections`), palette, projection constants, validation rules, chapter/ghosting rendering, adaptive step sizing, and byte-identical `.ldr` output. The Python `pdf` subcommand is the ONLY supported PDF path for large builds — headless-Chrome print-to-pdf flattens SVG `<use>` reuse and balloons at scale. When changing one implementation, mirror the change in the other and in `brick-design-guide.md`.
