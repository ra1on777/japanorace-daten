#!/usr/bin/env python3
"""Gemeinde-Raster je Kachel aus den OSM-Gemeindegrenzen (admin_level=7).

Ohne Zusatzbibliotheken: Jede Grenze wird zeilenweise gerastert (Scanline, gerade/ungerade
Regel, damit Löcher und Inseln stimmen). Zelle 0,005° ≈ 550 × 400 m, Zellmitte entscheidet.

Eingabe:  GeoJSON-Sequenz der Grenzen, data/municipalities.json, fertiger Kachelordner
Ausgabe:  jede Kachel bekommt
            "gq": [null, "Q123", ...]   Gemeinden der Kachel (Wikidata), 0 = keine (Meer)
            "g":  [i, n, i, n, ...]     Lauflängen über 50 × 50 Zellen, Zeile für Zeile von Süd nach Nord
Prüfpunkte (Name → Gemeinde) werden ausgegeben.
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

TILE = 0.25
CELL = 0.005
N = round(TILE / CELL)   # 50 Zellen je Kachelseite


def rings_of(geom):
    t, c = geom['type'], geom['coordinates']
    if t == 'Polygon':
        return c
    if t == 'MultiPolygon':
        return [r for poly in c for r in poly]
    return []


def raster(rings, put):
    """Alle Zellmitten innerhalb der Ringe → put(row, col) mit globalen Zellindizes."""
    cross = defaultdict(list)
    for ring in rings:
        for k in range(len(ring) - 1):
            (x1, y1), (x2, y2) = ring[k][:2], ring[k + 1][:2]
            if y1 == y2:
                continue
            if y1 > y2:
                x1, y1, x2, y2 = x2, y2, x1, y1
            r0 = math.ceil(y1 / CELL - 0.5)          # erste Zeile, deren Mitte ≥ y1
            r1 = math.ceil(y2 / CELL - 0.5) - 1      # letzte Zeile, deren Mitte < y2
            for r in range(r0, r1 + 1):
                yc = (r + 0.5) * CELL
                cross[r].append(x1 + (yc - y1) * (x2 - x1) / (y2 - y1))
    for r, xs in cross.items():
        xs.sort()
        for a, b in zip(xs[0::2], xs[1::2]):
            c0 = math.ceil(a / CELL - 0.5)
            c1 = math.ceil(b / CELL - 0.5) - 1
            for c in range(c0, c1 + 1):
                put(r, c)


def main(src, munis_path, tiles_dir, checks=None):
    known = {r[0] for r in json.load(open(munis_path, encoding='utf-8'))['rows']}
    grid = {}          # (row, col) -> qid
    matched, skipped = set(), 0
    with open(src, encoding='utf-8') as f:
        for line in f:
            line = line.strip().lstrip('\x1e')
            if not line:
                continue
            feat = json.loads(line)
            p = feat.get('properties') or {}
            q = p.get('wikidata')
            if p.get('admin_level') != '7' or q not in known:
                skipped += 1
                continue
            matched.add(q)
            def put(r, c, q=q):
                grid[(r, c)] = q
            raster(rings_of(feat['geometry']), put)
    print(f'{len(matched)} von {len(known)} Gemeinden mit Grenze, {skipped} Objekte übersprungen, {len(grid)} Landzellen', flush=True)

    tiles = Path(tiles_dir)
    added = 0
    for fp in tiles.glob('*.json'):
        d = json.load(open(fp, encoding='utf-8'))
        ty, tx = d['y'], d['x']
        qs, idx, runs = [None], {None: 0}, []
        last, n = None, 0
        for i in range(N):
            for j in range(N):
                q = grid.get((ty * N + i, tx * N + j))
                if q not in idx:
                    idx[q] = len(qs)
                    qs.append(q)
                v = idx[q]
                if v == last:
                    n += 1
                else:
                    if last is not None:
                        runs += [last, n]
                    last, n = v, 1
        runs += [last, n]
        if len(qs) == 1:
            continue          # ganz Meer oder ohne Grenze
        before = fp.stat().st_size
        d['gq'], d['g'] = qs, runs
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, separators=(',', ':'))
        added += fp.stat().st_size - before
    print(f'Raster: +{added / 1e6:.2f} MB über alle Kacheln', flush=True)

    # Prüfpunkte: Orte nach Namen suchen und Gemeinde melden
    out = []
    if checks:
        names = json.load(open(munis_path, encoding='utf-8'))['rows']
        qname = {r[0]: r[1] for r in names}
        for fp in tiles.glob('*.json'):
            d = json.load(open(fp, encoding='utf-8'))
            for row in d['r']:
                if row[3] in checks:
                    lat, lon = row[1] / 1e5, row[2] / 1e5
                    q = grid.get((math.floor(lat / CELL), math.floor(lon / CELL)))
                    out.append(f'{row[3]} ({lat:.4f}, {lon:.4f}) → {qname.get(q, q)}')
    stats = {'munis_with_boundary': len(matched), 'munis_total': len(known), 'cells': len(grid), 'bytes_added': added, 'checks': out}
    print(json.dumps(stats, ensure_ascii=False), flush=True)
    return stats


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(',') if len(sys.argv) > 4 else None)
