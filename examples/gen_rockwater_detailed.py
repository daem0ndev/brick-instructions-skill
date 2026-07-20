#!/usr/bin/env python3
"""rockwater-detailed.build.json — DETAILED grand-scale Guitar Hotel using the specialized
part vocabulary: trans glass curtain walls (BrickLink Window/Glass, cat 81),
tiles, slopes/cheese contours, round-brick palm trunks + foliage canopies
(Plant cats 25/95), inset guitar strings, fretboard with fret lines.
"""
import json

bricks = []

def add(section, size, pos, color, shape=None, rot=None, note=None):
    b = {"size": list(size), "pos": list(pos), "color": color, "section": section}
    if shape:
        b["shape"] = shape
    if rot:
        b["rot"] = rot
    if note:
        b["note"] = note
    bricks.append(b)

def dec(total, chunks=(2, 1)):
    out, t = [], total
    for c in chunks:
        while t >= c:
            out.append(c); t -= c
    return out

def fill(section, x0, y0, w, d, z, h, color, shape=None, note=None, rev_rows=False):
    """rev_rows puts the odd 1-deep row at the FRONT (y0) instead of the back —
    used on depth-expansion bands so 2-deep rows span the new back depth and
    reach support on the shallower band below."""
    first = True
    yy = 0
    rows = dec(d)
    if rev_rows:
        rows = list(reversed(rows))
    for dy in rows:
        xx = 0
        for dx in dec(w):
            add(section, (dx, dy, h), (x0 + xx, y0 + yy, z), color, shape=shape,
                note=note if first else None)
            first = False
            xx += dx
        yy += dy

# ---------------- Section 1: podium ----------------
PW, PD = 48, 28
fill("podium", 0, 0, PW, PD, 0, 1, "light-gray",
     note="Lay the full 48x28 podium first — the entire resort keys off its top surface (z=1).")

# ---------------- Section 2: hotel wing (7 stories, glazed ribbon facade) ----------------
WX, WY, WW, WD = 0, 0, 24, 16
STORY = 3
STORIES = 7
for s in range(STORIES):
    z = 1 + s * STORY
    color = "light-gray" if s < 3 else "white"
    if s == 0:
        fill("hotel-wing", WX, WY, WW, WD, z, STORY, color,
             note="Ground story is solid; every story above gets a glass ribbon on the two street faces.")
        continue
    # interior core (excludes the two glazed outer faces)
    fill("hotel-wing", WX, WY, WW - 1, WD - 1, z, STORY, color)
    # glass ribbon: front face (y = WD-1) and right face (x = WW-1)
    xx = 0
    for dx in dec(WW):
        add("hotel-wing", (dx, 1, STORY), (WX + xx, WY + WD - 1, z), "trans-light-blue",
            note="Glass ribbon: trans-light-blue glazing along the visible faces (BrickLink Window/Glass, cat 81)." if s == 1 and xx == 0 else None)
        xx += dx
    yy = 0
    for dy in dec(WD - 1):
        add("hotel-wing", (1, dy, STORY), (WX + WW - 1, WY + yy, z), "trans-light-blue")
        yy += dy
# roof plate + white tile cornice on the visible edges
fill("hotel-wing", WX, WY, WW, WD, 1 + STORIES * STORY, 1, "white")
zr = 2 + STORIES * STORY
xx = 0
for dx in dec(WW):
    add("hotel-wing", (dx, 1, 1), (WX + xx, WY + WD - 1, zr), "white", shape="tile",
        note="Tile cornice: studless finish along the roof edge." if xx == 0 else None)
    xx += dx
yy = 0
for dy in dec(WD - 1):
    add("hotel-wing", (1, dy, 1), (WX + WW - 1, WY + yy, zr), "white", shape="tile")
    yy += dy

# ---------------- Section 3: guitar tower (glass skin, strings, fretboard) ----------------
BANDS = [
    (16, 8), (16, 8), (16, 8), (14, 7), (14, 7), (12, 6), (12, 6), (11, 6),
    (12, 6), (13, 7), (14, 7), (16, 8), (16, 8), (14, 7), (10, 5),
    (6, 4), (6, 4), (6, 4), (6, 4), (6, 4), (6, 4),
    (8, 5), (9, 5), (10, 6), (12, 6), (12, 6), (10, 5), (8, 4), (6, 3), (6, 3),
]
TX, TY = 28, 4
CX = TX + 8
STRING_XS = [CX - 5, CX - 3, CX - 1, CX + 1, CX + 3, CX + 5]
geo = []
z = 1
for i, (w, d) in enumerate(BANDS):
    x0 = CX - w // 2
    y0 = TY  # flat guitar face: depth varies toward the BACK only, so the front skin is always supported
    x1, y1 = x0 + w, y0 + d
    geo.append((x0, x1, y0, y1, z))
    is_neck = w <= 6 and 15 <= i <= 20
    note = None
    if i == 0:
        note = "Tower base: trans-dark-blue glass skin over a structural blue core — the real hotel is blue glass."
    elif i == 5:
        note = "Waist: body narrows in width AND depth; cheese slopes soften each shoulder."
    elif i == 15:
        note = "Neck: black fretboard face with a light-gray fret line each band."
    elif i == 21:
        note = "Headstock flares back out; tuner pegs cap the top."
    # Width-expansion bands need "bond courses": 2-deep corner pieces that tie
    # the front skin back into the structural mass below (front-row-only pieces
    # at an expanding shoulder would otherwise form an unrooted floating sheet —
    # exactly what a real builder solves with a deeper course at the shoulder).
    prev = geo[i - 1] if i > 0 else None
    exp_l = prev is not None and x0 < prev[0]
    exp_r = prev is not None and x1 > prev[1]
    fx0 = x0 + (2 if exp_l else 0)
    fx1 = x1 - (2 if exp_r else 0)
    if exp_l:
        add("guitar-tower", (2, 2, 3), (x0, y0, z), "blue")
        fill("guitar-tower", x0, y0 + 2, 2, d - 2, z, 3, "blue", rev_rows=True)
    if exp_r:
        add("guitar-tower", (2, 2, 3), (x1 - 2, y0, z), "blue")
        fill("guitar-tower", x1 - 2, y0 + 2, 2, d - 2, z, 3, "blue", rev_rows=True)
    # front face row (y0): fretboard on neck, glass with inset strings on body
    if is_neck:
        xx = fx0
        for dx in dec(fx1 - fx0):
            add("guitar-tower", (dx, 1, 2), (xx, y0, z), "black", note=note if xx == fx0 else None)
            add("guitar-tower", (dx, 1, 1), (xx, y0, z + 2), "light-gray", shape="tile")
            xx += dx
        note = None
    else:
        xcur = fx0
        while xcur < fx1:
            if w >= 12 and i <= 13 and xcur in STRING_XS:
                add("guitar-tower", (1, 1, 3), (xcur, y0, z), "trans-clear", shape="round",
                    note=note if xcur == x0 else None)
                xcur += 1
            else:
                nxt = fx1
                for sx in STRING_XS:
                    if w >= 12 and i <= 13 and xcur < sx < nxt:
                        nxt = sx
                run = nxt - xcur
                chunks = dec(run)
                if nxt == fx1:
                    chunks = list(reversed(chunks))
                for dx in chunks:
                    add("guitar-tower", (dx, 1, 3), (xcur, y0, z), "trans-dark-blue",
                        note=note if xcur == x0 else None)
                    note = None
                    xcur += dx
        note = None
    # right face column (x1-1) is glazed only when the band below supports it;
    # on width-expansion bands the core takes the full width instead (its 2-wide
    # pieces reach back to supported cells)
    glaze_right = not exp_r
    ix0 = x0 + (2 if exp_l else 0)
    ix1 = x1 - (2 if exp_r else (1 if glaze_right else 0))
    if glaze_right:
        yy = y0 + 1
        for dy in dec(y1 - 1 - (y0 + 1)):
            add("guitar-tower", (1, dy, 3), (x1 - 1, yy, z), "trans-dark-blue")
            yy += dy
    fill("guitar-tower", ix0, y0 + 1, ix1 - ix0, d - 1, z, 3, "blue", rev_rows=True)
    z += 3
# cheese-slope shoulders wherever the next band narrows
for i in range(len(geo) - 1):
    x0, x1, y0, y1, zt = geo[i]
    nx0, nx1, _, _, _ = geo[i + 1]
    top = zt + 3
    for x in range(x0, min(nx0, x1)):
        add("guitar-tower", (1, 1, 2), (x, y0, top), "blue", shape="cheese")
    for x in range(max(nx1, x0), x1):
        add("guitar-tower", (1, 1, 2), (x, y0, top), "blue", shape="cheese")
# tuner pegs across the top band
tx0, tx1, ty0, ty1, tz = geo[-1]
for x in range(tx0 + 1, tx1 - 1, 2):
    add("guitar-tower", (1, 1, 1), (x, ty0, tz + 3), "light-gray", shape="round")

# ---------------- Section 4: villas (slope roofs) ----------------
VILLA_XS = list(range(2, 44, 8))
first_villa = True
for vy in [18, 24]:
    for vx in VILLA_XS:
        fill("villas", vx, vy, 6, 4, 1, 3, "tan",
             note="Villas get sloped shed roofs and white upper stories." if first_villa else None)
        fill("villas", vx, vy, 6, 4, 4, 3, "white")
        fill("villas", vx, vy, 6, 3, 7, 1, "brown")
        for k in range(3):
            add("villas", (2, 1, 3), (vx + 2 * k, vy + 3, 7), "brown", shape="slope")
        first_villa = False

# ---------------- Section 5: lagoon, palms & hedges ----------------
fill("lagoon", 2, 33, 44, 3, 0, 1, "azure",
     note="Lagoon base with a trans-clear tile water surface, palms, and hedge rows.")
fill("lagoon", 2, 33, 44, 3, 1, 1, "trans-clear", shape="tile")
for x in range(4, 44, 6):
    add("lagoon", (2, 2, 1), (x, 31, 0), "sand-green")
for px in [7, 13, 19, 25, 31, 37]:
    for k in range(3):
        add("lagoon", (1, 1, 3), (px, 31, k * 3), "reddish-brown", shape="round",
            note="Palm: stacked round-brick trunk + foliage canopy (BrickLink Plant cats 25/95)." if px == 7 and k == 0 else None)
    add("lagoon", (2, 2, 3), (px, 31, 9), "green", shape="foliage")
for hx in range(1, 45, 4):
    add("lagoon", (2, 2, 3), (hx, 16, 1), "dark-green", shape="foliage")

build = {
    "title": "Rockwater Resort & Guitar Tower — Detailed",
    "subtitle": "Glass curtain walls, inset strings, fretboard, cheese-slope contours, palms & hedges — real specialized parts throughout",
    "author": "Max",
    "sections": [
        {"id": "podium", "title": "Podium", "note": "48x28 ground deck for the whole resort."},
        {"id": "hotel-wing", "title": "Hotel Wing", "note": "7-story wing with glass ribbon facade and tile cornice."},
        {"id": "guitar-tower", "title": "Guitar Tower", "note": "Blue-glass skin, six inset strings, black fretboard, cheese-slope shoulders."},
        {"id": "villas", "title": "Villa Grid", "note": "16 cabanas with sloped shed roofs."},
        {"id": "lagoon", "title": "Lagoon & Palms", "note": "Water tiles, 6 palms, hedge rows."},
    ],
    "bricks": bricks,
}
json.dump(build, open("rockwater-detailed.build.json", "w"), indent=2)
print("bricks:", len(bricks))
