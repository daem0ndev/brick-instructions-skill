#!/usr/bin/env python3
"""render_instructions.py - LEGO-style instruction booklet generator (pure stdlib).

Python port of render-instructions.ts for environments without Bun or a browser,
notably the ChatGPT (Work) code-interpreter sandbox, including mobile. The PDF is
generated natively (hand-written vector PDF, no third-party libraries, no network).

Scales to thousands of pieces: each step's geometry is emitted ONCE - as an SVG
<symbol> referenced via <use> in the HTML, and as a PDF Form XObject referenced
via Do in the PDF - so output size grows linearly with brick count instead of
quadratically (steps x bricks). Auto-stepping adapts pieces-per-step to build
size (8 small / 16 medium / 24 large).

  python3 render_instructions.py validate build.json [--inventory inv.json]
  python3 render_instructions.py render   build.json [-o out.html]
  python3 render_instructions.py pdf      build.json [-o out.pdf]
  python3 render_instructions.py ldr      build.json [-o out.ldr]
"""
import json, math, sys

PALETTE = {
    "red": "#C91A09", "blue": "#0055BF", "yellow": "#F2CD37", "green": "#237841",
    "white": "#F4F4F4", "black": "#1B2A34", "tan": "#E4CD9E", "light-gray": "#A0A5A9",
    "dark-gray": "#6C6E68", "orange": "#FE8A18", "brown": "#583927", "lime": "#BBE90B",
    "dark-blue": "#0A3463", "dark-red": "#720E0F", "pink": "#FC97AC",
    "purple": "#81007B", "sand-green": "#A0BCAC", "azure": "#36AEBF",
    "dark-green": "#184632", "reddish-brown": "#582A12",
    # trans-* colors render translucent (glass) in both HTML and PDF
    "trans-clear": "#E6EFF2", "trans-light-blue": "#93C7DE", "trans-dark-blue": "#0059A3",
    "trans-black": "#635F52", "trans-red": "#C91A09", "trans-yellow": "#F5CD2F",
    "trans-green": "#237841", "trans-neon-orange": "#FF800D",
}

def is_trans(c):
    return c.startswith("trans-")

LDRAW_COLOR = {
    "red": 4, "blue": 1, "yellow": 14, "green": 2, "white": 15, "black": 0, "tan": 19,
    "light-gray": 71, "dark-gray": 72, "orange": 25, "brown": 6, "lime": 27,
    "dark-blue": 272, "dark-red": 320, "pink": 13, "purple": 5, "sand-green": 378, "azure": 322,
    "dark-green": 288, "reddish-brown": 70,
    "trans-clear": 47, "trans-light-blue": 43, "trans-dark-blue": 33, "trans-black": 40,
    "trans-red": 36, "trans-yellow": 46, "trans-green": 34, "trans-neon-orange": 57,
}
# "shape:AxB-H" (A<=B studs, H plates) -> BrickLink/LDraw part number.
# Curated from the BrickLink catalog (catalogList.asp?catType=P): bricks/plates,
# tiles, slopes, curved slopes, panels, Window/Glass (catString=81), Plant &
# foliage (catString=25/95). Extend alongside references/part-registry.md, or
# use any other real part via the per-brick "part" override.
LDRAW_PART = {
    "box:1x1-3": "3005", "box:1x2-3": "3004", "box:1x3-3": "3622", "box:1x4-3": "3010",
    "box:1x6-3": "3009", "box:1x8-3": "3008", "box:2x2-3": "3003", "box:2x3-3": "3002",
    "box:2x4-3": "3001", "box:2x6-3": "2456", "box:2x8-3": "3007",
    "box:1x1-1": "3024", "box:1x2-1": "3023", "box:1x3-1": "3623", "box:1x4-1": "3710",
    "box:1x6-1": "3666", "box:1x8-1": "3460", "box:2x2-1": "3022", "box:2x3-1": "3021",
    "box:2x4-1": "3020", "box:2x6-1": "3795", "box:2x8-1": "3034", "box:4x4-1": "3031",
    "box:4x6-1": "3032", "box:4x8-1": "3035", "box:6x8-1": "3036",
    "tile:1x1-1": "3070b", "tile:1x2-1": "3069b", "tile:1x3-1": "63864", "tile:1x4-1": "2431",
    "tile:1x6-1": "6636", "tile:1x8-1": "4162", "tile:2x2-1": "3068b", "tile:2x4-1": "87079",
    "slope:1x2-3": "3040", "slope:2x2-3": "3039", "slope:2x4-3": "3037", "slope:1x2-2": "85984",
    "cheese:1x1-2": "54200",
    "curved:1x2-2": "11477", "curved:1x4-2": "93273", "curved:2x2-2": "15068",
    "round:1x1-3": "3062b", "round:1x1-1": "4073",
    "panel:1x2-3": "4865b", "panel:1x2-6": "87552", "panel:1x4-9": "60581",
    "window:1x2-6": "60592", "window:1x4-9": "60594",
    "foliage:3x4-1": "2423", "foliage:5x6-1": "2417", "foliage:2x2-3": "30176",
}
IX = math.sqrt(3) / 2
PLATE = 0.4        # plate height in stud units (3.2mm / 8mm pitch)
STUD_R = 0.3       # stud radius in stud units
STUD_H = 0.5625    # stud height in plate units (1.8mm / 3.2mm)
LARGE_BUILD_THRESHOLD = 120  # bricks; above this, sections are strongly recommended
FLAT_STRUCTURE_HEIGHT_THRESHOLD = 15  # plates; taller all-1-stud-deep sections read as flat walls
STUDDED_HERO_MAX = 400  # bricks; above this the hero render drops stud detail

def pieces_per_step(n):
    """Real LEGO booklets use bigger steps on bigger sets; also bounds booklet length."""
    return 24 if n > 1000 else 16 if n > 300 else 8


def fp(b):
    return (b["size"][1], b["size"][0]) if b.get("rot") == 90 else (b["size"][0], b["size"][1])

def hex_for(c, build):
    return build.get("colors", {}).get(c) or PALETTE.get(c) or (c if c.startswith("#") else "#AAAAAA")

def section_id(b):
    return b.get("section") or ""

def section_title(build, sid):
    for s in build.get("sections", []):
        if s["id"] == sid:
            return s.get("title", sid)
    return sid or "Build"

def section_order(build):
    seen, order = set(), []
    for s in build.get("sections", []):
        if s["id"] not in seen:
            seen.add(s["id"])
            order.append(s["id"])
    for b in build["bricks"]:
        sid = section_id(b)
        if sid not in seen:
            seen.add(sid)
            order.append(sid)
    return order

def rgb01(hexs):
    n = int(hexs[1:], 16)
    return ((n >> 16 & 255) / 255, (n >> 8 & 255) / 255, (n & 255) / 255)

def shade(hexs, f):
    n = int(hexs[1:], 16)
    ch = lambda v: max(0, min(255, round(v * f)))
    return "#%02x%02x%02x" % (ch(n >> 16 & 255), ch(n >> 8 & 255), ch(n & 255))

def proj(x, y, z):
    return ((x - y) * IX, (x + y) * 0.5 - z * PLATE)

def shape_of(b):
    return b.get("shape") or "box"

def part_key(b):
    a, c = sorted(b["size"][:2])
    h = b["size"][2]
    s = shape_of(b)
    if s == "box":
        kind = "brick" if h == 3 else "plate" if h == 1 else f"{h}-plate-tall"
    elif s == "cheese":
        kind = "cheese slope"
    elif s == "curved":
        kind = "curved slope"
    elif s == "round":
        kind = "round plate" if h == 1 else "round brick"
    else:
        kind = s  # tile, slope, panel, window, foliage
    return f"{a}x{c}", kind, f"{s}:{a}x{c}-{h}"

def ensure_steps(build):
    """Auto-step per section (never mixes two sections into one step),
    continuing the global step counter across sections. If every brick
    already has an explicit step, respect it as-is (manual pacing)."""
    if all(b.get("step") is not None for b in build["bricks"]):
        return
    cap = pieces_per_step(len(build["bricks"]))
    step = 0
    for sec_id in section_order(build):
        group = [b for b in build["bricks"] if section_id(b) == sec_id]
        last_z, in_step = -1, 0
        for b in sorted(group, key=lambda b: (b["pos"][2], b["pos"][1], b["pos"][0])):
            if b["pos"][2] != last_z or in_step >= cap:
                step += 1
                in_step = 0
                last_z = b["pos"][2]
            b["step"] = step
            in_step += 1

# ---------- validation ----------

def cells(b):
    w, d = fp(b)
    for i in range(w):
        for j in range(d):
            for k in range(b["size"][2]):
                yield (b["pos"][0] + i, b["pos"][1] + j, b["pos"][2] + k)

def validate(build, inventory=None):
    errors, warnings = [], []
    bricks = build["bricks"]
    def name(b, i):
        return b.get("id") or "#%d(%s %s @%s)" % (i + 1, part_key(b)[0], b["color"], ",".join(map(str, b["pos"])))

    occ = {}
    for i, b in enumerate(bricks):
        for cell in cells(b):
            if cell in occ:
                errors.append("collision: %s overlaps %s at %s" % (name(b, i), name(bricks[occ[cell]], occ[cell]), cell))
            occ[cell] = i
        if b["pos"][2] < 0:
            errors.append("below ground: " + name(b, i))

    # connectivity via spatial hash of plan cells (near-linear at 1000s of bricks)
    top_at, bot_at = {}, {}
    for i, b in enumerate(bricks):
        w, d = fp(b)
        for dx in range(w):
            for dy in range(d):
                tk = (b["pos"][0] + dx, b["pos"][1] + dy, b["pos"][2] + b["size"][2])
                bk = (b["pos"][0] + dx, b["pos"][1] + dy, b["pos"][2])
                top_at.setdefault(tk, []).append(i)
                bot_at.setdefault(bk, []).append(i)
    adj_sets = [set() for _ in bricks]
    for k, tops in top_at.items():
        bots = bot_at.get(k)
        if not bots:
            continue
        for i in tops:
            for j in bots:
                if i != j:
                    adj_sets[i].add(j)
                    adj_sets[j].add(i)
    adj = [list(s) for s in adj_sets]
    seen = set(i for i, b in enumerate(bricks) if b["pos"][2] == 0)
    queue = list(seen)
    while queue:
        for n in adj[queue.pop()]:
            if n not in seen:
                seen.add(n)
                queue.append(n)
    for i, b in enumerate(bricks):
        if i not in seen:
            errors.append("floating: %s is not connected to the ground" % name(b, i))

    for i, b in enumerate(bricks):
        if b["pos"][2] == 0:
            continue
        supports = [j for j in adj[i] if bricks[j]["pos"][2] + bricks[j]["size"][2] == b["pos"][2]]
        if not supports:
            warnings.append("hangs from above only: %s (build order may be awkward)" % name(b, i))
        elif all((bricks[j].get("step") or 1) > (b.get("step") or 1) for j in supports):
            warnings.append("step order: %s placed before anything that supports it" % name(b, i))

    # section discipline: warn if a section's steps are interrupted by another
    # section, and nudge large unsectioned builds toward decomposition.
    step_sections = {}
    for b in bricks:
        s = b.get("step") or 1
        step_sections.setdefault(s, set()).add(section_id(b))
    ever_seen, warned, prev_active = set(), set(), set()
    for s in sorted(step_sections):
        active = step_sections[s]
        for sid in active:
            if sid not in prev_active and sid in ever_seen and sid not in warned:
                warnings.append("section order: '%s' resumes after another section started (around step %d) - group each section's steps contiguously" % (section_title(build, sid), s))
                warned.add(sid)
            ever_seen.add(sid)
        prev_active = active
    if len(bricks) > LARGE_BUILD_THRESHOLD and len(section_order(build)) <= 1:
        warnings.append("large build (%d bricks) has no sections defined - consider decomposing per brick-design-guide.md section Large-Scale Decomposition" % len(bricks))

    # flat structures: a tall section built entirely from 1-stud-deep bricks is
    # a silhouette wall, not a volume - see brick-design-guide.md Scale Planning.
    for sec_id in section_order(build):
        sec_bricks = [b for b in bricks if section_id(b) == sec_id]
        if not sec_bricks:
            continue
        top = max(b["pos"][2] + b["size"][2] for b in sec_bricks)
        bottom = min(b["pos"][2] for b in sec_bricks)
        all_shallow = all(min(fp(b)) == 1 for b in sec_bricks)
        if top - bottom > FLAT_STRUCTURE_HEIGHT_THRESHOLD and all_shallow:
            warnings.append("flat structure: '%s' is %d plates tall but every brick is only 1 stud deep - it will read as a silhouette wall, not a volume; give it real depth (>=3-4 studs) unless that's intentional (a thin motif, sign, or fin)" % (section_title(build, sec_id), top - bottom))

    if inventory is not None:
        need = {}
        for b in bricks:
            dims, kind, _ = part_key(b)
            k = "%s %s %s" % (dims, kind, b["color"])
            need[k] = need.get(k, 0) + 1
        for k, n in need.items():
            have = next((e["qty"] for e in inventory if "%s %s %s" % (e["size"], e["kind"], e["color"]) == k), 0)
            if have < n:
                errors.append("inventory: need %dx %s, have %d" % (n, k, have))
    return errors, warnings

# ---------- shared geometry ----------

def bounds_of(bricks):
    mnx = mny = 1e9
    mxx = mxy = -1e9
    for b in bricks:
        w, d = fp(b)
        x0, y0, z0 = b["pos"]
        for x, y, z in [(x0, y0, z0), (x0 + w, y0, z0), (x0, y0 + d, z0), (x0 + w, y0 + d, z0),
                        (x0, y0, z0 + b["size"][2] + 0.6), (x0 + w, y0, z0 + b["size"][2] + 0.6),
                        (x0, y0 + d, z0 + b["size"][2] + 0.6), (x0 + w, y0 + d, z0 + b["size"][2] + 0.6)]:
            px, py = proj(x, y, z)
            mnx, mxx = min(mnx, px), max(mxx, px)
            mny, mxy = min(mny, py), max(mxy, py)
    return mnx, mny, mxx, mxy

def sorted_bricks(bricks):
    return sorted(bricks, key=lambda b: (b["pos"][2], b["pos"][0] + b["pos"][1]))

def brick_faces(b):
    """Returns (top, left(+y), right(+x)) corner lists in world coords."""
    w, d = fp(b)
    x0, y0, z0 = b["pos"]
    x1, y1, z1 = x0 + w, y0 + d, z0 + b["size"][2]
    top = [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    left = [(x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)]
    right = [(x1, y0, z1), (x1, y1, z1), (x1, y1, z0), (x1, y0, z0)]
    return top, left, right, (x0, y0, z1, w, d)

def group_by_step(bricks):
    groups = {}
    for b in bricks:
        groups.setdefault(b["step"], []).append(b)
    return groups

# ---------- SVG / HTML ----------

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def brick_svg(b, build, studs, highlight, gray=False):
    """One brick's SVG geometry. studs=False is the cheap tier used inside
    step-group symbols; gray=True bakes the ghost palette. Shapes beyond
    "box" render archetype geometry (wedges, cylinders, thin panels,
    foliage blobs) so specialized real parts read correctly."""
    hexc = "#D7DAE0" if gray else hex_for(b["color"], build)
    w, d = fp(b)
    x0, y0, z0 = b["pos"]
    hgt = b["size"][2]
    x1, y1, z1 = x0 + w, y0 + d, z0 + hgt
    sh = shape_of(b)
    trans = (not gray) and is_trans(b["color"])
    pts = lambda arr: " ".join("%.2f,%.2f" % proj(x, y, z) for x, y, z in arr)
    if highlight:
        stroke = 'stroke="#111" stroke-width="0.06"'
    elif sh == "window":
        stroke = 'stroke="#2b2f36" stroke-width="0.05"'
    else:
        stroke = 'stroke="rgba(0,0,0,.35)" stroke-width="0.025"'
    s = '<g stroke-linejoin="round"%s>' % (' fill-opacity="0.55"' if trans else "")
    P = lambda arr, f: '<polygon points="%s" fill="%s" %s/>' % (pts(arr), shade(hexc, f), stroke)

    if sh == "round":
        r = min(w, d) * 0.4
        cx, cy = x0 + w / 2, y0 + d / 2
        px, py_t = proj(cx, cy, z1)
        _, py_b = proj(cx, cy, z0)
        rx, ry = r * 1.22, r * 0.71
        s += '<rect x="%.2f" y="%.2f" width="%.3f" height="%.3f" fill="%s" %s/>' % (px - rx, py_t, 2 * rx, py_b - py_t, shade(hexc, 0.74), stroke)
        s += '<ellipse cx="%.2f" cy="%.2f" rx="%.3f" ry="%.3f" fill="%s"/>' % (px, py_b, rx, ry, shade(hexc, 0.74))
        s += '<ellipse cx="%.2f" cy="%.2f" rx="%.3f" ry="%.3f" fill="%s" %s/>' % (px, py_t, rx, ry, hexc, stroke)
        return s + "</g>"

    if sh == "foliage":
        cx, cy = x0 + w / 2, y0 + d / 2
        px, py = proj(cx, cy, z0 + hgt * 0.55)
        R = max(w, d) * 0.62
        rx, ry = R * 1.1, R * 0.62
        s += '<ellipse cx="%.2f" cy="%.2f" rx="%.3f" ry="%.3f" fill="%s" %s/>' % (px - rx * 0.45, py + ry * 0.28, rx * 0.72, ry * 0.75, shade(hexc, 0.78), stroke)
        s += '<ellipse cx="%.2f" cy="%.2f" rx="%.3f" ry="%.3f" fill="%s" %s/>' % (px + rx * 0.42, py + ry * 0.2, rx * 0.68, ry * 0.7, shade(hexc, 0.88), stroke)
        s += '<ellipse cx="%.2f" cy="%.2f" rx="%.3f" ry="%.3f" fill="%s" %s/>' % (px, py - ry * 0.22, rx * 0.8, ry * 0.8, hexc, stroke)
        return s + "</g>"

    if sh in ("slope", "cheese", "curved"):
        # wedge descending toward +y (viewer-left); rot 90 descends toward +x
        if b.get("rot") == 90:
            s += P([(x0, y1, z0), (x1, y1, z0), (x0, y1, z1)], 0.82)
            if sh == "curved":
                xm, zm = x0 + (x1 - x0) * 0.45, z0 + (z1 - z0) * 0.72
                s += P([(x1, y0, z0), (x1, y1, z0), (xm, y1, zm), (xm, y0, zm)], 0.78)
                s += P([(xm, y0, zm), (xm, y1, zm), (x0, y1, z1), (x0, y0, z1)], 0.9)
            else:
                s += P([(x1, y0, z0), (x1, y1, z0), (x0, y1, z1), (x0, y0, z1)], 0.8)
        else:
            s += P([(x1, y0, z0), (x1, y1, z0), (x1, y0, z1)], 0.66)
            if sh == "curved":
                ym, zm = y0 + (y1 - y0) * 0.45, z0 + (z1 - z0) * 0.72
                s += P([(x0, y1, z0), (x1, y1, z0), (x1, ym, zm), (x0, ym, zm)], 0.86)
                s += P([(x0, ym, zm), (x1, ym, zm), (x1, y0, z1), (x0, y0, z1)], 0.97)
            else:
                s += P([(x0, y1, z0), (x1, y1, z0), (x1, y0, z1), (x0, y0, z1)], 0.92)
        return s + "</g>"

    if sh in ("panel", "window"):
        # thin wall at the back (-y) edge; trans-* colors = curtain wall/glazing
        t = 0.35
        s += P([(x0, y0 + t, z1), (x1, y0 + t, z1), (x1, y0 + t, z0), (x0, y0 + t, z0)], 0.82)
        s += P([(x1, y0, z1), (x1, y0 + t, z1), (x1, y0 + t, z0), (x1, y0, z0)], 0.66)
        s += P([(x0, y0, z1), (x1, y0, z1), (x1, y0 + t, z1), (x0, y0 + t, z1)], 1.0)
        return s + "</g>"

    # box / tile
    s += P([(x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)], 0.82)
    s += P([(x1, y0, z1), (x1, y1, z1), (x1, y1, z0), (x1, y0, z0)], 0.66)
    s += P([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], 1.06 if sh == "tile" else 1.0)
    if not studs or sh == "tile":
        return s + "</g>"
    rx, ry = STUD_R * 1.22, STUD_R * 0.71
    for i in range(w):
        for j in range(d):
            cx, cy_top = proj(x0 + i + 0.5, y0 + j + 0.5, z1 + STUD_H)
            _, cy_base = proj(x0 + i + 0.5, y0 + j + 0.5, z1)
            s += '<rect x="%.2f" y="%.2f" width="%.3f" height="%.3f" fill="%s"/>' % (cx - rx, cy_top, 2 * rx, cy_base - cy_top, shade(hexc, 0.88))
            s += '<ellipse cx="%.2f" cy="%.2f" rx="%.3f" ry="%.3f" fill="%s"/>' % (cx, cy_base, rx, ry, shade(hexc, 0.88))
            s += '<ellipse cx="%.2f" cy="%.2f" rx="%.3f" ry="%.3f" fill="%s" stroke="rgba(0,0,0,.25)" stroke-width="0.02"/>' % (cx, cy_top, rx, ry, shade(hexc, 1.08))
    return s + "</g>"

def view_box(bounds, pad=0.8):
    mnx, mny, mxx, mxy = bounds
    return "%.2f %.2f %.2f %.2f" % (mnx - pad, mny - pad, mxx - mnx + 2 * pad, mxy - mny + 2 * pad)

def model_svg(bricks, build, bounds, css_class, studs):
    body = "".join(brick_svg(b, build, studs, False) for b in sorted_bricks(bricks))
    return '<svg class="%s" viewBox="%s" xmlns="http://www.w3.org/2000/svg">%s</svg>' % (css_class, view_box(bounds), body)

def part_svg(size, color, build, shape="box"):
    b = {"size": list(size), "pos": [0, 0, 0], "color": color, "shape": shape}
    return model_svg([b], build, bounds_of([b]), "part-svg", True)

CSS = """
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
"""

def agg_parts(bricks):
    agg = {}
    for b in bricks:
        dims, kind, key = part_key(b)
        k = "%s %s" % (key, b["color"])
        if k in agg:
            agg[k]["qty"] += 1
        else:
            a, c = sorted(b["size"][:2])
            agg[k] = {"size": (a, c, b["size"][2]), "color": b["color"], "shape": shape_of(b),
                      "label": "%s %s" % (dims, kind), "qty": 1}
    return sorted(agg.values(), key=lambda e: (-e["size"][2], -e["size"][0] * e["size"][1]))

def build_html(build):
    ensure_steps(build)
    bricks = build["bricks"]
    n_steps = max(b["step"] for b in bricks)
    bounds = bounds_of(bricks)
    vb = view_box(bounds)
    max_x = max(b["pos"][0] + fp(b)[0] for b in bricks)
    max_y = max(b["pos"][1] + fp(b)[1] for b in bricks)
    max_z = max(b["pos"][2] + b["size"][2] for b in bricks)

    order = section_order(build)
    multi_section = len(order) > 1

    groups = group_by_step(bricks)
    step_section = {s: section_id(lst[0]) for s, lst in groups.items()}
    # Each step's geometry emitted once as a <g id> in a hidden <defs> block,
    # then referenced with <use> everywhere else - linear, not quadratic.
    defs = "".join('<g id="sg%d">%s</g>' % (s, "".join(brick_svg(b, build, False, False) for b in sorted_bricks(groups.get(s, []))))
                   for s in range(1, n_steps + 1))

    bom_html = "".join(
        '<div class="part"><div class="part-img">%s</div><div class="part-label">%dx %s<br><span>%s</span></div></div>'
        % (part_svg(e["size"], e["color"], build, e["shape"]), e["qty"], esc(e["label"]), esc(e["color"]))
        for e in agg_parts(bricks))

    toc_html = ""
    if multi_section:
        rows = ""
        for sid in order:
            sec_bricks = [b for b in bricks if section_id(b) == sid]
            steps = [b["step"] for b in sec_bricks]
            rows += '<div class="toc-row"><span class="toc-title">%s</span><span class="toc-meta">steps %d-%d - %d pieces</span></div>' % (
                esc(section_title(build, sid)), min(steps), max(steps), len(sec_bricks))
        toc_html = '<h2>Sections</h2><div class="toc">%s</div>' % rows

    chapter_start = {}
    if multi_section:
        for sid in order:
            steps = [b["step"] for b in bricks if section_id(b) == sid]
            if steps:
                chapter_start[min(steps)] = sid

    if len(bricks) <= STUDDED_HERO_MAX:
        hero = model_svg(bricks, build, bounds, "hero-svg", True)
    else:
        hero = '<svg class="hero-svg" viewBox="%s" xmlns="http://www.w3.org/2000/svg">%s</svg>' % (
            vb, "".join('<use href="#sg%d"/>' % t for t in range(1, n_steps + 1)))

    steps_html = ""
    for s in range(1, n_steps + 1):
        if s in chapter_start:
            sid = chapter_start[s]
            sec_bricks = [b for b in bricks if section_id(b) == sid]
            meta = next((sec for sec in build.get("sections", []) if sec["id"] == sid), None)
            steps_html += ('<div class="chapter"><div class="chapter-title">Section %d - %s</div>%s'
                          '<div class="chapter-meta">%d pieces - steps %d-%d</div></div>'
                          % (order.index(sid) + 1, esc(section_title(build, sid)),
                             '<div class="chapter-note">%s</div>' % esc(meta["note"]) if meta and meta.get("note") else "",
                             len(sec_bricks), s, max(b["step"] for b in sec_bricks)))
        cur_sec = step_section.get(s, "")
        added = groups.get(s, [])
        callout = "".join('<div class="callout-part">%s<span>%dx</span></div>' % (part_svg(e["size"], e["color"], build, e["shape"]), e["qty"])
                          for e in agg_parts(added))
        notes = "".join('<p class="note">%s</p>' % esc(b["note"]) for b in added if b.get("note"))
        uses = "".join('<use href="#sg%d"%s/>' % (t, ' class="gh"' if multi_section and step_section.get(t) != cur_sec else "")
                       for t in range(1, s))
        current = "".join(brick_svg(b, build, True, True) for b in sorted_bricks(added))
        steps_html += ('<section class="step"><div class="step-head"><div class="step-num">%d</div>'
                       '<div class="callout">%s</div></div>'
                       '<svg class="step-svg" viewBox="%s" xmlns="http://www.w3.org/2000/svg">%s%s</svg>%s</section>'
                       % (s, callout, vb, uses, current, notes))

    sub = '<div class="sub">%s</div>' % esc(build["subtitle"]) if build.get("subtitle") else ""
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>%s - Building Instructions</title><style>%s</style></head><body>'
            '<svg width="0" height="0" style="position:absolute" xmlns="http://www.w3.org/2000/svg"><defs>%s</defs></svg>'
            '<div class="page cover"><div class="badge">BUILDING INSTRUCTIONS</div><h1>%s</h1>%s'
            '<div class="hero">%s</div>'
            '<div class="stats"><div><b>%d</b> pieces</div><div><b>%d</b> steps</div>'
            '<div><b>%dx%d</b> studs</div><div><b>%d</b> plates tall</div></div>'
            '%s'
            '<h2>Parts List</h2><div class="bom">%s</div></div>'
            '<div class="page"><h2>Steps</h2><div class="steps">%s</div></div>'
            '<footer>%s - generated by brick-instructions</footer></body></html>'
            % (esc(build["title"]), CSS, defs, esc(build["title"]), sub, hero,
               len(bricks), n_steps, max_x, max_y, max_z, toc_html, bom_html, steps_html,
               esc(build.get("author", ""))))

# ---------- native PDF (no dependencies; Form XObjects for scale) ----------

BEZ_K = 0.552284749831
RED = rgb01("#C91A09")
GRAY = (0.35, 0.38, 0.41)
INK = (0.1, 0.11, 0.13)

def _poly_ops(o, pts, fill, stroke, lw):
    o.append("%.3f %.3f %.3f rg" % fill)
    o.append("%.3f %.3f %.3f RG %.3f w" % (stroke + (lw,)))
    o.append("%.2f %.2f m" % pts[0])
    for p in pts[1:]:
        o.append("%.2f %.2f l" % p)
    o.append("h b")

def _ellipse_ops(o, cx, cy, rx, ry, fill, stroke=None, lw=0.02):
    k = BEZ_K
    o.append("%.3f %.3f %.3f rg" % fill)
    if stroke:
        o.append("%.3f %.3f %.3f RG %.3f w" % (stroke + (lw,)))
    o.append("%.2f %.2f m" % (cx + rx, cy))
    o.append("%.3f %.3f %.3f %.3f %.2f %.2f c" % (cx + rx, cy + k * ry, cx + k * rx, cy + ry, cx, cy + ry))
    o.append("%.3f %.3f %.3f %.3f %.2f %.2f c" % (cx - k * rx, cy + ry, cx - rx, cy + k * ry, cx - rx, cy))
    o.append("%.3f %.3f %.3f %.3f %.2f %.2f c" % (cx - rx, cy - k * ry, cx - k * rx, cy - ry, cx, cy - ry))
    o.append("%.3f %.3f %.3f %.3f %.2f %.2f c" % (cx + k * rx, cy - ry, cx + rx, cy - k * ry, cx + rx, cy))
    o.append("b" if stroke else "f")

def model_brick_ops(b, build, mnx, mny, studs, highlight, gray=False, pad=0.8):
    """One brick's PDF ops in MODEL space (projected units, y grows DOWN;
    placement matrices flip it). Used both inside Form XObjects and inline.
    Shape-aware (wedges, cylinders, panels, foliage) with trans-* colors
    rendered via the /GT ExtGState alpha."""
    o = []
    hexc = "#D7DAE0" if gray else hex_for(b["color"], build)
    w, d = fp(b)
    x0, y0, z0 = b["pos"]
    hgt = b["size"][2]
    x1, y1, z1 = x0 + w, y0 + d, z0 + hgt
    sh = shape_of(b)
    trans = (not gray) and is_trans(b["color"])
    M = lambda px, py: (px - (mnx - pad), py - (mny - pad))
    P = lambda pt: M(*proj(*pt))
    if highlight:
        stroke, lw = (0.07, 0.07, 0.07), 0.06
    elif gray:
        stroke, lw = (0.78, 0.79, 0.81), 0.02
    elif sh == "window":
        stroke, lw = (0.17, 0.18, 0.21), 0.05
    else:
        stroke, lw = (0.25, 0.25, 0.25), 0.02
    if trans:
        o.append("/GT gs")
    poly = lambda pts_, f: _poly_ops(o, pts_, rgb01(shade(hexc, f)), stroke, lw)

    if sh == "round":
        r = min(w, d) * 0.4
        cx, cy = x0 + w / 2, y0 + d / 2
        px, py_t = M(*proj(cx, cy, z1))
        _, py_b = M(*proj(cx, cy, z0))
        rx, ry = r * 1.22, r * 0.71
        o.append("%.3f %.3f %.3f rg %.2f %.2f %.3f %.3f re f" % (rgb01(shade(hexc, 0.74)) + (px - rx, py_t, 2 * rx, py_b - py_t)))
        _ellipse_ops(o, px, py_b, rx, ry, rgb01(shade(hexc, 0.74)))
        _ellipse_ops(o, px, py_t, rx, ry, rgb01(hexc), stroke, lw)
    elif sh == "foliage":
        cx, cy = x0 + w / 2, y0 + d / 2
        px, py = M(*proj(cx, cy, z0 + hgt * 0.55))
        R = max(w, d) * 0.62
        rx, ry = R * 1.1, R * 0.62
        _ellipse_ops(o, px - rx * 0.45, py + ry * 0.28, rx * 0.72, ry * 0.75, rgb01(shade(hexc, 0.78)), stroke, lw)
        _ellipse_ops(o, px + rx * 0.42, py + ry * 0.2, rx * 0.68, ry * 0.7, rgb01(shade(hexc, 0.88)), stroke, lw)
        _ellipse_ops(o, px, py - ry * 0.22, rx * 0.8, ry * 0.8, rgb01(hexc), stroke, lw)
    elif sh in ("slope", "cheese", "curved"):
        if b.get("rot") == 90:
            poly([P((x0, y1, z0)), P((x1, y1, z0)), P((x0, y1, z1))], 0.82)
            if sh == "curved":
                xm, zm = x0 + (x1 - x0) * 0.45, z0 + (z1 - z0) * 0.72
                poly([P((x1, y0, z0)), P((x1, y1, z0)), P((xm, y1, zm)), P((xm, y0, zm))], 0.78)
                poly([P((xm, y0, zm)), P((xm, y1, zm)), P((x0, y1, z1)), P((x0, y0, z1))], 0.9)
            else:
                poly([P((x1, y0, z0)), P((x1, y1, z0)), P((x0, y1, z1)), P((x0, y0, z1))], 0.8)
        else:
            poly([P((x1, y0, z0)), P((x1, y1, z0)), P((x1, y0, z1))], 0.66)
            if sh == "curved":
                ym, zm = y0 + (y1 - y0) * 0.45, z0 + (z1 - z0) * 0.72
                poly([P((x0, y1, z0)), P((x1, y1, z0)), P((x1, ym, zm)), P((x0, ym, zm))], 0.86)
                poly([P((x0, ym, zm)), P((x1, ym, zm)), P((x1, y0, z1)), P((x0, y0, z1))], 0.97)
            else:
                poly([P((x0, y1, z0)), P((x1, y1, z0)), P((x1, y0, z1)), P((x0, y0, z1))], 0.92)
    elif sh in ("panel", "window"):
        t = 0.35
        poly([P((x0, y0 + t, z1)), P((x1, y0 + t, z1)), P((x1, y0 + t, z0)), P((x0, y0 + t, z0))], 0.82)
        poly([P((x1, y0, z1)), P((x1, y0 + t, z1)), P((x1, y0 + t, z0)), P((x1, y0, z0))], 0.66)
        poly([P((x0, y0, z1)), P((x1, y0, z1)), P((x1, y0 + t, z1)), P((x0, y0 + t, z1))], 1.0)
    else:
        # box / tile
        poly([P((x0, y1, z1)), P((x1, y1, z1)), P((x1, y1, z0)), P((x0, y1, z0))], 0.82)
        poly([P((x1, y0, z1)), P((x1, y1, z1)), P((x1, y1, z0)), P((x1, y0, z0))], 0.66)
        poly([P((x0, y0, z1)), P((x1, y0, z1)), P((x1, y1, z1)), P((x0, y1, z1))], 1.06 if sh == "tile" else 1.0)
        if studs and sh != "tile":
            rx, ry = STUD_R * 1.22, STUD_R * 0.71
            for i in range(w):
                for j in range(d):
                    tx, ty = M(*proj(x0 + i + 0.5, y0 + j + 0.5, z1 + STUD_H))
                    bx, by = M(*proj(x0 + i + 0.5, y0 + j + 0.5, z1))
                    o.append("%.3f %.3f %.3f rg %.2f %.2f %.3f %.3f re f" % (rgb01(shade(hexc, 0.88)) + (bx - rx, ty, 2 * rx, by - ty)))
                    _ellipse_ops(o, bx, by, rx, ry, rgb01(shade(hexc, 0.88)))
                    _ellipse_ops(o, tx, ty, rx, ry, rgb01(shade(hexc, 1.08)), (0.3, 0.3, 0.3), 0.015)
    if trans:
        o.append("/GN gs")
    return o

class Canvas:
    def __init__(self):
        self.ops = []

    def raw(self, op):
        self.ops.append(op)

    def rect(self, x, y, w, h, fill):
        self.ops.append("%.3f %.3f %.3f rg %.2f %.2f %.2f %.2f re f" % (fill + (x, y, w, h)))

    def rect_stroke(self, x, y, w, h, rgb):
        self.ops.append("%.3f %.3f %.3f RG 1 w %.2f %.2f %.2f %.2f re S" % (rgb + (x, y, w, h)))

    def text(self, x, y, s, size=10, color=(0, 0, 0), bold=False, center=False):
        if center:
            x -= 0.25 * size * len(s)  # approx 0.5em average glyph width
        t = s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        self.ops.append("BT /%s %.1f Tf %.3f %.3f %.3f rg %.2f %.2f Td (%s) Tj ET"
                        % ("F2" if bold else "F1", size, color[0], color[1], color[2], x, y, t))

    def place(self, rect, bw, bh, inner_ops):
        """Fit-place model-space ops (y down, 0..bw x 0..bh) into a page rect."""
        rx0, ry0, rw, rh = rect
        s = min(rw / bw, rh / bh)
        x0 = rx0 + (rw - bw * s) / 2
        ytop = ry0 + (rh - bh * s) / 2 + bh * s
        self.ops.append("q %.4f 0 0 %.4f %.2f %.2f cm" % (s, -s, x0, ytop))
        self.ops.extend(inner_ops)
        self.ops.append("Q")

    def stream(self):
        return "\n".join(self.ops)

def pdf_bytes(pages, forms, bw, bh, W=792, H=612):
    """forms: ordered list of (name, ops_list) in model space. All pages share
    one Resources dict referencing every form (PDF readers lazy-load them).
    /GT is the translucency ExtGState used by trans-* (glass) colors; forms
    carry a small resources dict of their own (obj 6) so /GT resolves inside
    form content streams too."""
    GS = "/ExtGState << /GT << /ca 0.55 /CA 0.7 >> /GN << /ca 1 /CA 1 >> >>"
    objs = {}  # num -> (dict_str, stream_bytes|None)
    n_forms = len(forms)
    form_base = 7
    page_base = form_base + n_forms
    n_pages = len(pages)
    kids = " ".join("%d 0 R" % (page_base + 2 * i) for i in range(n_pages))
    xobj = " ".join("/%s %d 0 R" % (forms[i][0], form_base + i) for i in range(n_forms))
    objs[1] = ("<< /Type /Catalog /Pages 2 0 R >>", None)
    objs[2] = ("<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, n_pages), None)
    objs[3] = ("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>", None)
    objs[4] = ("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>", None)
    objs[5] = ("<< /Font << /F1 3 0 R /F2 4 0 R >> /XObject << %s >> %s >>" % (xobj, GS), None)
    objs[6] = ("<< %s >>" % GS, None)
    for i, (fname, fops) in enumerate(forms):
        data = "\n".join(fops).encode("cp1252", "replace")
        objs[form_base + i] = ("<< /Type /XObject /Subtype /Form /BBox [0 0 %.2f %.2f] /Resources 6 0 R /Length %d >>" % (bw, bh, len(data)), data)
    for i, cv in enumerate(pages):
        data = cv.stream().encode("cp1252", "replace")
        objs[page_base + 2 * i] = ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Resources 5 0 R /Contents %d 0 R >>" % (W, H, page_base + 2 * i + 1), None)
        objs[page_base + 2 * i + 1] = ("<< /Length %d >>" % len(data), data)
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        d, stream = objs[num]
        out += ("%d 0 obj\n" % num).encode()
        out += d.encode()
        if stream is not None:
            out += b"\nstream\n" + stream + b"\nendstream"
        out += b"\nendobj\n"
    xref = len(out)
    count = len(objs) + 1
    out += ("xref\n0 %d\n" % count).encode()
    out += b"0000000000 65535 f \n"
    for num in sorted(offsets):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (count, xref)).encode()
    return bytes(out)

def build_pdf(build):
    ensure_steps(build)
    bricks = build["bricks"]
    n_steps = max(b["step"] for b in bricks)
    bounds = bounds_of(bricks)
    mnx, mny, mxx, mxy = bounds
    pad = 0.8
    bw, bh = mxx - mnx + 2 * pad, mxy - mny + 2 * pad
    max_x = max(b["pos"][0] + fp(b)[0] for b in bricks)
    max_y = max(b["pos"][1] + fp(b)[1] for b in bricks)
    max_z = max(b["pos"][2] + b["size"][2] for b in bricks)
    order = section_order(build)
    multi_section = len(order) > 1
    W, H = 792, 612
    groups = group_by_step(bricks)
    step_section = {s: section_id(lst[0]) for s, lst in groups.items()}

    # Form XObjects: each step's flat geometry ONCE (normal + ghost-gray
    # variants); every later step just references them - linear output size.
    forms = []
    for s in range(1, n_steps + 1):
        lst = sorted_bricks(groups.get(s, []))
        ops_n, ops_g = [], []
        for b in lst:
            ops_n.extend(model_brick_ops(b, build, mnx, mny, False, False, False, pad))
            ops_g.extend(model_brick_ops(b, build, mnx, mny, False, False, True, pad))
        forms.append(("S%d" % s, ops_n))
        forms.append(("G%d" % s, ops_g))

    def refs(upto, cur_sec):
        o = []
        for t in range(1, upto):
            ghost = multi_section and step_section.get(t) != cur_sec
            o.append("/%s Do" % (("G%d" if ghost else "S%d") % t))
        return o

    pages = []

    # cover
    cv = Canvas()
    cv.rect(40, H - 52, 170, 20, RED)
    cv.text(52, H - 46, "BUILDING INSTRUCTIONS", 9, (1, 1, 1), bold=True)
    cv.text(40, H - 84, build["title"], 26, INK, bold=True)
    if build.get("subtitle"):
        cv.text(40, H - 102, build["subtitle"], 11, GRAY)
    if len(bricks) <= STUDDED_HERO_MAX:
        hero_ops = []
        for b in sorted_bricks(bricks):
            hero_ops.extend(model_brick_ops(b, build, mnx, mny, True, False, False, pad))
        cv.place((196, 175, 400, 300), bw, bh, hero_ops)
    else:
        cv.place((196, 175, 400, 300), bw, bh, ["/S%d Do" % t for t in range(1, n_steps + 1)])
    stats = "%d pieces   |   %d steps   |   %dx%d studs   |   %d plates tall" % (len(bricks), n_steps, max_x, max_y, max_z)
    cv.text(W / 2, 155, stats, 11, GRAY, center=True)
    cv.text(40, 128, "PARTS LIST", 11, GRAY, bold=True)
    entries = agg_parts(bricks)
    shown = entries[:16]
    for idx, e in enumerate(shown):
        col, row = idx % 4, idx // 4
        x, y = 40 + col * 185, 96 - row * 34
        pb = {"size": list(e["size"]), "pos": [0, 0, 0], "color": e["color"], "shape": e["shape"]}
        pmnx, pmny, pmxx, pmxy = bounds_of([pb])
        pops = model_brick_ops(pb, build, pmnx, pmny, True, False, False, pad)
        cv.place((x, y - 4, 34, 28), pmxx - pmnx + 2 * pad, pmxy - pmny + 2 * pad, pops)
        cv.text(x + 42, y + 10, "%dx %s" % (e["qty"], e["label"]), 9, INK, bold=True)
        cv.text(x + 42, y, e["color"], 8, GRAY)
    if len(entries) > 16:
        cv.text(40, 18, "+ %d more part types (see HTML booklet for the full list)" % (len(entries) - 16), 8.5, GRAY)
    pages.append(cv)

    if multi_section:
        cv = Canvas()
        cv.text(40, H - 44, "SECTIONS", 14, INK, bold=True)
        for idx, sid in enumerate(order):
            sec_bricks = [b for b in bricks if section_id(b) == sid]
            steps = [b["step"] for b in sec_bricks]
            y = H - 76 - idx * 26
            cv.rect(40, y - 6, 18, 18, RED)
            cv.text(45, y - 1, str(idx + 1), 10, (1, 1, 1), bold=True, center=True)
            cv.text(66, y, section_title(build, sid), 11, INK, bold=True)
            cv.text(66, y - 12, "steps %d-%d - %d pieces" % (min(steps), max(steps), len(sec_bricks)), 8.5, GRAY)
        pages.append(cv)

    chapter_start = {}
    if multi_section:
        for sid in order:
            steps = [b["step"] for b in bricks if section_id(b) == sid]
            if steps:
                chapter_start[min(steps)] = sid

    # steps, 4 per page; a new page also starts whenever a chapter begins
    margin, gutter = 30, 16
    cw, chh = (W - 2 * margin - gutter) / 2, (H - 2 * margin - gutter) / 2
    idx = 4
    for s in range(1, n_steps + 1):
        if idx >= 4 or s in chapter_start:
            cv = Canvas()
            pages.append(cv)
            idx = 0
        if s in chapter_start:
            sid = chapter_start[s]
            sec_bricks = [b for b in bricks if section_id(b) == sid]
            cv.rect(0, H - 40, W, 40, INK)
            cv.text(30, H - 25, "SECTION %d - %s" % (order.index(sid) + 1, section_title(build, sid).upper()), 14, (1, 1, 1), bold=True)
            meta = next((sec for sec in build.get("sections", []) if sec["id"] == sid), None)
            if meta and meta.get("note"):
                cv.text(30, H - 36, meta["note"][:110], 8, (0.78, 0.8, 0.83))
            else:
                cv.text(30, H - 36, "%d pieces - steps %d-%d" % (len(sec_bricks), s, max(b["step"] for b in sec_bricks)), 8, (0.78, 0.8, 0.83))
        top_offset = 40 if s in chapter_start else 0
        col, row = idx % 2, idx // 2
        cx0 = margin + col * (cw + gutter)
        cy0 = H - margin - top_offset - chh - row * (chh + gutter)
        cur_sec = step_section.get(s, "")
        cv.rect_stroke(cx0, cy0, cw, chh, (0.89, 0.9, 0.92))
        cv.rect(cx0 + 10, cy0 + chh - 36, 26, 26, RED)
        cv.text(cx0 + 23, cy0 + chh - 28, str(s), 14, (1, 1, 1), bold=True, center=True)
        added = groups.get(s, [])
        callout = "   ".join("%dx %s %s" % (e["qty"], e["label"], e["color"]) for e in agg_parts(added))
        cv.text(cx0 + 46, cy0 + chh - 24, ("Add:  " + callout)[:120], 8.5, GRAY)
        notes = [b["note"] for b in added if b.get("note")]
        if notes:
            cv.text(cx0 + 46, cy0 + chh - 35, notes[0][:80], 7.5, GRAY)
        inner = refs(s, cur_sec)
        for b in sorted_bricks(added):
            inner.extend(model_brick_ops(b, build, mnx, mny, True, True, False, pad))
        cv.place((cx0 + 14, cy0 + 10, cw - 28, chh - 56), bw, bh, inner)
        idx += 1
    return pdf_bytes(pages, forms, bw, bh, W, H)

# ---------- LDraw export ----------

def build_ldr(build):
    lines = ["0 " + build["title"], "0 Name: %s.ldr" % build["title"].replace(" ", "_"),
             "0 Author: %s" % build.get("author", "brick-instructions"), "0 BFC CERTIFY CCW"]
    for b in build["bricks"]:
        _, _, key = part_key(b)
        part = b.get("part") or LDRAW_PART.get(key)
        if not part:
            lines.append("0 // WARNING: no LDraw part mapping for %s (%s) - set an explicit \"part\" on this brick" % (key, b["color"]))
            continue
        w, d = fp(b)
        color = LDRAW_COLOR.get(b["color"], 7)
        x = (b["pos"][0] + w / 2) * 20
        z = (b["pos"][1] + d / 2) * 20
        y = -(b["pos"][2] + b["size"][2]) * 8
        native_rot = (b["size"][0] > b["size"][1]) != (b.get("rot") == 90)
        m = "0 0 1 0 1 0 -1 0 0" if native_rot else "1 0 0 0 1 0 0 0 1"
        lines.append("1 %d %g %g %g %s %s.dat" % (color, x, y, z, m, part))
    return "\n".join(lines) + "\n"

# ---------- CLI ----------

def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)
    cmd, file = args[0], args[1]
    rest = args[2:]
    opt = lambda flag: rest[rest.index(flag) + 1] if flag in rest else None
    with open(file) as f:
        build = json.load(f)
    ensure_steps(build)

    if cmd == "validate":
        inv = None
        if opt("--inventory"):
            with open(opt("--inventory")) as f:
                inv = json.load(f)
        errors, warnings = validate(build, inv)
        for e in errors[:40]:
            print("ERROR   " + e)
        if len(errors) > 40:
            print("... and %d more errors" % (len(errors) - 40))
        for w in warnings[:40]:
            print("warning " + w)
        if len(warnings) > 40:
            print("... and %d more warnings" % (len(warnings) - 40))
        print("%d bricks, %d steps - %d errors, %d warnings"
              % (len(build["bricks"]), max(b["step"] for b in build["bricks"]), len(errors), len(warnings)))
        sys.exit(1 if errors else 0)
    elif cmd in ("render", "pdf", "ldr"):
        errors, _ = validate(build)
        for e in errors[:20]:
            print("ERROR   " + e)
        if len(errors) > 20:
            print("... and %d more errors" % (len(errors) - 20))
        ext = {"render": ".html", "pdf": ".pdf", "ldr": ".ldr"}[cmd]
        out = opt("-o") or file.rsplit(".json", 1)[0] + ext
        if cmd == "render":
            with open(out, "w") as f:
                f.write(build_html(build))
        elif cmd == "pdf":
            with open(out, "wb") as f:
                f.write(build_pdf(build))
        else:
            with open(out, "w") as f:
                f.write(build_ldr(build))
        print("wrote %s%s" % (out, " (%d validation errors - fix before shipping)" % len(errors) if errors else ""))
    else:
        print("unknown command: " + cmd)
        sys.exit(1)

if __name__ == "__main__":
    main()
