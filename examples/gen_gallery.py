#!/usr/bin/env python3
"""Gallery examples for the README: three small-but-charming builds that
exercise the specialized part vocabulary (windows, fence panels, slope roofs,
sails, curved-slope tapers, rounds, foliage, trans glass/water)."""
import json

def build_writer(name, title, subtitle):
    bricks = []
    def add(size, pos, color, shape=None, rot=None, note=None):
        b = {"size": list(size), "pos": list(pos), "color": color}
        if shape: b["shape"] = shape
        if rot: b["rot"] = rot
        if note: b["note"] = note
        bricks.append(b)
    def fill(x0, y0, w, d, z, h, color, shape=None):
        yy = 0
        while yy < d:
            dy = 2 if d - yy >= 2 else 1
            xx = 0
            while xx < w:
                dx = 2 if w - xx >= 2 else 1
                add((dx, dy, h), (x0 + xx, y0 + yy, z), color, shape=shape)
                xx += dx
            yy += dy
    def save():
        json.dump({"title": title, "subtitle": subtitle, "author": "Max", "bricks": bricks},
                  open(name, "w"), indent=1)
        print(name, len(bricks))
    return add, fill, save

# ---------------- Cottage ----------------
add, fill, save = build_writer("gallery-cottage.build.json", "Brookside Cottage",
                               "Slope roof, glass windows, fenced garden")
fill(0, 0, 16, 12, 0, 1, "green")                      # grass base
# house block x3..13, y2..10; front face row y=9
for z in (1, 4):
    # back + middle rows solid
    fill(3, 2, 10, 7, z, 3, "tan")
    # front row y=9 custom: door (z1..7) at x7..9, windows (z4) at x4..6 / x10..12
    if z == 1:
        add((2, 1, 6), (7, 9, 1), "reddish-brown", note="Front door spans both wall courses.")
        for seg in [(3, 4), (9, 1), (10, 2), (12, 1)]:
            add((seg[1], 1, 3), (seg[0], 9, 1), "tan")
    else:
        add((1, 1, 3), (3, 9, 4), "tan")
        add((2, 1, 3), (4, 9, 4), "trans-light-blue", shape="window")
        add((1, 1, 3), (6, 9, 4), "tan")
        add((1, 1, 3), (9, 9, 4), "tan")
        add((2, 1, 3), (10, 9, 4), "trans-light-blue", shape="window")
        add((1, 1, 3), (12, 9, 4), "tan")
# saltbox roof: 4 levels, brown slopes on the front edge, ridge tiles on top
for k in range(4):
    z = 7 + 3 * k
    fill(3, 2, 10, 7 - k, z, 3, "brown")
    for sx in range(3, 13, 2):
        add((2, 1, 3), (sx, 9 - k, z), "brown", shape="slope")
fill(3, 2, 10, 3, 19, 1, "brown", shape="tile")        # ridge cap
add((2, 2, 3), (4, 3, 20), "light-gray")               # chimney
add((1, 1, 1), (4, 3, 23), "light-gray", shape="round")
# garden: path, fence with gate gap, hedges, flowers
for py in (10, 11):
    add((2, 1, 1), (7, py, 1), "tan", shape="tile")
for fx in range(0, 16, 2):
    if fx not in (6, 8):
        add((2, 1, 3), (fx, 11, 1), "white", shape="panel")
for fy in range(0, 10, 2):
    add((1, 2, 3), (15, fy, 1), "white", shape="panel")
add((2, 2, 3), (0, 8, 1), "dark-green", shape="foliage")
add((2, 2, 3), (13, 8, 1), "dark-green", shape="foliage")
for fx, c in [(1, "red"), (2, "yellow"), (13, "yellow"), (14, "red")]:
    add((1, 1, 1), (fx, 10, 1), c, shape="round")
save()

# ---------------- Sailboat ----------------
add, fill, save = build_writer("gallery-sailboat.build.json", "Trade Wind Sloop",
                               "Slope bow, staircase mainsail, glass water")
fill(0, 0, 20, 10, 0, 1, "azure")                      # sea
for x0, w in [(0, 4), (18, 2)]:                        # visible water sheen patches
    fill(x0, 6, w, 4, 1, 1, "trans-clear", shape="tile")
fill(4, 3, 12, 5, 1, 3, "red")                         # hull lower
fill(4, 3, 12, 5, 4, 3, "red")                         # hull upper
add((4, 2, 3), (16, 3, 1), "red", rot=90, shape="slope", note="Bow tapers with a rotated slope.")
add((4, 2, 3), (16, 3, 4), "red", rot=90, shape="slope")
fill(4, 3, 12, 5, 7, 1, "tan", shape="tile")           # deck
add((3, 2, 3), (5, 4, 8), "white")                     # cabin
add((2, 1, 3), (5, 6, 8), "trans-light-blue", shape="window")
for k in range(6):                                     # mast
    add((1, 1, 3), (9, 6, 8 + 3 * k), "reddish-brown", shape="round")
widths = [6, 5, 4, 3, 2]                               # staircase mainsail
for i, w in enumerate(widths):
    add((w, 1, 3), (10, 7, 8 + 3 * i), "white", note="Mainsail: rows shrink as they climb." if i == 0 else None)
add((1, 1, 2), (9, 6, 26), "red", shape="cheese")      # pennant
save()

# ---------------- Rocket ----------------
add, fill, save = build_writer("gallery-rocket.build.json", "Redline Rocket",
                               "Curved-slope taper, porthole glass, fin slopes")
fill(0, 0, 12, 12, 0, 1, "light-gray")                 # pad
for tx in range(0, 12, 2):                             # scorch ring tiles
    add((2, 1, 1), (tx, 10, 1), "dark-gray", shape="tile")
    add((2, 1, 1), (tx, 0, 1), "dark-gray", shape="tile")
for c in range(7):                                     # body: 7 courses of 4x4
    z = 1 + 3 * c
    color = "red" if c == 3 else "white"
    if c in (2, 4):
        fill(4, 4, 4, 3, z, 3, color)                  # rows y4..6
        add((1, 1, 3), (4, 7, z), color)
        add((1, 1, 3), (5, 7, z), "trans-light-blue", shape="round", note="Porthole: glass round inset in the hull." if c == 2 else None)
        add((2, 1, 3), (6, 7, z), color)
    else:
        fill(4, 4, 4, 4, z, 3, color)
Z = 22
add((2, 1, 2), (4, 7, Z), "red", shape="curved")       # shoulder taper, front
add((2, 1, 2), (6, 7, Z), "red", shape="curved")
add((1, 2, 2), (7, 4, Z), "red", shape="curved", rot=90)
add((1, 1, 2), (7, 6, Z), "red", shape="cheese")
fill(4, 4, 3, 3, Z, 2, "white")
add((2, 2, 3), (5, 5, 24), "red")                      # neck
add((2, 2, 3), (5, 5, 27), "red")
add((2, 2, 3), (5, 5, 30), "red", shape="slope")       # nose
add((2, 1, 3), (5, 8, 1), "red", shape="slope")        # front fin
add((2, 2, 3), (8, 5, 1), "red", shape="slope", rot=90)  # right fin
save()
