#!/usr/bin/env python3
"""Baut aus dem gefilterten OSM-Export die Kacheln für JapanOrace.

Eingabe: GeoJSON-Sequenz aus `osmium export`.
Ausgabe (Ordner):
  tiles/<ty>_<tx>.json   Orte je Kachel (0,25° × 0,25°), nach Dichte ausgedünnt
  stations.json          alle Bahnhöfe Japans
  index.json             Kachelliste und Kennzahlen

Kürzel je Ort (mehrere möglich):
  Kategorien: o Onsen, a Aussicht, w Wasser, g Geschichte, s Sport, v Verkehr,
              p Park, e Essen, l Alltag, m Gemeinde, t Schrein
  Dienste:    S Bahnhof, B Bushaltestelle, K Snack (Konbini/Automat), M Mahlzeit,
              H Hotel, h Hostel/Minshuku, C Camping, R Fahrradladen, P Gipfel
"""
import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path

TILE = 0.25
# Höchstzahl je Kürzel und Kachel; darüber wird räumlich ausgedünnt
CAPS = {c: 120 for c in 'oawgsvpelmt'}
CAPS.update({'S': 100000, 'B': 500, 'K': 200, 'M': 200, 'H': 60, 'h': 60, 'C': 40, 'R': 40, 'P': 120})


def classify(t):
    out = set()
    g = t.get
    named = bool(g('name'))
    am, tou, nat, lei, shop = g('amenity', ''), g('tourism', ''), g('natural', ''), g('leisure', ''), g('shop', '')
    if am == 'public_bath' or (nat == 'hot_spring' and named) or (lei == 'swimming_pool' and named and g('access') != 'private'):
        out.add('o')
    if tou == 'viewpoint' or (nat == 'peak' and named) or (g('mountain_pass') == 'yes' and named):
        out.add('a')
    if named and (nat == 'beach' or g('waterway') in ('waterfall', 'dam') or (nat == 'water' and g('water') in ('lake', 'reservoir', 'pond'))):
        out.add('w')
    if named and (tou == 'museum' or g('historic') in ('castle', 'monument', 'memorial', 'archaeological_site', 'ruins', 'fort')):
        out.add('g')
    if named and lei in ('stadium', 'sports_centre', 'golf_course', 'amusement_arcade', 'pitch', 'track'):
        out.add('s')
    if (named and (g('railway') == 'station' or g('man_made') in ('bridge', 'lighthouse') or g('landuse') == 'harbour' or g('aeroway') == 'aerodrome')) or am == 'ferry_terminal':
        out.add('v')
    if named and (lei in ('park', 'garden') or tou == 'camp_site'):
        out.add('p')
    if named and (am in ('restaurant', 'cafe', 'fast_food') or shop in ('bakery', 'confectionery', 'pastry')):
        out.add('e')
    if named and (shop in ('convenience', 'supermarket', 'mall', 'department_store') or am in ('post_office', 'marketplace')):
        out.add('l')
    if named and am in ('townhall', 'library', 'community_centre', 'school', 'college', 'university'):
        out.add('m')
    if named and am == 'place_of_worship':
        out.add('t')
    # Dienste
    if g('railway') in ('station', 'halt') and named:
        out.add('S')
    if g('highway') == 'bus_stop':
        out.add('B')
    if shop == 'convenience' or am == 'vending_machine':
        out.add('K')
    if am in ('restaurant', 'fast_food', 'cafe'):
        out.add('M')
    if tou == 'hotel':
        out.add('H')
    if tou in ('guest_house', 'hostel', 'motel'):
        out.add('h')
    if tou == 'camp_site':
        out.add('C')
    if shop == 'bicycle':
        out.add('R')
    if nat == 'peak' and named:
        out.add('P')
    return out


def point_of(geom):
    t, c = geom['type'], geom['coordinates']
    if t == 'Point':
        return c[1], c[0]
    if t == 'LineString':
        m = c[len(c) // 2]
        return m[1], m[0]
    if t == 'Polygon':
        ring = c[0]
    elif t == 'MultiPolygon':
        ring = max((p[0] for p in c), key=len)
    else:
        return None
    n = len(ring) - 1 if len(ring) > 1 and ring[0] == ring[-1] else len(ring)
    lon = sum(p[0] for p in ring[:n]) / n
    lat = sum(p[1] for p in ring[:n]) / n
    return lat, lon


def latin(t):
    for k in ('name:ja-Latn', 'name:ja_rm', 'name:en'):
        if t.get(k):
            return t[k]
    return None


def kana(t):
    for k in ('name:ja-Hira', 'name:ja_kana'):
        if t.get(k):
            return t[k]
    return None


def quality(it):
    # bevorzugt beim Ausdünnen: Wikidata, Lateinname, Name
    return (1 if it['q'] else 0) * 4 + (1 if it['lt'] else 0) * 2 + (1 if it['n'] else 0)


def thin(items, cap):
    if len(items) <= cap:
        return items
    cell = 0.002
    while True:
        best = {}
        for it in items:
            k = (math.floor(it['lat'] / cell), math.floor(it['lon'] / cell))
            if k not in best or quality(it) > quality(best[k]):
                best[k] = it
        if len(best) <= cap:
            return list(best.values())
        cell *= 1.5


def main(src, outdir):
    t0 = time.time()
    out = Path(outdir)
    (out / 'tiles').mkdir(parents=True, exist_ok=True)
    hs = set()          # Rasterzellen mit Schnellfahrstrecke
    items = []
    n_in = 0
    with open(src, encoding='utf-8') as f:
        for line in f:
            line = line.strip().lstrip('\x1e')
            if not line:
                continue
            n_in += 1
            feat = json.loads(line)
            t = feat.get('properties') or {}
            geom = feat.get('geometry')
            if not geom:
                continue
            if t.get('highspeed') == 'yes' and geom['type'] in ('LineString', 'MultiLineString'):
                lines = [geom['coordinates']] if geom['type'] == 'LineString' else geom['coordinates']
                for ln in lines:
                    for lon, lat in ln:
                        hs.add((math.floor(lat / 0.004), math.floor(lon / 0.004)))
                continue
            codes = classify(t)
            if not codes:
                continue
            p = point_of(geom)
            if not p:
                continue
            ele = None
            if 'P' in codes and t.get('ele'):
                try:
                    ele = round(float(str(t['ele']).replace('m', '').strip()))
                except ValueError:
                    ele = None
            items.append({
                'c': ''.join(sorted(codes)), 'lat': p[0], 'lon': p[1],
                'n': t.get('name') or t.get('brand') or '', 'lt': latin(t), 'k': kana(t),
                'q': t.get('wikidata') or None, 'e': ele,
                'st': 'x' if t.get('railway') == 'halt' else '',
            })
    print(f'{n_in} Objekte gelesen, {len(items)} brauchbar, {len(hs)} Schnellfahr-Zellen', flush=True)

    # Bahnhöfe: Schnellfahr-Bahnhöfe markieren
    stations = []
    for it in items:
        if 'S' in it['c']:
            ky, kx = math.floor(it['lat'] / 0.004), math.floor(it['lon'] / 0.004)
            near = any((ky + dy, kx + dx) in hs for dy in (-1, 0, 1) for dx in (-1, 0, 1))
            it['st'] += 'h' if near else ''
            stations.append([round(it['lat'], 5), round(it['lon'], 5), it['n'], it['lt'], it['k'], it['st']])

    tiles = defaultdict(list)
    for it in items:
        tiles[(math.floor(it['lat'] / TILE), math.floor(it['lon'] / TILE))].append(it)

    index = {}
    total = 0
    for (ty, tx), lst in tiles.items():
        keep = set()
        for code, cap in CAPS.items():
            sub = [it for it in lst if code in it['c']]
            for it in thin(sub, cap):
                keep.add(id(it))
        rows = []
        for it in lst:
            if id(it) not in keep:
                continue
            row = [it['c'], round(it['lat'] * 1e5), round(it['lon'] * 1e5), it['n'], it['lt'], it['k'], it['q'], it['e'], it['st'] or None]
            while row and row[-1] is None:
                row.pop()
            rows.append(row)
        name = f'{ty}_{tx}'
        with open(out / 'tiles' / f'{name}.json', 'w', encoding='utf-8') as f:
            json.dump({'v': 1, 'y': ty, 'x': tx, 'r': rows}, f, ensure_ascii=False, separators=(',', ':'))
        index[name] = len(rows)
        total += len(rows)

    with open(out / 'stations.json', 'w', encoding='utf-8') as f:
        json.dump({'v': 1, 'fields': ['lat', 'lon', 'name', 'latin', 'kana', 'flags'], 'rows': stations}, f, ensure_ascii=False, separators=(',', ':'))
    with open(out / 'index.json', 'w', encoding='utf-8') as f:
        json.dump({'v': 1, 'built': time.strftime('%Y-%m-%d'), 'tile': TILE, 'tiles': index, 'items': total, 'stations': len(stations),
                   'source': 'OpenStreetMap-Mitwirkende (ODbL), Auszug von Geofabrik'}, f, ensure_ascii=False, separators=(',', ':'))
    print(f'{len(index)} Kacheln, {total} Orte, {len(stations)} Bahnhöfe, {time.time() - t0:.0f} s', flush=True)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
