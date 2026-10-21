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
| `index.json` | Kachelliste und Kennzahlen |

## Quellen

- © OpenStreetMap-Mitwirkende, Lizenz ODbL, Auszug von Geofabrik
- Gemeinden: Wikidata, CC0
