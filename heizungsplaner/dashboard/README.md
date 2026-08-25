# Karten für das Dashboard

Der Heizungsplaner meldet seinen Zustand über MQTT an Home Assistant. Diese
Karten machen daraus eine Übersicht, die man aufs Dashboard legen kann – mit
Partytaste, Störungsanzeige und einer Tabelle aller Räume samt nächstem
Schaltpunkt.

## Einsetzen

Der einfache Weg, ohne Python: den Inhalt von
[`heizungsplaner-karten.yaml`](heizungsplaner-karten.yaml) kopieren und in eine
Ansicht vom Typ *sections* einfügen – Ansicht bearbeiten → Abschnitt hinzufügen
→ Dreipunktmenü → *Im YAML-Editor bearbeiten*.

## Ändern

`karten.py` ist die Quelle: Dort stehen die Jinja-Vorlagen und der Aufbau des
Abschnitts. Nach einer Änderung die YAML-Fassung neu erzeugen:

```
python3 heizungsplaner/dashboard/erzeuge_yaml.py
```

## Eine Übersteuerungsregel im Blick behalten

`regelkarten("sensor.heizungsplaner_raum_wohnzimmer")` liefert eine Karte für
einen Raum mit Übersteuerungsregel:

* **greift die Regel**, steht dort ihr Name, der Zielwert und die gemessene
  Temperatur, mit grünem Akzent;
* **greift sie nicht**, steht dort der Grund – „greift heute nicht – Ferien &
  Feiertage läuft" –, damit man nicht vor einer leeren Stelle steht und rätselt.

Bewusst **keine** `conditional`-Karte: In einer Sections-Ansicht meldet die in
HA 2026.8 „Konfigurationsfehler". Eine schlichte Karte mit if/else im Template
tut dasselbe.

Diese Karten gehören nicht in den Planer-Abschnitt, sondern dorthin, wo man
den Raum ohnehin ansieht – beim Wohnzimmer also in dessen Klima-Abschnitt.

## Was die Karten voraussetzen

* Das Add-on läuft und ist über MQTT mit Home Assistant verbunden – daher
  kommen `sensor.heizungsplaner_*`, `binary_sensor.heizungsplaner_*` und
  `switch.heizungsplaner_party`.
* **card-mod** (über HACS) für die Tabellenbreite und die farbigen Akzente an
  den Störungskarten. Ohne card-mod funktionieren die Karten, sehen aber
  schlichter aus: Die Tabelle nimmt dann nur die Breite ihres Inhalts ein.

## Woraus die Übersicht besteht

| Karte | wann sichtbar |
|---|---|
| Überschrift mit Status und Außentemperatur | immer |
| Partytaste mit Restzeit | immer |
| „Ausgefallen“ (roter Akzent) | wenn ein Thermostat sich nicht meldet oder Sollwerte verweigert |
| „Hinweise“ (gelber Akzent) | bei schwacher Batterie und Ähnlichem |
| Raumtabelle mit Ziel, Ist und nächstem Schaltpunkt | immer |
| Betriebsschalter | immer |

Die Zustandsspalte in der Tabelle erscheint nur, wenn die Räume sich
unterscheiden. Stehen alle im Sommerbetrieb, wäre eine Spalte mit zehnmal
„Sommer“ nur Rauschen – der Zustand steht dann schon in der Überschrift.

## Ein Hinweis zu Vorlagen in Karten

In Lovelace-Templates gibt es **kein `strftime`**. Zeitangaben liefert das
Add-on deshalb fertig formatiert als Attribut (`bis_uhrzeit`,
`naechste_uhrzeit`). Wer dort selbst rechnet, riskiert, dass ein Fehler die
ganze Markdown-Karte ausfallen lässt – nicht nur die betroffene Zeile.
