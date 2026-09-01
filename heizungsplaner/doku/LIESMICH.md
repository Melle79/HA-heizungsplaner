# Bildquellen

`icon.svg` und `logo.svg` sind die Quellen für `icon.png` (128×128) und
`logo.png` (250×100) im Add-on-Verzeichnis. Neu erzeugen mit einem beliebigen
Browser im Kopflos-Betrieb, zum Beispiel:

```
chrome --headless=new --screenshot=icon.png --window-size=128,128 \
       --default-background-color=00000000 --hide-scrollbars seite.html
```

Das Motiv: ein Heizkörper, darüber die Stufenkurve eines Tagesplans – die
beiden Dinge, um die es geht.

## Bilder der Oberfläche

`bilder/*.png` sind Aufnahmen der Oberfläche gegen einen Beispielzustand
(Winter, 2,4 °C draußen, Schultag) – so kommen alle Zustände ins Bild, die es
im Sommer nicht zu sehen gibt: Komfort, Abwesend, Heimkehr, Fenster offen,
Von Hand, Gesperrt.

Unter `bilder/en/` liegen dieselben Ansichten mit englischer Oberfläche und
englischem Beispielzustand – sie gehören zur englischen Fassung von README und
Anleitung. Erzeugt werden sie gegen denselben Mock-Server, nur mit
`api/sprache` → `en` und übersetzten Beispieldaten.

In README und Anleitung sind sie über die Rohadresse von GitHub eingebunden,
nicht über relative Pfade: Home Assistant zeigt `DOCS.md` im Reiter
*Dokumentation* an, löst relative Bildpfade dort aber nicht auf.
