# JapanOrace-Daten

Datenpaket für das Reisespiel JapanOrace. Ein GitHub-Ablauf lädt den OpenStreetMap-Auszug für Japan von Geofabrik, filtert die Orte der elf Spielkategorien, Bahnhöfe, Haltestellen und Unterkünfte, dünnt dichte Gebiete räumlich aus und legt alles als Kacheln auf GitHub Pages ab.

## Neu bauen

Reiter **Actions** → **Daten bauen** → **Run workflow**. Der Bau dauert etwa 15–30 Minuten.

## Inhalt

| Datei | Inhalt |
| --- | --- |
| `tiles/<y>_<x>.json` | Orte je Kachel von 0,25° × 0,25° |
| `stations.json` | alle Bahnhöfe Japans, Schnellfahr-Bahnhöfe markiert |
| `municipalities.json` | 1.707 Gemeinden mit Lesung, Einwohnern, Fläche, Lage |
| `index.json` | Kachelliste, Kennzahlen, Typtabelle (`types`) und Kettenzählung |
| `chains.json` | je Kette ein Ladenfoto mit Urheber, Lizenz und Quelle |
| `img/chains/<id>.jpg` | die Ladenfotos (480 px) |

### Kachelzeilen (Format 2)

`[Kürzel, Breite·1e5, Länge·1e5, Name, Lateinname, Kana, Wikidata, Höhe, Flags, Typ-Index, Kette]`

Der Typ-Index zeigt in `index.json → types` (z. B. `shrine`, `konbini`, `harbour`). Die Kette ist die `id` aus `data/chains.json`. Format-1-Leser ignorieren die beiden letzten Felder.

## Ketten pflegen

`data/chains.json` listet die erkannten Ketten. `match` sind Namensbestandteile, `kinds` die erlaubten Ortstypen, `search` die Commons-Suche für das Foto. Passt ein Foto nicht, trägt man unter `file` einen festen Commons-Dateinamen ein. Logo-Dateien werden nie genommen.

## Quellen

- © OpenStreetMap-Mitwirkende, Lizenz ODbL, Auszug von Geofabrik
- Gemeinden: Wikidata, CC0
- Ladenfotos: Wikimedia Commons, Urheber und Lizenz je Bild in `chains.json`
