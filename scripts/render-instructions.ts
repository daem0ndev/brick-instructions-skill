#!/usr/bin/env bun
/**
 * render-instructions.ts — LEGO-style instruction booklet generator.
 * Canonical input: build.json — ALL outputs derive from it; iterate by editing
 * the JSON and re-rendering (cheap, deterministic).
 *
 * Scales to thousands of pieces: each step's geometry is emitted ONCE as an
 * SVG <symbol> and referenced with <use> in every later step, so booklet size
 * grows linearly with brick count instead of quadratically (steps × bricks).
 * Sections render as chapters with a TOC; bricks outside the active section
 * are ghosted via CSS on the <use> reference. Auto-stepping adapts pieces-per-
 * step to build size (8 small / 16 medium / 24 large).
 *
 *   bun render-instructions.ts render   build.json [-o out.html]
 *   bun render-instructions.ts validate build.json [--inventory inv.json]
 *   bun render-instructions.ts ldr      build.json [-o out.ldr]
 */

type Vec3 = [number, number, number];
interface Brick {
  id?: string;
  size: Vec3; // [width(x studs), depth(y studs), height(plates: brick=3, plate=1)]
  pos: Vec3; // [x stud, y stud, z plate-level], z=0 is ground
  rot?: 0 | 90; // 90 swaps width/depth
  color: string; // palette name or #hex
  section?: string; // groups bricks into booklet chapters for large builds
  step?: number; // omit everywhere for auto layer-based steps
  note?: string;
}
interface SectionMeta {
  id: string;
  title: string;
  note?: string;
}
interface Build {
  title: string;
  subtitle?: string;
  author?: string;
  colors?: Record<string, string>; // custom palette overrides
  sections?: SectionMeta[]; // declares section order/titles; optional
  bricks: Brick[];
}

const PALETTE: Record<string, string> = {
  red: "#C91A09", blue: "#0055BF", yellow: "#F2CD37", green: "#237841",
  white: "#F4F4F4", black: "#1B2A34", tan: "#E4CD9E", "light-gray": "#A0A5A9",
  "dark-gray": "#6C6E68", orange: "#FE8A18", brown: "#583927", lime: "#BBE90B",
  "dark-blue": "#0A3463", "dark-red": "#720E0F", pink: "#FC97AC",
  purple: "#81007B", "sand-green": "#A0BCAC", azure: "#36AEBF",
};
const LDRAW_COLOR: Record<string, number> = {
  red: 4, blue: 1, yellow: 14, green: 2, white: 15, black: 0, tan: 19,
  "light-gray": 71, "dark-gray": 72, orange: 25, brown: 6, lime: 27,
  "dark-blue": 272, "dark-red": 320, pink: 13, purple: 5, "sand-green": 378, azure: 322,
};
// "AxB-H" (A<=B studs, H plates) -> LDraw part number
const LDRAW_PART: Record<string, string> = {
  "1x1-3": "3005", "1x2-3": "3004", "1x3-3": "3622", "1x4-3": "3010",
  "1x6-3": "3009", "1x8-3": "3008", "2x2-3": "3003", "2x3-3": "3002",
  "2x4-3": "3001", "2x6-3": "2456", "2x8-3": "3007",
  "1x1-1": "3024", "1x2-1": "3023", "1x3-1": "3623", "1x4-1": "3710",
  "1x6-1": "3666", "1x8-1": "3460", "2x2-1": "3022", "2x3-1": "3021",
  "2x4-1": "3020", "2x6-1": "3795", "2x8-1": "3034", "4x4-1": "3031",
  "4x6-1": "3032", "4x8-1": "3035", "6x8-1": "3036",
};

const IX = Math.sqrt(3) / 2;
const PLATE = 0.4; // plate height in stud units (3.2mm / 8mm pitch)
const STUD_R = 0.3; // stud radius in stud units (4.8mm dia)
const LARGE_BUILD_THRESHOLD = 120; // bricks; above this, sections are strongly recommended
const FLAT_STRUCTURE_HEIGHT_THRESHOLD = 15; // plates; a section this tall built entirely from 1-stud-deep bricks reads as a flat wall, not a volume
const STUDDED_HERO_MAX = 400; // bricks; above this the hero render drops stud detail (subpixel anyway)

// Auto-step sizing: real LEGO booklets use bigger steps on bigger sets. This
// also bounds booklet length (a 2,500-piece build at 8/step would be 300+ steps).
const piecesPerStep = (n: number) => (n > 1000 ? 24 : n > 300 ? 16 : 8);

const fp = (b: Brick) =>
  b.rot === 90 ? { w: b.size[1], d: b.size[0] } : { w: b.size[0], d: b.size[1] };
const hexFor = (c: string, bld: Build) =>
  bld.colors?.[c] ?? PALETTE[c] ?? (c.startsWith("#") ? c : "#AAAAAA");
const sectionId = (b: Brick) => b.section ?? "";
const sectionTitle = (bld: Build, id: string) => bld.sections?.find((s) => s.id === id)?.title ?? (id || "Build");

function sectionOrder(build: Build): string[] {
  const seen = new Set<string>();
  const order: string[] = [];
  for (const s of build.sections ?? []) if (!seen.has(s.id)) { seen.add(s.id); order.push(s.id); }
  for (const b of build.bricks) { const id = sectionId(b); if (!seen.has(id)) { seen.add(id); order.push(id); } }
  return order;
}

function shade(hex: string, f: number): string {
  const n = parseInt(hex.slice(1), 16);
  const ch = (v: number) => Math.max(0, Math.min(255, Math.round(v * f)));
  return (
    "#" +
    [(n >> 16) & 255, (n >> 8) & 255, n & 255]
      .map((v) => ch(v).toString(16).padStart(2, "0"))
      .join("")
  );
}

// Isometric-style projection. z is in plate units; screen y grows downward.
const proj = (x: number, y: number, z: number): [number, number] => [
  (x - y) * IX,
  (x + y) * 0.5 - z * PLATE,
];

function partKey(b: Brick): { dims: string; kind: string; key: string } {
  const [a, c] = [b.size[0], b.size[1]].sort((x, y) => x - y);
  const h = b.size[2];
  const kind = h === 3 ? "brick" : h === 1 ? "plate" : `${h}-plate-tall`;
  return { dims: `${a}x${c}`, kind, key: `${a}x${c}-${h}` };
}

// Auto-step per section (never mixes two sections into one step), continuing
// the global step counter across sections. If every brick already has an
// explicit step, respect it as-is (manual pacing).
function ensureSteps(build: Build) {
  if (build.bricks.every((b) => b.step != null)) return;
  const cap = piecesPerStep(build.bricks.length);
  let step = 0;
  for (const secId of sectionOrder(build)) {
    const group = build.bricks.filter((b) => sectionId(b) === secId);
    const sorted = [...group].sort(
      (a, b) => a.pos[2] - b.pos[2] || a.pos[1] - b.pos[1] || a.pos[0] - b.pos[0],
    );
    let lastZ = -1, inStep = 0;
    for (const b of sorted) {
      if (b.pos[2] !== lastZ || inStep >= cap) {
        step++;
        inStep = 0;
        lastZ = b.pos[2];
      }
      b.step = step;
      inStep++;
    }
  }
}

// ---------- geometry / validation ----------

function* cells(b: Brick): Generator<[number, number, number]> {
  const { w, d } = fp(b);
  for (let i = 0; i < w; i++)
    for (let j = 0; j < d; j++)
      for (let k = 0; k < b.size[2]; k++)
        yield [b.pos[0] + i, b.pos[1] + j, b.pos[2] + k];
}

function planOverlap(a: Brick, b: Brick): boolean {
  const fa = fp(a), fb = fp(b);
  return (
    a.pos[0] < b.pos[0] + fb.w && b.pos[0] < a.pos[0] + fa.w &&
    a.pos[1] < b.pos[1] + fb.d && b.pos[1] < a.pos[1] + fa.d
  );
}

interface Report { errors: string[]; warnings: string[]; }

function validate(build: Build, inventory?: { size: string; kind: string; color: string; qty: number }[]): Report {
  const errors: string[] = [], warnings: string[] = [];
  const bricks = build.bricks;
  const name = (b: Brick, i: number) => b.id ?? `#${i + 1}(${partKey(b).dims} ${b.color} @${b.pos.join(",")})`;

  // collisions
  const occ = new Map<string, number>();
  bricks.forEach((b, i) => {
    for (const [x, y, z] of cells(b)) {
      const k = `${x},${y},${z}`;
      if (occ.has(k)) errors.push(`collision: ${name(b, i)} overlaps ${name(bricks[occ.get(k)!], occ.get(k)!)} at (${k})`);
      occ.set(k, i);
    }
    if (b.pos[2] < 0) errors.push(`below ground: ${name(b, i)}`);
  });

  // connectivity: bricks connect when vertically adjacent + plan overlap.
  // Spatial-hash the plan cells so this stays near-linear at thousands of bricks.
  const topAt = new Map<string, number[]>(); // "x,y,zTop" -> brick idx list
  const botAt = new Map<string, number[]>();
  bricks.forEach((b, i) => {
    const { w, d } = fp(b);
    for (let dx = 0; dx < w; dx++)
      for (let dy = 0; dy < d; dy++) {
        const tk = `${b.pos[0] + dx},${b.pos[1] + dy},${b.pos[2] + b.size[2]}`;
        const bk = `${b.pos[0] + dx},${b.pos[1] + dy},${b.pos[2]}`;
        if (!topAt.has(tk)) topAt.set(tk, []);
        topAt.get(tk)!.push(i);
        if (!botAt.has(bk)) botAt.set(bk, []);
        botAt.get(bk)!.push(i);
      }
  });
  const adjSets: Set<number>[] = bricks.map(() => new Set());
  for (const [k, tops] of topAt) {
    const bots = botAt.get(k);
    if (!bots) continue;
    for (const i of tops) for (const j of bots) if (i !== j) { adjSets[i].add(j); adjSets[j].add(i); }
  }
  const adj: number[][] = adjSets.map((s) => [...s]);
  const seen = new Set<number>();
  const queue = bricks.map((b, i) => (b.pos[2] === 0 ? i : -1)).filter((i) => i >= 0);
  queue.forEach((i) => seen.add(i));
  while (queue.length) for (const n of adj[queue.shift()!]) if (!seen.has(n)) { seen.add(n); queue.push(n); }
  bricks.forEach((b, i) => {
    if (!seen.has(i)) errors.push(`floating: ${name(b, i)} is not connected to the ground`);
  });

  // buildability: each step supported by earlier/same-step bricks or ground
  bricks.forEach((b, i) => {
    if (b.pos[2] === 0) return;
    const supports = adj[i].filter((j) => bricks[j].pos[2] + bricks[j].size[2] === b.pos[2]);
    if (!supports.length) warnings.push(`hangs from above only: ${name(b, i)} (build order may be awkward)`);
    else if (supports.every((j) => (bricks[j].step ?? 1) > (b.step ?? 1)))
      warnings.push(`step order: ${name(b, i)} placed before anything that supports it`);
  });

  // section discipline: warn if a section's steps are interrupted by another
  // section (defeats the point of chapters), and nudge large unsectioned builds.
  const stepSections = new Map<number, Set<string>>();
  bricks.forEach((b) => {
    const s = b.step ?? 1;
    if (!stepSections.has(s)) stepSections.set(s, new Set());
    stepSections.get(s)!.add(sectionId(b));
  });
  const steps = [...stepSections.keys()].sort((a, b) => a - b);
  const everSeen = new Set<string>(), warnedInterleaved = new Set<string>();
  let prevActive = new Set<string>();
  for (const s of steps) {
    const active = stepSections.get(s)!;
    for (const id of active) {
      if (!prevActive.has(id) && everSeen.has(id) && !warnedInterleaved.has(id)) {
        warnings.push(`section order: '${sectionTitle(build, id)}' resumes after another section started (around step ${s}) — group each section's steps contiguously`);
        warnedInterleaved.add(id);
      }
      everSeen.add(id);
    }
    prevActive = active;
  }
  const allDefaultSection = sectionOrder(build).length <= 1;
  if (bricks.length > LARGE_BUILD_THRESHOLD && allDefaultSection) {
    warnings.push(`large build (${bricks.length} bricks) has no sections defined — consider decomposing per brick-design-guide.md §Large-Scale Decomposition`);
  }

  // flat structures: a tall section built entirely from 1-stud-deep bricks is
  // a silhouette wall, not a volume — fine for small motifs, a smell for a
  // hero structure. See brick-design-guide.md §Scale Planning.
  for (const secId of sectionOrder(build)) {
    const secBricks = bricks.filter((b) => sectionId(b) === secId);
    if (!secBricks.length) continue;
    const top = Math.max(...secBricks.map((b) => b.pos[2] + b.size[2]));
    const bottom = Math.min(...secBricks.map((b) => b.pos[2]));
    const allShallow = secBricks.every((b) => Math.min(fp(b).w, fp(b).d) === 1);
    if (top - bottom > FLAT_STRUCTURE_HEIGHT_THRESHOLD && allShallow) {
      warnings.push(`flat structure: '${sectionTitle(build, secId)}' is ${top - bottom} plates tall but every brick is only 1 stud deep — it will read as a silhouette wall, not a volume; give it real depth (≥3-4 studs) unless that's intentional (a thin motif, sign, or fin)`);
    }
  }

  // inventory
  if (inventory) {
    const need = new Map<string, number>();
    bricks.forEach((b) => {
      const p = partKey(b);
      const k = `${p.dims} ${p.kind} ${b.color}`;
      need.set(k, (need.get(k) ?? 0) + 1);
    });
    for (const [k, n] of need) {
      const have = inventory.find((e) => `${e.size} ${e.kind} ${e.color}` === k)?.qty ?? 0;
      if (have < n) errors.push(`inventory: need ${n}× ${k}, have ${have}`);
    }
  }
  return { errors, warnings };
}

// ---------- SVG rendering ----------

interface Bounds { minX: number; minY: number; maxX: number; maxY: number; }

function boundsOf(bricks: Brick[]): Bounds {
  let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9;
  for (const b of bricks) {
    const { w, d } = fp(b);
    for (const [x, y, z] of [
      [b.pos[0], b.pos[1], b.pos[2]], [b.pos[0] + w, b.pos[1], b.pos[2]],
      [b.pos[0], b.pos[1] + d, b.pos[2]], [b.pos[0] + w, b.pos[1] + d, b.pos[2]],
      [b.pos[0], b.pos[1], b.pos[2] + b.size[2] + 0.6], [b.pos[0] + w, b.pos[1], b.pos[2] + b.size[2] + 0.6],
      [b.pos[0], b.pos[1] + d, b.pos[2] + b.size[2] + 0.6], [b.pos[0] + w, b.pos[1] + d, b.pos[2] + b.size[2] + 0.6],
    ] as Vec3[]) {
      const [px, py] = proj(x, y, z);
      minX = Math.min(minX, px); maxX = Math.max(maxX, px);
      minY = Math.min(minY, py); maxY = Math.max(maxY, py);
    }
  }
  return { minX, minY, maxX, maxY };
}

const sortedBricks = (bricks: Brick[]) =>
  [...bricks].sort((a, b) => a.pos[2] - b.pos[2] || a.pos[0] + a.pos[1] - (b.pos[0] + b.pos[1]));

// One brick's SVG geometry. `studs: false` = the cheap tier (3 polygons) used
// for step-group symbols; `studs: true` adds full stud detail; `highlight`
// bolds the outline for pieces new in the current step.
function brickSVG(b: Brick, bld: Build, studs: boolean, highlight: boolean): string {
  const { w, d } = fp(b);
  const [x0, y0, z0] = [b.pos[0], b.pos[1], b.pos[2]];
  const [x1, y1, z1] = [x0 + w, y0 + d, z0 + b.size[2]];
  const hex = hexFor(b.color, bld);
  const pts = (arr: Vec3[]) => arr.map(([x, y, z]) => proj(x, y, z).map((v) => v.toFixed(2)).join(",")).join(" ");
  const stroke = highlight ? `stroke="#111" stroke-width="0.06"` : `stroke="rgba(0,0,0,.35)" stroke-width="0.025"`;
  let s = `<g stroke-linejoin="round">`;
  s += `<polygon points="${pts([[x0, y1, z1], [x1, y1, z1], [x1, y1, z0], [x0, y1, z0]])}" fill="${shade(hex, 0.82)}" ${stroke}/>`; // +y face (left)
  s += `<polygon points="${pts([[x1, y0, z1], [x1, y1, z1], [x1, y1, z0], [x1, y0, z0]])}" fill="${shade(hex, 0.66)}" ${stroke}/>`; // +x face (right)
  s += `<polygon points="${pts([[x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]])}" fill="${hex}" ${stroke}/>`; // top
  if (!studs) return s + `</g>`;
  const studH = 0.5625; // in plate units (1.8mm / 3.2mm)
  for (let i = 0; i < w; i++)
    for (let j = 0; j < d; j++) {
      const [cx, cyTop] = proj(x0 + i + 0.5, y0 + j + 0.5, z1 + studH);
      const [, cyBase] = proj(x0 + i + 0.5, y0 + j + 0.5, z1);
      const rx = (STUD_R * 1.22).toFixed(3), ry = (STUD_R * 0.71).toFixed(3);
      s += `<rect x="${(cx - STUD_R * 1.22).toFixed(2)}" y="${cyTop.toFixed(2)}" width="${(STUD_R * 2.44).toFixed(3)}" height="${(cyBase - cyTop).toFixed(3)}" fill="${shade(hex, 0.88)}"/>`;
      s += `<ellipse cx="${cx.toFixed(2)}" cy="${cyBase.toFixed(2)}" rx="${rx}" ry="${ry}" fill="${shade(hex, 0.88)}"/>`;
      s += `<ellipse cx="${cx.toFixed(2)}" cy="${cyTop.toFixed(2)}" rx="${rx}" ry="${ry}" fill="${shade(hex, 1.08)}" stroke="rgba(0,0,0,.25)" stroke-width="0.02"/>`;
    }
  return s + `</g>`;
}

const viewBoxOf = (bounds: Bounds, pad = 0.8) =>
  `${(bounds.minX - pad).toFixed(2)} ${(bounds.minY - pad).toFixed(2)} ${(bounds.maxX - bounds.minX + 2 * pad).toFixed(2)} ${(bounds.maxY - bounds.minY + 2 * pad).toFixed(2)}`;

// Standalone model render (hero, part thumbnails) — geometry drawn inline.
function modelSVG(bricks: Brick[], bld: Build, bounds: Bounds, cssClass: string, studs: boolean): string {
  const body = sortedBricks(bricks).map((b) => brickSVG(b, bld, studs, false)).join("");
  return `<svg class="${cssClass}" viewBox="${viewBoxOf(bounds)}" xmlns="http://www.w3.org/2000/svg">${body}</svg>`;
}

function partSVG(size: Vec3, color: string, bld: Build): string {
  const b: Brick = { size, pos: [0, 0, 0], color };
  return modelSVG([b], bld, boundsOf([b]), "part-svg", true);
}

// ---------- HTML booklet ----------

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function buildHTML(build: Build): string {
  ensureSteps(build);
  const bricks = build.bricks;
  const nSteps = Math.max(...bricks.map((b) => b.step!));
  const bounds = boundsOf(bricks);
  const vb = viewBoxOf(bounds);

  const maxX = Math.max(...bricks.map((b) => b.pos[0] + fp(b).w));
  const maxY = Math.max(...bricks.map((b) => b.pos[1] + fp(b).d));
  const maxZ = Math.max(...bricks.map((b) => b.pos[2] + b.size[2]));

  const order = sectionOrder(build);
  const multiSection = order.length > 1;

  // Per-step brick groups, painter-sorted within each step. Each becomes one
  // <g id="sgN"> in a shared <defs>, referenced with <use> everywhere after —
  // the core trick that keeps booklet size LINEAR in brick count.
  const stepBricks = new Map<number, Brick[]>();
  for (const b of bricks) {
    if (!stepBricks.has(b.step!)) stepBricks.set(b.step!, []);
    stepBricks.get(b.step!)!.push(b);
  }
  const stepSection = new Map<number, string>();
  for (const [s, list] of stepBricks) stepSection.set(s, sectionId(list[0]));
  let defs = "";
  for (let s = 1; s <= nSteps; s++) {
    const list = stepBricks.get(s) ?? [];
    defs += `<g id="sg${s}">${sortedBricks(list).map((b) => brickSVG(b, build, false, false)).join("")}</g>`;
  }

  const bom = new Map<string, { size: Vec3; color: string; label: string; qty: number }>();
  for (const b of bricks) {
    const p = partKey(b);
    const k = `${p.key} ${b.color}`;
    const e = bom.get(k);
    if (e) e.qty++;
    else bom.set(k, { size: [Math.min(b.size[0], b.size[1]), Math.max(b.size[0], b.size[1]), b.size[2]], color: b.color, label: `${p.dims} ${p.kind}`, qty: 1 });
  }
  const bomHTML = [...bom.values()]
    .sort((a, b) => b.size[2] - a.size[2] || b.size[0] * b.size[1] - a.size[0] * a.size[1])
    .map((e) => `<div class="part"><div class="part-img">${partSVG(e.size, e.color, build)}</div><div class="part-label">${e.qty}× ${esc(e.label)}<br><span>${esc(e.color)}</span></div></div>`)
    .join("");

  let tocHTML = "";
  if (multiSection) {
    const rows = order.map((id) => {
      const secBricks = bricks.filter((b) => sectionId(b) === id);
      const steps = secBricks.map((b) => b.step!);
      return `<div class="toc-row"><span class="toc-title">${esc(sectionTitle(build, id))}</span><span class="toc-meta">steps ${Math.min(...steps)}–${Math.max(...steps)} · ${secBricks.length} pieces</span></div>`;
    }).join("");
    tocHTML = `<h2>Sections</h2><div class="toc">${rows}</div>`;
  }

  // Chapter divider markers: step number -> section id that starts there.
  const chapterStart = new Map<number, string>();
  if (multiSection) {
    for (const id of order) {
      const steps = bricks.filter((b) => sectionId(b) === id).map((b) => b.step!);
      if (steps.length) chapterStart.set(Math.min(...steps), id);
    }
  }

  // Hero: full-stud detail for small builds; flat via <use> for large ones
  // (studs are subpixel there anyway, and it keeps the cover cheap).
  const heroSVG = bricks.length <= STUDDED_HERO_MAX
    ? modelSVG(bricks, build, bounds, "hero-svg", true)
    : `<svg class="hero-svg" viewBox="${vb}" xmlns="http://www.w3.org/2000/svg">${Array.from({ length: nSteps }, (_, i) => `<use href="#sg${i + 1}"/>`).join("")}</svg>`;

  let stepsHTML = "";
  for (let s = 1; s <= nSteps; s++) {
    if (chapterStart.has(s)) {
      const id = chapterStart.get(s)!;
      const secBricks = bricks.filter((b) => sectionId(b) === id);
      const meta = build.sections?.find((sec) => sec.id === id);
      stepsHTML += `<div class="chapter"><div class="chapter-title">Section ${order.indexOf(id) + 1} — ${esc(sectionTitle(build, id))}</div>${meta?.note ? `<div class="chapter-note">${esc(meta.note)}</div>` : ""}<div class="chapter-meta">${secBricks.length} pieces · steps ${s}–${Math.max(...secBricks.map((b) => b.step!))}</div></div>`;
    }
    const curSec = stepSection.get(s) ?? "";
    const added = stepBricks.get(s) ?? [];
    const parts = new Map<string, { size: Vec3; color: string; qty: number }>();
    for (const b of added) {
      const p = partKey(b);
      const k = `${p.key} ${b.color}`;
      const e = parts.get(k);
      if (e) e.qty++;
      else parts.set(k, { size: [Math.min(b.size[0], b.size[1]), Math.max(b.size[0], b.size[1]), b.size[2]], color: b.color, qty: 1 });
    }
    const callout = [...parts.values()]
      .map((e) => `<div class="callout-part">${partSVG(e.size, e.color, build)}<span>${e.qty}×</span></div>`)
      .join("");
    const notes = added.filter((b) => b.note).map((b) => `<p class="note">💡 ${esc(b.note!)}</p>`).join("");
    // Prior steps as cheap <use> references (ghost-styled when cross-section);
    // only THIS step's bricks get inline full-stud geometry.
    const uses = Array.from({ length: s - 1 }, (_, i) => {
      const t = i + 1;
      const ghost = multiSection && stepSection.get(t) !== curSec;
      return `<use href="#sg${t}"${ghost ? ' class="gh"' : ""}/>`;
    }).join("");
    const current = sortedBricks(added).map((b) => brickSVG(b, build, true, true)).join("");
    stepsHTML += `<section class="step"><div class="step-head"><div class="step-num">${s}</div><div class="callout">${callout}</div></div><svg class="step-svg" viewBox="${vb}" xmlns="http://www.w3.org/2000/svg">${uses}${current}</svg>${notes}</section>`;
  }

  return `<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(build.title)} — Building Instructions</title>
<style>
  :root { --accent: #C91A09; --ink: #1a1d21; --paper: #fff; --edge: #e4e6ea; }
  * { box-sizing: border-box; margin: 0; }
  body { font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: var(--ink); background: #f2f3f5; }
  .page { background: var(--paper); max-width: 980px; margin: 24px auto; padding: 40px 48px; border-radius: 10px; box-shadow: 0 2px 14px rgba(0,0,0,.08); }
  .cover h1 { font-size: 40px; letter-spacing: -.02em; }
  .cover .sub { color: #5a6069; font-size: 17px; margin-top: 6px; }
  .badge { display: inline-block; background: var(--accent); color: #fff; font-weight: 700; padding: 4px 12px; border-radius: 6px; font-size: 13px; margin-bottom: 14px; letter-spacing: .06em; }
  .hero { text-align: center; margin: 20px 0 8px; }
  .hero svg { width: min(560px, 92%); }
  .stats { display: flex; gap: 28px; justify-content: center; margin: 14px 0 26px; color: #5a6069; font-size: 14px; }
  .stats b { color: var(--ink); font-size: 20px; display: block; text-align: center; }
  h2 { font-size: 15px; text-transform: uppercase; letter-spacing: .1em; color: #5a6069; border-bottom: 2px solid var(--edge); padding-bottom: 8px; margin-bottom: 16px; margin-top: 28px; }
  h2:first-of-type { margin-top: 0; }
  .toc { border: 1px solid var(--edge); border-radius: 8px; overflow: hidden; }
  .toc-row { display: flex; justify-content: space-between; padding: 10px 14px; font-size: 13px; }
  .toc-row:nth-child(odd) { background: #fafbfc; }
  .toc-title { font-weight: 700; }
  .toc-meta { color: #8a9099; }
  .bom { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 14px; }
  .part { display: flex; align-items: center; gap: 10px; border: 1px solid var(--edge); border-radius: 8px; padding: 8px 10px; }
  .part-img svg, .callout-part svg { width: 46px; height: 40px; }
  .part-label { font-size: 12.5px; font-weight: 600; } .part-label span { color: #8a9099; font-weight: 400; }
  .steps { display: grid; grid-template-columns: 1fr 1fr; gap: 22px; }
  .chapter { grid-column: 1 / -1; background: var(--ink); color: #fff; border-radius: 10px; padding: 16px 20px; margin-top: 6px; }
  .chapter-title { font-size: 18px; font-weight: 800; }
  .chapter-note { font-size: 12.5px; color: #c7cbd1; margin-top: 4px; }
  .chapter-meta { font-size: 11.5px; color: #9aa0a8; margin-top: 6px; text-transform: uppercase; letter-spacing: .06em; }
  .step { border: 1px solid var(--edge); border-radius: 10px; padding: 16px; break-inside: avoid; }
  .step-head { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 8px; }
  .step-num { background: var(--accent); color: #fff; font-size: 22px; font-weight: 800; min-width: 44px; height: 44px; border-radius: 8px; display: flex; align-items: center; justify-content: center; }
  .callout { display: flex; flex-wrap: wrap; gap: 8px; border: 1.5px dashed #c3c8cf; border-radius: 8px; padding: 6px 10px; flex: 1; min-height: 44px; align-items: center; }
  .callout-part { display: flex; align-items: center; gap: 3px; font-size: 13px; font-weight: 700; }
  .step-svg { width: 100%; max-height: 300px; }
  .gh { opacity: .4; filter: saturate(0) brightness(1.12); }
  .note { font-size: 12.5px; color: #5a6069; margin-top: 6px; }
  footer { text-align: center; color: #9aa0a8; font-size: 12px; margin: 18px 0 30px; }
  @media print {
    body { background: #fff; } footer { display: none; }
    .page { box-shadow: none; margin: 0 auto; border-radius: 0; max-width: none; padding: 24px 28px; }
    .cover { page-break-after: always; }
    .chapter { break-before: page; break-after: avoid; }
    .steps > .chapter:first-child { break-before: avoid; }
    @page { size: letter landscape; margin: 10mm; }
  }
</style></head><body>
<svg width="0" height="0" style="position:absolute" xmlns="http://www.w3.org/2000/svg"><defs>${defs}</defs></svg>
<div class="page cover">
  <div class="badge">BUILDING INSTRUCTIONS</div>
  <h1>${esc(build.title)}</h1>
  ${build.subtitle ? `<div class="sub">${esc(build.subtitle)}</div>` : ""}
  <div class="hero">${heroSVG}</div>
  <div class="stats">
    <div><b>${bricks.length}</b> pieces</div>
    <div><b>${nSteps}</b> steps</div>
    <div><b>${maxX}×${maxY}</b> studs</div>
    <div><b>${maxZ}</b> plates tall</div>
  </div>
  ${tocHTML}
  <h2>Parts List</h2>
  <div class="bom">${bomHTML}</div>
</div>
<div class="page">
  <h2>Steps</h2>
  <div class="steps">${stepsHTML}</div>
</div>
<footer>${esc(build.author ?? "")} · generated by brick-instructions</footer>
</body></html>`;
}

// ---------- LDraw export ----------

function buildLDR(build: Build): string {
  const lines = [`0 ${build.title}`, `0 Name: ${build.title.replace(/\s+/g, "_")}.ldr`, `0 Author: ${build.author ?? "brick-instructions"}`, `0 BFC CERTIFY CCW`];
  for (const b of build.bricks) {
    const p = partKey(b);
    const part = LDRAW_PART[p.key];
    if (!part) { lines.push(`0 // WARNING: no LDraw part mapping for ${p.key} (${b.color})`); continue; }
    const { w, d } = fp(b);
    const color = LDRAW_COLOR[b.color] ?? 7;
    const x = (b.pos[0] + w / 2) * 20;
    const z = (b.pos[1] + d / 2) * 20;
    const y = -(b.pos[2] + b.size[2]) * 8; // LDraw -Y is up; part origin at top of body
    // rotate about vertical axis when the part's native long side runs along x
    const nativeRot = (b.size[0] > b.size[1]) !== (b.rot === 90);
    const m = nativeRot ? "0 0 1 0 1 0 -1 0 0" : "1 0 0 0 1 0 0 0 1";
    lines.push(`1 ${color} ${x} ${y} ${z} ${m} ${part}.dat`);
  }
  return lines.join("\n") + "\n";
}

// ---------- CLI ----------

async function main() {
  const [cmd, file, ...rest] = process.argv.slice(2);
  if (!cmd || !file) {
    console.log("usage: render-instructions.ts <render|validate|ldr> build.json [-o out] [--inventory inv.json]");
    process.exit(1);
  }
  const build: Build = JSON.parse(await Bun.file(file).text());
  ensureSteps(build);
  const opt = (flag: string) => {
    const i = rest.indexOf(flag);
    return i >= 0 ? rest[i + 1] : undefined;
  };

  if (cmd === "validate") {
    const invPath = opt("--inventory");
    const inv = invPath ? JSON.parse(await Bun.file(invPath).text()) : undefined;
    const r = validate(build, inv);
    r.errors.forEach((e) => console.log(`ERROR   ${e}`));
    r.warnings.forEach((w) => console.log(`warning ${w}`));
    console.log(`${build.bricks.length} bricks, ${Math.max(...build.bricks.map((b) => b.step!))} steps — ${r.errors.length} errors, ${r.warnings.length} warnings`);
    process.exit(r.errors.length ? 1 : 0);
  } else if (cmd === "render") {
    const out = opt("-o") ?? file.replace(/\.json$/, "") + ".html";
    const r = validate(build);
    r.errors.forEach((e) => console.log(`ERROR   ${e}`));
    await Bun.write(out, buildHTML(build));
    console.log(`wrote ${out}${r.errors.length ? ` (${r.errors.length} validation errors — fix before shipping)` : ""}`);
    if (build.bricks.length > 300) {
      console.log(`note: for PDF on a build this size, use "python3 scripts/render_instructions.py pdf ${file}" — it stays small at any scale. Headless-Chrome's print-to-pdf does NOT preserve this HTML's <use> element reuse (it flattens/rasterizes), so printing a large build directly can produce a wildly oversized PDF.`);
    }
  } else if (cmd === "ldr") {
    const out = opt("-o") ?? file.replace(/\.json$/, "") + ".ldr";
    await Bun.write(out, buildLDR(build));
    console.log(`wrote ${out}`);
  } else {
    console.log(`unknown command: ${cmd}`);
    process.exit(1);
  }
}

main();
