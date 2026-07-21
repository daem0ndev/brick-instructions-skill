#!/usr/bin/env python3
"""rockwater-true-shape.build.json — TRUE-SHAPE Guitar Hotel from multi-angle reference study.

Key shape corrections vs earlier attempts (from the construction photo + aerial
render): the building is a guitar BODY ONLY — a constant-depth glass slab whose
WIDTH follows the body outline (round lower bout → deep waist → upper bout →
shoulders), with a center NOTCH at the top where two clusters of thin masts
(the "headstocks" of the back-to-back guitars) rise. The strings are a tight
vertical stripe up the center of the face; floors read as thin white horizontal
lines across light-blue glass.
"""
import json, math

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

def fill(section, x0, y0, w, d, z, h, color, shape=None, note=None, chunks=(2, 1)):
    first = True
    yy = 0
    for dy in dec(d, (2, 1)):
        xx = 0
        for dx in dec(w, chunks):
            add(section, (dx, dy, h), (x0 + xx, y0 + yy, z), color, shape=shape,
                note=note if first else None)
            first = False
            xx += dx
        yy += dy

# ---------------- Section 1: podium ----------------
PW, PD = 64, 30
fill("podium", 0, 0, PW, PD, 0, 1, "light-gray", chunks=(4, 2, 1),
     note="Lay the full 64x30 podium first — everything keys off its top surface (z=1).")

# ---------------- Section 2: hotel wing (unchanged pattern, 7 stories) ----------------
WX, WY, WW, WD = 0, 0, 24, 16
STORY = 3
STORIES = 7
for s in range(STORIES):
    z = 1 + s * STORY
    color = "light-gray" if s < 3 else "white"
    if s == 0:
        fill("hotel-wing", WX, WY, WW, WD, z, STORY, color, chunks=(4, 2, 1),
             note="Ground story solid; upper stories carry the glass ribbon on the street faces.")
        continue
    fill("hotel-wing", WX, WY, WW - 1, WD - 1, z, STORY, color, chunks=(4, 2, 1))
    xx = 0
    for dx in dec(WW):
        add("hotel-wing", (dx, 1, STORY), (WX + xx, WY + WD - 1, z), "trans-light-blue")
        xx += dx
    yy = 0
    for dy in dec(WD - 1):
        add("hotel-wing", (1, dy, STORY), (WX + WW - 1, WY + yy, z), "trans-light-blue")
        yy += dy
fill("hotel-wing", WX, WY, WW, WD, 1 + STORIES * STORY, 1, "white", chunks=(4, 2, 1))
zr = 2 + STORIES * STORY
xx = 0
for dx in dec(WW):
    add("hotel-wing", (dx, 1, 1), (WX + xx, WY + WD - 1, zr), "white", shape="tile")
    xx += dx

# ---------------- Section 3: guitar tower — true body outline ----------------
CX, TY, DEPTH = 45, 4, 8
N = 46                      # body bands (x3 plates)
NOTCH = 5                   # top bands carrying the center notch
GAPS = [1, 2, 3, 4, 4]      # notch half-gap per notch band
STRING_XS = list(range(CX - 3, CX + 3))  # tight 6-wide string stripe up the center

# half-width control points (t along height, half-width in studs)
CTRL = [(0.00, 12), (0.10, 16), (0.24, 17), (0.42, 12.5), (0.52, 10),
        (0.62, 12), (0.74, 13), (0.88, 11), (1.00, 8)]

def hw_at(t):
    for k in range(len(CTRL) - 1):
        t0, v0 = CTRL[k]
        t1, v1 = CTRL[k + 1]
        if t0 <= t <= t1:
            u = (t - t0) / (t1 - t0)
            return v0 + (v1 - v0) * (1 - math.cos(u * math.pi)) / 2
    return CTRL[-1][1]

halfw = []
for i in range(N):
    hw = round(hw_at(i / (N - 1)))
    if halfw:
        hw = max(halfw[-1] - 1, min(halfw[-1] + 1, hw))  # clamp ±1/side per band
    halfw.append(hw)

geo = []
z = 1
for i in range(N):
    hw = halfw[i]
    x0, x1 = CX - hw, CX + hw
    y0 = TY
    w, d = 2 * hw, DEPTH
    y1 = y0 + d
    geo.append((x0, x1, y0, y1, z))
    notch_j = i - (N - NOTCH)
    gap = GAPS[notch_j] if notch_j >= 0 else 0
    runs = [(x0, x1)] if gap == 0 else [(x0, CX - gap), (CX + gap, x1)]
    prev = geo[i - 1] if i > 0 else None
    exp_l = prev is not None and x0 < prev[0]
    exp_r = prev is not None and x1 > prev[1]
    note = None
    if i == 0:
        note = "Body base — the tower is a constant-depth glass slab whose width follows the guitar-body outline."
    elif i == 11:
        note = "Lower bout at maximum width."
    elif i == 24:
        note = "Waist: the deep pinch that defines the silhouette."
    elif i == N - NOTCH:
        note = "Top notch begins — the face splits around the neck heel, where the mast clusters will stand."
    # VIEWER-FACING face: in this projection the camera sees the +y and +x
    # faces, so the detailed skin (glass, spandrels, strings) lives on the
    # y1-1 row. Bond courses (2-deep) at expansions tie that skin into the
    # mass; column back-fills keep no hollow pockets under later bands.
    FY = y1 - 1
    if exp_l:
        add("guitar-tower", (2, 2, 3), (x0, FY - 1, z), "white")
        fill("guitar-tower", x0, y0, 2, d - 2, z, 3, "white")
    if exp_r:
        add("guitar-tower", (2, 2, 3), (x1 - 2, FY - 1, z), "white")
        fill("guitar-tower", x1 - 2, y0, 2, d - 2, z, 3, "white")
    for (r0, r1) in runs:
        f0 = r0 + (2 if exp_l and r0 == x0 else 0)
        f1 = r1 - (2 if exp_r and r1 == x1 else 0)
        # front face: 2-plate glass + 1-plate white spandrel line (floor banding),
        # with trans-clear round "strings" inset full-height at the center stripe
        xcur = f0
        while xcur < f1:
            if gap == 0 and xcur in STRING_XS:
                add("guitar-tower", (1, 1, 3), (xcur, FY, z), "light-gray", shape="round",
                    note=note if xcur == f0 else None)
                xcur += 1
            else:
                nxt = f1
                if gap == 0:
                    for sx in STRING_XS:
                        if xcur < sx < nxt:
                            nxt = sx
                run = nxt - xcur
                chunks = dec(run)
                if nxt == f1:
                    chunks = list(reversed(chunks))
                for dx in chunks:
                    add("guitar-tower", (dx, 1, 2), (xcur, FY, z), "trans-light-blue",
                        note=note if xcur == f0 else None)
                    add("guitar-tower", (dx, 1, 1), (xcur, FY, z + 2), "white")
                    note = None
                    xcur += dx
        note = None
        # interior core (rows y0..FY-1) + right-side glazing
        i0 = r0 + (2 if exp_l and r0 == x0 else 0)
        i1 = r1 - (2 if exp_r and r1 == x1 else (1 if r1 == x1 and not exp_r else 0))
        if r1 == x1 and not exp_r:
            yy = y0
            for dy in dec(FY - y0):
                add("guitar-tower", (1, dy, 3), (x1 - 1, yy, z), "trans-light-blue")
                yy += dy
        if i1 > i0:
            fill("guitar-tower", i0, y0, i1 - i0, d - 1, z, 3, "white", chunks=(4, 2, 1))
    # cheese slopes soften every contraction step on the front edge
    if i + 1 < N:
        n_hw = halfw[i + 1]
        if n_hw < hw:
            top = z + 3
            for x in range(x0, CX - n_hw):
                add("guitar-tower", (1, 1, 2), (x, TY + DEPTH - 1, top), "trans-light-blue", shape="cheese")
            for x in range(CX + n_hw, x1):
                add("guitar-tower", (1, 1, 2), (x, TY + DEPTH - 1, top), "trans-light-blue", shape="cheese")
    z += 3
# mast clusters ("headstocks" of the back-to-back guitars) on the notch shoulders
mz = geo[-1][4] + 3
for cluster in [range(CX - 7, CX - 4), range(CX + 4, CX + 7)]:
    for x in cluster:
        for k in range(5):
            add("guitar-tower", (1, 1, 3), (x, TY + 3, mz + k * 3), "light-gray", shape="round",
                note="Mast cluster — the thin spires that read as the guitars' headstocks." if x == CX - 7 and k == 0 else None)

# ---------------- Section 4: villas ----------------
first_villa = True
for vy in [18, 24]:
    for vx in range(2, 60, 8):
        if 26 <= vx <= 62 and vy == 18:
            pass  # villas run under the tower's south side is fine — tower starts at y4..12
        fill("villas", vx, vy, 6, 4, 1, 3, "tan",
             note="16 cabanas with sloped shed roofs." if first_villa else None)
        fill("villas", vx, vy, 6, 4, 4, 3, "white")
        fill("villas", vx, vy, 6, 3, 7, 1, "brown")
        for k in range(3):
            add("villas", (2, 1, 3), (vx + 2 * k, vy + 3, 7), "brown", shape="slope")
        first_villa = False

# ---------------- Section 5: lagoon, palms & hedges ----------------
fill("lagoon", 2, 35, 60, 3, 0, 1, "azure",
     note="Lagoon with trans-clear water tiles, 8 palms, hedge rows.")
fill("lagoon", 2, 35, 60, 3, 1, 1, "trans-clear", shape="tile")
for x in range(4, 60, 7):
    add("lagoon", (2, 2, 1), (x, 33, 0), "sand-green")
for px in [7, 14, 21, 28, 35, 42, 49, 56]:
    for k in range(3):
        add("lagoon", (1, 1, 3), (px, 33, k * 3), "reddish-brown", shape="round")
    add("lagoon", (2, 2, 3), (px, 33, 9), "green", shape="foliage")
for hx in range(1, 61, 4):
    add("lagoon", (2, 2, 3), (hx, 16, 1), "dark-green", shape="foliage")

build = {
    "title": "Rockwater Guitar Hotel",
    "subtitle": "Body-only slab with real guitar outline, center notch + mast headstocks, string stripe, floor-line glass banding",
    "author": "Max",
    "sections": [
        {"id": "podium", "title": "Podium", "note": "64x30 ground deck."},
        {"id": "hotel-wing", "title": "Hotel Wing", "note": "7-story glass-ribbon wing."},
        {"id": "guitar-tower", "title": "Guitar Tower", "note": "46-band body outline, notch + masts, strings, floor banding."},
        {"id": "villas", "title": "Villa Grid", "note": "16 cabanas, sloped roofs."},
        {"id": "lagoon", "title": "Lagoon & Palms", "note": "Water tiles, 8 palms, hedges."},
    ],
    "bricks": bricks,
}
json.dump(build, open("rockwater-true-shape.build.json", "w"), indent=2)
print("bricks:", len(bricks))
