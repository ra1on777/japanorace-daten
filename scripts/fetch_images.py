#!/usr/bin/env python3
"""Holt je Kette ein freies Ladenfoto von Wikimedia Commons (keine Logo-Dateien).

Eingabe:  data/chains.json
Ausgabe:  <out>/img/chains/<id>.jpg  (Vorschaubild, 480 px breit)
          <out>/chains.json          Kette -> Bild, Urheber, Lizenz, Quelle

Fehler bei einzelnen Ketten brechen den Bau nicht ab; die Kette hat dann kein Foto
und das Spiel zeigt die Kategorie-Illustration.
"""
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = 'https://commons.wikimedia.org/w/api.php'
UA = 'JapanOrace-Daten/1.0 (https://github.com/ra1on777/japanorace-daten)'
BAD = re.compile(r'logo|signboard|icon|symbol|\bmap\b|menu|receipt|card|bag|package|wrapper|bottle|seal|stamp|product|beverage|display|\.svg', re.I)
# Fotos aus dem Ausland ausschließen: Das Spiel zeigt Japan
ABROAD = re.compile(r'jakarta|\bjkt\b|indonesia|china|chinese|shanghai|beijing|guangzhou|shenzhen|hong ?kong|taiwan|taipei|korea|seoul|thailand|bangkok|philippines|manila|vietnam|hanoi|singapore|malaysia|hawaii|\busa\b|california|new york|canada|london|australia|cambodia|myanmar|\bindia\b|dubai', re.I)
STORE = re.compile(r'store|shop|branch|restaurant|hotel|mall|店|exterior|facade|façade', re.I)
FREE = re.compile(r'^(cc[ -]by|cc0|public domain|pd)', re.I)


def get(params):
    params = dict(params, format='json', formatversion=2)
    url = API + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def plain(s):
    s = re.sub(r'<[^>]+>', '', s or '')
    return html.unescape(s).strip()


def norm(s):
    return re.sub(r'[\s\-‐・_.,!！&＆()（）]', '', (s or '').lower())


def infos(titles):
    d = get({'action': 'query', 'titles': '|'.join(titles), 'prop': 'imageinfo',
             'iiprop': 'url|mime|size|extmetadata', 'iiurlwidth': 480})
    out = {}
    for p in d.get('query', {}).get('pages', []):
        ii = (p.get('imageinfo') or [None])[0]
        if ii:
            out[p['title']] = ii
    return out


def acceptable(title, ii, keys):
    if ii.get('mime') != 'image/jpeg' or BAD.search(title) or ABROAD.search(title):
        return False
    if ii.get('width', 0) < 400 or ii.get('height', 0) > ii.get('width', 1) * 1.3:
        return False
    meta = ii.get('extmetadata') or {}
    lic = plain((meta.get('LicenseShortName') or {}).get('value'))
    if not FREE.search(lic):
        return False
    t = norm(title)
    return any(k in t for k in keys)


def pick(chain):
    keys = {norm(chain['en']), norm(chain['ja'])} | {norm(m) for m in chain['match'] if len(norm(m)) >= 3}
    keys.discard('')
    if chain.get('file'):
        cands = ['File:' + chain['file'].removeprefix('File:')]
        keys = {''}
    else:
        cands = []
        searches = chain['search'] if isinstance(chain['search'], list) else [chain['search']]
        for q in searches:
            d = get({'action': 'query', 'list': 'search', 'srnamespace': 6, 'srlimit': 30, 'srsearch': q})
            cands += [r['title'] for r in d.get('query', {}).get('search', []) if r['title'] not in cands]
    if not cands:
        return None
    ii = {}
    for i in range(0, len(cands), 40):
        ii.update(infos(cands[i:i + 40]))
    ok = [t for t in cands if t in ii and acceptable(t, ii[t], keys)]
    if not ok:
        return None
    # Ladenansichten bevorzugen, sonst Suchreihenfolge
    ok.sort(key=lambda t: (0 if STORE.search(t) else 1, cands.index(t)))
    return ok[0], ii[ok[0]]


def main(chains_path, outdir):
    out = Path(outdir)
    (out / 'img' / 'chains').mkdir(parents=True, exist_ok=True)
    chains = json.load(open(chains_path, encoding='utf-8'))['chains']
    result = {}
    for c in chains:
        try:
            hit = pick(c)
            if not hit:
                print(f'{c["id"]}: kein passendes Foto', flush=True)
                continue
            title, ii = hit
            meta = ii.get('extmetadata') or {}
            req = urllib.request.Request(ii['thumburl'], headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                (out / 'img' / 'chains' / f'{c["id"]}.jpg').write_bytes(r.read())
            result[c['id']] = {
                'img': f'img/chains/{c["id"]}.jpg',
                'file': title.removeprefix('File:'),
                'page': ii.get('descriptionurl'),
                'artist': plain((meta.get('Artist') or {}).get('value'))[:120] or 'unbekannt',
                'license': plain((meta.get('LicenseShortName') or {}).get('value')),
                'licenseUrl': plain((meta.get('LicenseUrl') or {}).get('value')) or None,
            }
            print(f'{c["id"]}: {title}', flush=True)
        except Exception as e:  # einzelne Kette darf scheitern
            print(f'{c["id"]}: Fehler {e}', flush=True)
        time.sleep(0.5)
    with open(out / 'chains.json', 'w', encoding='utf-8') as f:
        json.dump({'v': 1, 'built': time.strftime('%Y-%m-%d'), 'chains': result}, f, ensure_ascii=False, indent=1)
    print(f'{len(result)} von {len(chains)} Ketten mit Foto', flush=True)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
