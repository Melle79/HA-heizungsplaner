"""Zugriff auf die Home-Assistant-API über den Supervisor-Proxy.

Alles, was das Add-on über Home Assistant weiß oder an ihm ändert, läuft hier
durch. Zwei Eigenheiten der Heizungssteuerung sind eingebaut:

* ``set_temperature`` scheitert an einem ausgeschalteten Thermostat und reißt
  bei einem Sammelaufruf alle übrigen mit. Deshalb wird **jeder Thermostat
  einzeln** angesprochen und ein Fehler bleibt lokal.
* Ein Thermostat im Modus ``off`` nimmt keinen Sollwert an. Wer heizen will,
  muss ihn vorher auf ``heat`` stellen.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

_LOGGER = logging.getLogger(__name__)

API_BASE = "http://supervisor/core/api"
TIMEOUT = 15


def _token() -> str:
    return os.environ.get("SUPERVISOR_TOKEN", "")


def available() -> bool:
    return bool(_token())


def _request(method: str, path: str, payload: dict | None = None):
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        method=method,
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers={
            "Authorization": f"Bearer {_token()}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body) if body else None


# ---------------------------------------------------------------- lesen ----

def get_states() -> list[dict]:
    """Alle Zustände auf einen Schlag – ein Aufruf je Regeltakt."""
    if not available():
        return []
    try:
        states = _request("GET", "/states")
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Zustände konnten nicht geladen werden: %s", err)
        return []
    return states if isinstance(states, list) else []


def get_state(entity_id: str) -> dict | None:
    if not available():
        return None
    try:
        data = _request("GET", f"/states/{entity_id}")
        return data if isinstance(data, dict) else None
    except urllib.error.HTTPError as err:
        if err.code != 404:
            _LOGGER.warning("Fehler beim Lesen von %s: %s", entity_id, err)
        return None
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("HA-API nicht erreichbar: %s", err)
        return None


def as_float(value) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if f == f else None  # NaN aussortieren


# -------------------------------------------------------------- schalten ----

def set_hvac_mode(entity_id: str, mode: str) -> bool:
    """Betriebsart setzen (``heat`` / ``off``)."""
    if not available():
        return False
    try:
        _request("POST", "/services/climate/set_hvac_mode",
                 {"entity_id": entity_id, "hvac_mode": mode})
        _LOGGER.info("%s → Betriebsart %s", entity_id, mode)
        return True
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Betriebsart %s für %s fehlgeschlagen: %s", mode, entity_id, err)
        return False


def set_temperature(entity_id: str, temperature: float) -> bool:
    """Sollwert eines einzelnen Thermostats setzen.

    Ein ausgeschaltetes Thermostat lehnt den Aufruf ab – dann wird es einmal
    auf ``heat`` gestellt und der Sollwert erneut geschickt.
    """
    if not available():
        _LOGGER.warning("Kein SUPERVISOR_TOKEN – %s kann nicht gestellt werden", entity_id)
        return False
    payload = {"entity_id": entity_id, "temperature": round(float(temperature), 1)}
    try:
        _request("POST", "/services/climate/set_temperature", payload)
        return True
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Sollwert für %s abgelehnt (%s) – versuche einzuschalten", entity_id, err)

    if not set_hvac_mode(entity_id, "heat"):
        return False
    try:
        _request("POST", "/services/climate/set_temperature", payload)
        return True
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Sollwert %.1f für %s endgültig fehlgeschlagen: %s",
                        temperature, entity_id, err)
        return False


# ------------------------------------------------------------- Auswahlen ----

def climate_entities(states: list[dict] | None = None) -> list[dict]:
    """Alle Thermostate für die Raumkonfiguration in der Oberfläche.

    Gruppen-Helfer (``climate_group_helper``) bleiben außen vor: Der Planer
    stellt jeden Heizkörper einzeln, sonst kämpfen Gruppe und Planer um
    denselben Sollwert.
    """
    out = []
    for s in states if states is not None else get_states():
        eid = s.get("entity_id", "")
        if not eid.startswith("climate."):
            continue
        attrs = s.get("attributes", {}) or {}
        out.append({
            "entity_id": eid,
            "name": attrs.get("friendly_name", eid),
            "min_temp": as_float(attrs.get("min_temp")) or 5.0,
            "max_temp": as_float(attrs.get("max_temp")) or 30.0,
            "current_temperature": as_float(attrs.get("current_temperature")),
            "temperature": as_float(attrs.get("temperature")),
            "state": s.get("state"),
            "gruppe": bool(attrs.get("total_member_count")),
        })
    out.sort(key=lambda e: e["name"])
    return out


def person_entities(states: list[dict] | None = None) -> list[dict]:
    out = []
    for s in states if states is not None else get_states():
        eid = s.get("entity_id", "")
        if not eid.startswith("person."):
            continue
        attrs = s.get("attributes", {}) or {}
        out.append({
            "entity_id": eid,
            "name": attrs.get("friendly_name", eid),
            "state": s.get("state"),
        })
    out.sort(key=lambda e: e["name"])
    return out


TEMPLATE_API = f"{API_BASE}/template"

# Wörter, an denen ein Fensterkontakt auch ohne Geräteklasse zu erkennen ist.
# „Tür“ steht bewusst nicht darin: Es steckt in Gerätenamen wie „Heizung
# Eingangstür“, deren Nebenmelder (Sommermodus, Tastensperre) sonst alle als
# Kontakt gälten. Türkontakte erkennt die Geräteklasse ``door`` zuverlässig.
FENSTER_WORTE = ("fenster", "window", "kipp")

# Was trotz passender Geräteklasse oder passendem Namen keiner ist. Zwei
# Fallgruben aus der Praxis: Die Öffnungszeiten von Tankstellen kommen als
# `device_class: opening`, und die Diagnosemelder eines Rollladens tragen das
# Fenster im Namen, an dem sie hängen.
KEIN_KONTAKT_WORTE = ("status", "blocking", "obstacle", "sun program",
                      "sonnenprogramm", "aufnahme", "update", "verfügbar",
                      "battery", "batterie", "signal", "calibration",
                      "tastensperre", "sommermodus", "urlaubsmodus")


def template(vorlage: str) -> str:
    """Ein Jinja-Template in Home Assistant auswerten lassen.

    Der einzige Weg, aus einem Add-on an die Bereichszuordnung zu kommen: Das
    Geräte- und Entitätenregister gibt es nur über die Websocket-API, die einem
    Add-on nicht offensteht. ``area_name()`` liefert dieselbe Auskunft.
    """
    if not available():
        return ""
    req = urllib.request.Request(
        TEMPLATE_API, method="POST",
        data=json.dumps({"template": vorlage}).encode("utf-8"),
        headers={"Authorization": f"Bearer {_token()}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8")
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Template konnte nicht ausgewertet werden: %s", err)
        return ""


_bereich_cache: dict[tuple, tuple[float, dict]] = {}
BEREICH_CACHE_SEKUNDEN = 300


def bereiche_je_entitaet(domains: tuple[str, ...] = ("binary_sensor",),
                         hoechstalter: float = BEREICH_CACHE_SEKUNDEN) -> dict:
    """Entity-ID → Bereichsname für die angegebenen Domänen.

    Kurz zwischengespeichert: Bereiche ändern sich selten, die Oberfläche
    fragt aber alle halbe Minute nach.
    """
    import time

    gespeichert = _bereich_cache.get(domains)
    if gespeichert and time.monotonic() - gespeichert[0] < hoechstalter:
        return gespeichert[1]

    teile = [
        "{%- for s in states." + domain + " %}{{ s.entity_id }}|"
        "{{ area_name(s.entity_id) or '' }}\n{% endfor -%}"
        for domain in domains
    ]
    zuordnung = {}
    for zeile in template("".join(teile)).splitlines():
        entity_id, _, bereich = zeile.partition("|")
        if entity_id and bereich:
            zuordnung[entity_id] = bereich
    if zuordnung or gespeichert is None:
        _bereich_cache[domains] = (time.monotonic(), zuordnung)
    return zuordnung if zuordnung else (gespeichert[1] if gespeichert else {})


def ist_fensterkontakt(entity_id: str, name: str, klasse: str | None) -> bool:
    """Fensterkontakt an Geräteklasse oder Bezeichnung erkennen.

    ``window`` und ``door`` sind eindeutig. ``opening`` ist es nicht – diese
    Klasse tragen auch Öffnungszeiten von Geschäften –, deshalb muss dort der
    Name mitspielen. Ohne Geräteklasse zählt allein der Name; so werden auch
    die „Offenes Fenster erkannt“-Meldungen mancher Thermostate gefunden.

    Ausgeschlossen bleibt, was nach Diagnose klingt: Ein Rolladen bringt
    Melder wie „Rollo Fenster Luna Obstacle Detection“ mit, die das Fenster
    nur im Namen führen, an dem sie hängen.
    """
    if klasse in ("window", "door"):
        return True
    text = f"{entity_id} {name}".lower()
    if any(wort in text for wort in KEIN_KONTAKT_WORTE):
        return False
    return any(wort in text for wort in FENSTER_WORTE)


def sensor_candidates(states: list[dict] | None = None,
                      mit_bereichen: bool = True) -> dict:
    """Kandidaten für die Auswahllisten der Oberfläche.

    Die Fensterliste enthält, was nach Geräteklasse oder Namen ein Kontakt ist;
    alles übrige Binäre steht getrennt unter ``sonstige_melder``. Ohne diese
    Trennung stünden in der Auswahl auch Dinge wie Tankstellen-Öffnungszeiten.
    """
    aussen, fenster, sonstige, praesenz, raumtemp, schalter = [], [], [], [], [], []
    zustaende = states if states is not None else get_states()
    bereiche = bereiche_je_entitaet(("binary_sensor",)) if mit_bereichen else {}

    for s in zustaende:
        eid = s.get("entity_id", "")
        attrs = s.get("attributes", {}) or {}
        name = attrs.get("friendly_name", eid)
        domain = eid.split(".", 1)[0]
        klasse = attrs.get("device_class")
        if domain == "weather":
            aussen.append({"entity_id": eid, "name": name,
                           "wert": as_float(attrs.get("temperature"))})
        elif domain == "sensor" and klasse == "temperature":
            eintrag = {"entity_id": eid, "name": name, "wert": as_float(s.get("state"))}
            aussen.append(eintrag)
            raumtemp.append(eintrag)
        elif domain == "binary_sensor":
            eintrag = {"entity_id": eid, "name": name,
                       "bereich": bereiche.get(eid, ""),
                       "zustand": s.get("state")}
            if klasse in ("motion", "occupancy", "presence"):
                praesenz.append(eintrag)
            elif ist_fensterkontakt(eid, name, klasse):
                fenster.append(eintrag)
            else:
                sonstige.append(eintrag)
            schalter.append(eintrag)
        elif domain in ("input_boolean", "switch"):
            schalter.append({"entity_id": eid, "name": name})
    for liste in (aussen, fenster, sonstige, praesenz, raumtemp, schalter):
        liste.sort(key=lambda e: e["name"])
    return {"aussen": aussen, "fenster": fenster, "sonstige_melder": sonstige,
            "praesenz": praesenz, "raumtemp": raumtemp, "schalter": schalter}


def zone_home(states: list[dict] | None = None) -> tuple[float, float, float] | None:
    """Koordinaten und Radius der Heimzone – Grundlage fürs Vorheizen."""
    for s in states if states is not None else get_states():
        if s.get("entity_id") != "zone.home":
            continue
        attrs = s.get("attributes", {}) or {}
        lat = as_float(attrs.get("latitude"))
        lon = as_float(attrs.get("longitude"))
        radius = as_float(attrs.get("radius")) or 100.0
        if lat is not None and lon is not None:
            return lat, lon, radius
    return None


def historien_mittel(entity_id: str, stunden: float = 48.0) -> float | None:
    """Mittlere Außentemperatur der letzten Stunden aus der HA-Historie.

    Beim allerersten Start hat der Planer keine Vorgeschichte. Ohne sie würde
    die gedämpfte Außentemperatur beim aktuellen Messwert beginnen – an einem
    kühlen Sommertag hieße das: Heizbetrieb, obwohl die Woche davor mild war.
    Die Historie liefert den fehlenden Anlauf.

    Zwei Eigenheiten der Historien-Schnittstelle sind zu beachten: Ohne
    ``end_time`` gibt sie nur einen Tag ab dem Startzeitpunkt zurück, und der
    Zeitstempel muss URL-kodiert sein, sonst antwortet sie mit 400.
    """
    import datetime
    import urllib.parse

    if not entity_id or not available():
        return None
    jetzt = datetime.datetime.now(datetime.timezone.utc)
    seit = urllib.parse.quote((jetzt - datetime.timedelta(hours=stunden)).isoformat())
    bis = urllib.parse.quote(jetzt.isoformat())
    try:
        daten = _request(
            "GET",
            f"/history/period/{seit}?filter_entity_id={entity_id}&end_time={bis}")
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Historie für %s nicht lesbar: %s", entity_id, err)
        return None

    werte = []
    for reihe in daten if isinstance(daten, list) else []:
        for punkt in reihe if isinstance(reihe, list) else []:
            attrs = punkt.get("attributes") or {}
            rohwert = (attrs.get("temperature") if entity_id.startswith("weather.")
                       else punkt.get("state"))
            wert = as_float(rohwert)
            if wert is not None:
                werte.append(wert)
    if not werte:
        return None
    mittel = round(sum(werte) / len(werte), 2)
    _LOGGER.info("Außentemperatur der letzten %.0f Stunden: %.1f °C aus %d Werten",
                 stunden, mittel, len(werte))
    return mittel
