"""Vorschlag für die Ersteinrichtung aus dem Bestand in Home Assistant.

Statt dreizehn Thermostate von Hand einzutragen, liest der Assistent die
Bereiche aus Home Assistant, ordnet ihnen ihre Thermostate zu und rät die
zuständigen Personen aus den Namen. Der Vorschlag wird angezeigt, bevor er
gespeichert wird – geraten ist nicht entschieden.

Die Bereichszuordnung kommt über eine Template-Abfrage. Das Geräte- und
Entitätenregister ließe sich nur über die Websocket-API lesen, die einem
Add-on nicht offensteht; ``area_name()`` liefert dieselbe Auskunft über die
REST-Schnittstelle, die das Add-on ohnehin benutzt.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request

import zeitplan as zp

_LOGGER = logging.getLogger(__name__)

API_BASE = "http://supervisor/core/api"

# Räume, in denen dauerhaft niemand wohnt: niedriger Grundplan, keine
# personenbezogene Absenkung (dort ist ohnehin nie jemand gemeldet).
NEBENRAUM_WORTE = ("wc", "toilette", "bad", "flur", "eingang", "diele", "keller",
                   "garage", "waschk", "treppenh", "gäste", "gaeste", "hobby",
                   "abstell", "speis")
SCHLAF_WORTE = ("schlafzimmer", "elternschlaf")
KINDER_WORTE = ("zimmer",)

# Vorgabetemperaturen je Raumart: Komfort, Eco, Nacht, Abwesend.
# Die Wohn- und Kinderzimmerwerte entsprechen dem, was die bisherigen
# Zeitpläne dieses Hauses geschaltet haben.
TEMPERATUREN = {
    "wohnraum":     (23.0, 19.0, 19.0, 17.0),
    "kinderzimmer": (23.0, 19.0, 19.0, 17.0),
    "schlafzimmer": (20.0, 18.0, 17.0, 16.0),
    "nebenraum":    (21.0, 18.0, 17.0, 16.0),
}

# Vier Felder je Zeile: Entität, Bereich, Anzeigename, Rolle.
# Rolle ist "gruppe" für Gruppen-Helfer, "einzeln" für echte Thermostate und
# "fuehler" für Temperatursensoren.
BEREICHS_TEMPLATE = (
    "{%- for s in states.climate %}"
    "{{ s.entity_id }}|{{ area_name(s.entity_id) or '' }}|{{ s.name }}|"
    "{{ 'gruppe' if s.attributes.total_member_count is defined else 'einzeln' }}\n"
    "{% endfor -%}"
    "{%- for s in states.sensor if s.attributes.device_class == 'temperature' %}"
    "{{ s.entity_id }}|{{ area_name(s.entity_id) or '' }}|{{ s.name }}|fuehler\n"
    "{% endfor -%}"
)


def _token() -> str:
    return os.environ.get("SUPERVISOR_TOKEN", "")


def _template(vorlage: str) -> str:
    req = urllib.request.Request(
        f"{API_BASE}/template",
        method="POST",
        data=json.dumps({"template": vorlage}).encode("utf-8"),
        headers={"Authorization": f"Bearer {_token()}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8")


def _states() -> list[dict]:
    req = urllib.request.Request(
        f"{API_BASE}/states",
        headers={"Authorization": f"Bearer {_token()}"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _art(name: str, personen: list[str]) -> str:
    klein = name.lower()
    if any(wort in klein for wort in NEBENRAUM_WORTE):
        return "nebenraum"
    if any(wort in klein for wort in SCHLAF_WORTE):
        return "schlafzimmer"
    if personen and any(wort in klein for wort in KINDER_WORTE):
        return "kinderzimmer"
    return "wohnraum"


def vorschlag() -> list[dict]:
    """Räume aus dem HA-Bestand ableiten – ein Raum je Bereich mit Thermostat."""
    zeilen = []
    for zeile in _template(BEREICHS_TEMPLATE).splitlines():
        teile = zeile.split("|")
        if len(teile) == 4:
            zeilen.append(teile)

    personen = []
    for eintrag in _states():
        eid = eintrag.get("entity_id", "")
        if eid.startswith("person."):
            personen.append({
                "entity_id": eid,
                "name": (eintrag.get("attributes") or {}).get("friendly_name", eid),
                "vorname": eid.split(".", 1)[1].split("_")[0].lower(),
            })

    thermostate_je_bereich: dict[str, list[tuple[str, str]]] = {}
    fuehler_je_bereich: dict[str, list[str]] = {}
    for entity_id, bereich, anzeigename, art in zeilen:
        if not bereich:
            continue
        if art == "fuehler":
            fuehler_je_bereich.setdefault(bereich, []).append(entity_id)
        elif art == "einzeln":
            thermostate_je_bereich.setdefault(bereich, []).append(
                (entity_id, anzeigename))

    raeume = []
    for bereich, eintraege in sorted(thermostate_je_bereich.items()):
        # Doppelt registrierte Geräte erzeugen zwei Entitäten mit gleichem
        # Anzeigenamen. Die Zweitfassung würde nur denselben Heizkörper ein
        # weiteres Mal stellen, deshalb bleibt sie außen vor.
        gesehen, eindeutig = set(), []
        for entity_id, anzeigename in sorted(eintraege):
            if anzeigename in gesehen:
                _LOGGER.info("%s übersprungen – gleicher Name wie ein anderes "
                             "Thermostat in %s", entity_id, bereich)
                continue
            gesehen.add(anzeigename)
            eindeutig.append(entity_id)

        zugeordnet = [p["entity_id"] for p in personen
                      if p["vorname"] and p["vorname"] in bereich.lower()]
        art = _art(bereich, zugeordnet)
        komfort, eco, nacht, abwesend = TEMPERATUREN[art]
        raeume.append({
            "name": bereich,
            "aktiv": True,
            "thermostate": eindeutig,
            "personen": zugeordnet,
            "praesenz": [],
            "fenster": [],
            "raumtemp": "",
            "komfort": komfort,
            "eco": eco,
            "abwesend": abwesend,
            "nacht": nacht,
            "min": 5.0,
            "max": 26.0,
            "heizkurve": True,
            "anwesenheit": art != "nebenraum",
            "zeitplan": zp.standardplan(art),
            "_art": art,
            "_fuehler_vorschlag": fuehler_je_bereich.get(bereich, []),
        })

    # Thermostate ohne Bereich gehen sonst stillschweigend verloren.
    ohne_bereich = [e for e, b, _n, a in zeilen if not b and a == "einzeln"]
    if ohne_bereich:
        raeume.append({
            "name": "Ohne Bereich",
            "aktiv": False,
            "thermostate": ohne_bereich,
            "personen": [], "praesenz": [], "fenster": [], "raumtemp": "",
            "komfort": 21.0, "eco": 18.0, "abwesend": 16.0, "nacht": 17.0,
            "min": 5.0, "max": 26.0, "heizkurve": True, "anwesenheit": False,
            "zeitplan": zp.standardplan("nebenraum"),
            "_art": "nebenraum",
            "_fuehler_vorschlag": [],
        })
    return raeume
