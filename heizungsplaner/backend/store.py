"""Persistenz: Konfiguration (Räume, Zeitpläne, Einstellungen) und Laufzeitzustand.

Zwei Dateien unter ``/data``:

``config.json``  – was der Benutzer eingestellt hat.
``zustand.json`` – was der Planer zuletzt getan hat.

Der Laufzeitzustand **muss** die Platte überleben. Ohne ihn wüsste der Planer
nach einem Neustart nicht mehr, welchen Sollwert er zuletzt geschrieben hat,
und würde bei jedem Start aufs Neue in jedes Thermostat schreiben – genau das
Dauerfeuer, das der Urlaubsplaner sich geleistet hat.
"""
from __future__ import annotations

import json
import os
import re
import threading
import uuid

DATA_DIR = os.environ.get("DATA_DIR", "./data")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
STATE_FILE = os.path.join(DATA_DIR, "zustand.json")

_lock = threading.Lock()

TAGE = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
MODI = ["komfort", "eco", "nacht", "aus"]
GELTUNG = ["immer", "schultag", "schulfrei"]

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


class ValidationError(ValueError):
    """Ungültige Eingabedaten."""


# --------------------------------------------------------------- Vorgaben ----

STANDARD_EINSTELLUNGEN = {
    "automatik": True,
    "trockenlauf": True,          # sicherer Start: erst rechnen, nicht schalten
    "aussen_entity": "weather.forecast_home",
    "daempfung_stunden": 24.0,    # Zeitkonstante der gedämpften Außentemperatur
    "schulfrei_entity": "input_boolean.wochenende_feiertag",
    "urlaub_entity": "input_boolean.urlaub",
    "urlaub_temperatur": 12.0,
    "frostschutz": 8.0,
    "takt_sekunden": 300,
    "manuell_respektieren": True,
    "heizkurve": {
        "aktiv": True,
        "basis_aussen": 15.0,     # bei dieser Außentemperatur gilt der Sollwert unverändert
        "steilheit": 0.06,        # Kelvin Aufschlag je Kelvin Außenkälte
        "max_korrektur": 1.5,
    },
    "sommer": {
        "aktiv": True,
        "grenze": 16.0,           # gedämpfte Außentemperatur, ab der nicht mehr geheizt wird
        "hysterese": 1.5,
    },
    "anwesenheit": {
        "aktiv": True,
        "karenz_min": 45,         # so lange muss der Raum leer sein, bevor abgesenkt wird
    },
    "vorheizen": {
        "aktiv": True,
        "grund_min": 30,          # Vorlauf bei milder Witterung
        "min_pro_grad": 2.0,      # zusätzliche Minuten je Grad unter 15 °C
        "max_min": 120,
        "heimkehr_km": 8.0,       # ab dieser Entfernung gilt jemand als auf dem Heimweg
    },
    "fenster": {
        "aktiv": True,
        "sturz_k": 1.2,           # Temperatursturz in Kelvin …
        "sturz_min": 10,          # … innerhalb dieser Zeitspanne
        "sperre_min": 30,         # so lange bleibt der Raum danach auf Frostschutz
    },
}

STANDARD_RAUM = {
    "name": "Neuer Raum",
    "aktiv": True,
    "thermostate": [],
    "personen": [],       # leer = jede Person zählt
    "praesenz": [],
    "fenster": [],
    "raumtemp": "",
    "komfort": 21.0,
    "eco": 19.0,
    "abwesend": 17.0,
    "nacht": 18.0,
    "min": 5.0,
    "max": 26.0,
    "heizkurve": True,
    "anwesenheit": True,
    "zeitplan": [],
}


def _leer_config() -> dict:
    return {"einstellungen": dict(STANDARD_EINSTELLUNGEN), "raeume": []}


# ------------------------------------------------------------------- I/O ----

def _read(path: str, fallback):
    if not os.path.exists(path):
        return fallback
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return fallback


def _write(path: str, data) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _merge(vorgabe: dict, gespeichert: dict) -> dict:
    """Gespeicherte Werte über die Vorgaben legen, verschachtelt.

    Sorgt dafür, dass neue Einstellungen aus einer Add-on-Aktualisierung
    auftauchen, ohne dass die Konfiguration von Hand nachgezogen werden muss.
    """
    out = dict(vorgabe)
    for key, value in (gespeichert or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


# --------------------------------------------------------- Konfiguration ----

def load_config() -> dict:
    with _lock:
        roh = _read(CONFIG_FILE, None)
    if not roh:
        return _leer_config()
    return {
        "einstellungen": _merge(STANDARD_EINSTELLUNGEN, roh.get("einstellungen") or {}),
        "raeume": [_merge(STANDARD_RAUM, r) for r in (roh.get("raeume") or [])],
    }


def save_config(config: dict) -> dict:
    with _lock:
        _write(CONFIG_FILE, config)
    return config


# ------------------------------------------------------------ Validierung ----

def _zahl(wert, name: str, minimum: float, maximum: float) -> float:
    try:
        f = float(wert)
    except (TypeError, ValueError) as err:
        raise ValidationError(f"{name}: Zahl erwartet") from err
    if not minimum <= f <= maximum:
        raise ValidationError(f"{name}: Wert muss zwischen {minimum} und {maximum} liegen")
    return round(f, 2)


def validate_zeitplan(zeitplan) -> list[dict]:
    if not isinstance(zeitplan, list):
        raise ValidationError("Zeitplan: Liste erwartet")
    out = []
    for eintrag in zeitplan:
        if not isinstance(eintrag, dict):
            raise ValidationError("Zeitplan: ungültiger Eintrag")
        start = str(eintrag.get("start", "")).strip()
        if not _TIME_RE.match(start):
            raise ValidationError(f"Zeitplan: ungültige Uhrzeit {start!r} (erwartet HH:MM)")
        modus = str(eintrag.get("modus", "")).strip()
        if modus not in MODI:
            raise ValidationError(f"Zeitplan: unbekannter Modus {modus!r}")
        gilt = str(eintrag.get("gilt", "immer")).strip() or "immer"
        if gilt not in GELTUNG:
            raise ValidationError(f"Zeitplan: unbekannte Geltung {gilt!r}")
        tage = [t for t in (eintrag.get("tage") or []) if t in TAGE]
        if not tage:
            raise ValidationError("Zeitplan: mindestens ein Wochentag nötig")
        out.append({"start": start, "modus": modus, "gilt": gilt, "tage": tage})
    out.sort(key=lambda e: e["start"])
    return out


def validate_raum(raum: dict, vorhandene_id: str | None = None) -> dict:
    if not isinstance(raum, dict):
        raise ValidationError("Raum: Objekt erwartet")
    name = str(raum.get("name") or "").strip()[:60]
    if not name:
        raise ValidationError("Der Raum braucht einen Namen")

    thermostate = [str(e).strip() for e in (raum.get("thermostate") or []) if str(e).strip()]
    for eid in thermostate:
        if not eid.startswith("climate."):
            raise ValidationError(f"{eid} ist kein Thermostat")

    minimum = _zahl(raum.get("min", 5.0), "Minimum", 4.0, 30.0)
    maximum = _zahl(raum.get("max", 26.0), "Maximum", 4.0, 35.0)
    if maximum <= minimum:
        raise ValidationError("Das Maximum muss über dem Minimum liegen")

    temperaturen = {}
    for schluessel, vorgabe in (("komfort", 21.0), ("eco", 19.0),
                                ("abwesend", 17.0), ("nacht", 18.0)):
        temperaturen[schluessel] = _zahl(raum.get(schluessel, vorgabe),
                                         schluessel.capitalize(), minimum, maximum)

    return {
        "id": vorhandene_id or uuid.uuid4().hex[:8],
        "name": name,
        "aktiv": bool(raum.get("aktiv", True)),
        "thermostate": thermostate,
        "personen": [str(e).strip() for e in (raum.get("personen") or []) if str(e).strip()],
        "praesenz": [str(e).strip() for e in (raum.get("praesenz") or []) if str(e).strip()],
        "fenster": [str(e).strip() for e in (raum.get("fenster") or []) if str(e).strip()],
        "raumtemp": str(raum.get("raumtemp") or "").strip(),
        "min": minimum,
        "max": maximum,
        "heizkurve": bool(raum.get("heizkurve", True)),
        "anwesenheit": bool(raum.get("anwesenheit", True)),
        "zeitplan": validate_zeitplan(raum.get("zeitplan") or []),
        **temperaturen,
    }


def validate_einstellungen(roh: dict) -> dict:
    """Nur bekannte Felder übernehmen und in vernünftige Grenzen zwingen."""
    e = _merge(STANDARD_EINSTELLUNGEN, roh or {})
    e["automatik"] = bool(e["automatik"])
    e["trockenlauf"] = bool(e["trockenlauf"])
    e["manuell_respektieren"] = bool(e["manuell_respektieren"])
    e["aussen_entity"] = str(e["aussen_entity"] or "").strip()
    e["schulfrei_entity"] = str(e["schulfrei_entity"] or "").strip()
    e["urlaub_entity"] = str(e["urlaub_entity"] or "").strip()
    e["urlaub_temperatur"] = _zahl(e["urlaub_temperatur"], "Urlaubstemperatur", 5.0, 25.0)
    e["frostschutz"] = _zahl(e["frostschutz"], "Frostschutz", 4.0, 15.0)
    e["daempfung_stunden"] = _zahl(e["daempfung_stunden"], "Dämpfung", 0.0, 48.0)
    e["takt_sekunden"] = int(_zahl(e["takt_sekunden"], "Takt", 60, 3600))

    k = e["heizkurve"]
    k["aktiv"] = bool(k["aktiv"])
    k["basis_aussen"] = _zahl(k["basis_aussen"], "Basis-Außentemperatur", -10.0, 25.0)
    k["steilheit"] = _zahl(k["steilheit"], "Steilheit", 0.0, 0.5)
    k["max_korrektur"] = _zahl(k["max_korrektur"], "Maximale Korrektur", 0.0, 6.0)

    s = e["sommer"]
    s["aktiv"] = bool(s["aktiv"])
    s["grenze"] = _zahl(s["grenze"], "Sommergrenze", 5.0, 30.0)
    s["hysterese"] = _zahl(s["hysterese"], "Hysterese", 0.0, 5.0)

    a = e["anwesenheit"]
    a["aktiv"] = bool(a["aktiv"])
    a["karenz_min"] = int(_zahl(a["karenz_min"], "Karenzzeit", 0, 480))

    v = e["vorheizen"]
    v["aktiv"] = bool(v["aktiv"])
    v["grund_min"] = int(_zahl(v["grund_min"], "Grundvorlauf", 0, 240))
    v["min_pro_grad"] = _zahl(v["min_pro_grad"], "Minuten je Grad", 0.0, 15.0)
    v["max_min"] = int(_zahl(v["max_min"], "Maximaler Vorlauf", 0, 360))
    v["heimkehr_km"] = _zahl(v["heimkehr_km"], "Heimkehr-Entfernung", 0.0, 100.0)

    f = e["fenster"]
    f["aktiv"] = bool(f["aktiv"])
    f["sturz_k"] = _zahl(f["sturz_k"], "Temperatursturz", 0.2, 10.0)
    f["sturz_min"] = int(_zahl(f["sturz_min"], "Sturz-Zeitfenster", 2, 120))
    f["sperre_min"] = int(_zahl(f["sperre_min"], "Fenstersperre", 1, 240))
    return e


# ------------------------------------------------------------- Raum-CRUD ----

def add_raum(raum: dict) -> dict:
    config = load_config()
    neu = validate_raum(raum)
    config["raeume"].append(neu)
    save_config(config)
    return neu


def update_raum(raum_id: str, raum: dict) -> dict:
    config = load_config()
    for i, vorhanden in enumerate(config["raeume"]):
        if vorhanden.get("id") == raum_id:
            neu = validate_raum(raum, vorhandene_id=raum_id)
            config["raeume"][i] = neu
            save_config(config)
            return neu
    raise ValidationError("Raum nicht gefunden")


def delete_raum(raum_id: str) -> bool:
    config = load_config()
    vorher = len(config["raeume"])
    config["raeume"] = [r for r in config["raeume"] if r.get("id") != raum_id]
    if len(config["raeume"]) == vorher:
        return False
    save_config(config)
    return True


def update_einstellungen(roh: dict) -> dict:
    config = load_config()
    config["einstellungen"] = validate_einstellungen(
        _merge(config["einstellungen"], roh or {}))
    save_config(config)
    return config["einstellungen"]


# -------------------------------------------------------- Laufzeitzustand ----

def load_state() -> dict:
    with _lock:
        state = _read(STATE_FILE, None)
    if not isinstance(state, dict):
        state = {}
    state.setdefault("thermostate", {})   # entity_id -> {soll, gesetzt_am, modus}
    state.setdefault("raeume", {})        # raum_id  -> Laufzeitdaten
    state.setdefault("aussen_gedaempft", None)
    state.setdefault("sommerbetrieb", False)
    return state


def save_state(state: dict) -> None:
    with _lock:
        _write(STATE_FILE, state)
