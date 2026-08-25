#!/usr/bin/env python3
"""Aus dem Kartenbaukasten eine YAML-Fassung zum Einfügen erzeugen.

    python3 heizungsplaner/dashboard/erzeuge_yaml.py

PyYAML wird nicht vorausgesetzt – der Aufbau ist flach genug, um ihn selbst zu
schreiben. Das Ergebnis lässt sich im Lovelace-YAML-Editor einsetzen und liest
sich beim Zurücklesen wieder als genau dieselbe Struktur.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import karten  # noqa: E402

KOPF = """# Karten für die Übersicht des Heizungsplaners
#
# Einzufügen als eigener Abschnitt einer Ansicht vom Typ „sections“:
# Ansicht bearbeiten → Abschnitt hinzufügen → Dreipunktmenü →
# „Im YAML-Editor bearbeiten“ → diesen Inhalt einsetzen.
#
# Voraussetzungen:
#   * das Add-on läuft und ist über MQTT mit Home Assistant verbunden
#   * card-mod ist installiert – für die Tabellenbreite und die farbigen
#     Akzente an den Störungskarten. Ohne card-mod funktionieren die Karten,
#     sehen aber schlichter aus.
#
# Erzeugt aus karten.py; Änderungen dort vornehmen und neu erzeugen.
"""

# Schlüssel, die in Anführungszeichen müssen: card-mod verwendet Zeichen, die
# YAML sonst als Struktur liest.
HEIKEL = " $.:"


def als_yaml(wert, tiefe=0):
    einzug = "  " * tiefe
    if isinstance(wert, dict):
        zeilen = []
        for schluessel, inhalt in wert.items():
            schl = f'"{schluessel}"' if any(c in schluessel for c in HEIKEL) else schluessel
            if isinstance(inhalt, (dict, list)) and inhalt:
                zeilen.append(f"{einzug}{schl}:")
                zeilen.append(als_yaml(inhalt, tiefe + 1))
            elif isinstance(inhalt, str) and "\n" in inhalt:
                # „|“ behält den abschließenden Umbruch, „|-“ streicht ihn –
                # so bleibt der Text bitgenau erhalten.
                zeilen.append(f"{einzug}{schl}: " + ("|" if inhalt.endswith("\n") else "|-"))
                for z in inhalt.rstrip("\n").split("\n"):
                    zeilen.append(f"{einzug}  {z}" if z else "")
            else:
                zeilen.append(f"{einzug}{schl}: {json.dumps(inhalt, ensure_ascii=False)}")
        return "\n".join(zeilen)
    if isinstance(wert, list):
        zeilen = []
        for eintrag in wert:
            if isinstance(eintrag, dict):
                erste, *rest = als_yaml(eintrag, tiefe + 1).lstrip().split("\n")
                zeilen.append(f"{einzug}- {erste}")
                zeilen += rest
            else:
                zeilen.append(f"{einzug}- {json.dumps(eintrag, ensure_ascii=False)}")
        return "\n".join(zeilen)
    return f"{einzug}{json.dumps(wert, ensure_ascii=False)}"


if __name__ == "__main__":
    ziel = pathlib.Path(__file__).parent / "heizungsplaner-karten.yaml"
    ziel.write_text(KOPF + als_yaml(karten.abschnitt()) + "\n", encoding="utf-8")
    print(f"{ziel.name}: {len(ziel.read_text(encoding='utf-8'))} Zeichen")
