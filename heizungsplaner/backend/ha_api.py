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


def sensor_candidates(states: list[dict] | None = None) -> dict:
    """Kandidaten für die Auswahllisten der Oberfläche.

    Fensterkontakte und Präsenzmelder werden über ihre Geräteklasse erkannt.
    Weil in diesem Haus die Fenster-offen-Meldung mancher Thermostate ohne
    Geräteklasse kommt, wandern zusätzlich alle Binärsensoler in die
    Schalterliste – dort lässt sich alles auswählen, was ``on``/``off`` kennt.
    """
    aussen, fenster, praesenz, raumtemp, schalter = [], [], [], [], []
    for s in states if states is not None else get_states():
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
            eintrag = {"entity_id": eid, "name": name}
            if klasse in ("window", "door", "opening"):
                fenster.append(eintrag)
            elif klasse in ("motion", "occupancy", "presence"):
                praesenz.append(eintrag)
            else:
                fenster.append(eintrag)      # z. B. „Offenes Fenster erkannt“
            schalter.append(eintrag)
        elif domain in ("input_boolean", "switch"):
            schalter.append({"entity_id": eid, "name": name})
    for liste in (aussen, fenster, praesenz, raumtemp, schalter):
        liste.sort(key=lambda e: e["name"])
    return {"aussen": aussen, "fenster": fenster, "praesenz": praesenz,
            "raumtemp": raumtemp, "schalter": schalter}


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
