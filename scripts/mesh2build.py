#!/usr/bin/env python3
"""Convert BrickGPT mesh2brick text output into a build.json skeleton.

Input format (one brick per line): `HxW (x,y,z)` where H is the footprint
length along x, W along y, and z is the brick layer (each layer = one brick
height = 3 plates). Produces an all-brick massing draft; apply colors, glass,
and shapes in a detail pass afterward. See references/mesh-input.md.

Usage: mesh2build.py bricks.txt out.build.json --title "Name" [--color "#7B3FA0"]
"""
import argparse
import json
import re

PAT = re.compile(r'(\d+)x(\d+) \((\d+),(\d+),(\d+)\)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input_txt')
    ap.add_argument('output_json')
    ap.add_argument('--title', default='Mesh Import')
    ap.add_argument('--subtitle', default='Converted from a 3D mesh via mesh2brick')
    ap.add_argument('--color', default='#7B3FA0', help='body color for all bricks')
    ap.add_argument('--base-color', default='black',
                    help='color for layer-0 bricks (often wheels/foundation)')
    args = ap.parse_args()

    bricks = []
    for line in open(args.input_txt):
        m = PAT.match(line.strip())
        if not m:
            continue
        h, w, x, y, z = map(int, m.groups())
        bricks.append({
            'size': [h, w, 3],
            'pos': [x, y, z * 3],
            'color': args.base_color if z == 0 else args.color,
        })

    bricks.sort(key=lambda b: (b['pos'][2], b['pos'][1], b['pos'][0]))
    build = {'title': args.title, 'subtitle': args.subtitle, 'bricks': bricks}
    with open(args.output_json, 'w') as f:
        json.dump(build, f, indent=1)
    print(f'{len(bricks)} bricks -> {args.output_json}')
    print('Next: validate, then a detail pass (colors from source materials, '
          'trans-* glass, shape system).')


if __name__ == '__main__':
    main()
