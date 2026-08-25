"""Heizungsplaner – Dienst, Regeltakt und REST-Schnittstelle.

Der Takt läuft in einem eigenen Faden und rechnet alle paar Minuten alle Räume
durch. Die Oberfläche liest denselben Bericht, den auch MQTT bekommt; es gibt
keine zweite Wahrheit.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.request

from flask import Flask, jsonify, request, send_from_directory

import ha_api
import logbuch
import regelung
import store
import uebernahme
from version import VERSION

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
_LOGGER = logging.getLogger("heizungsplaner")

FRONTEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "frontend")

app = Flask(__name__, static_folder=None)

_takt_lock = threading.Lock()
_wecker = threading.Event()
_letzter_bericht: dict = {"zeit": None, "raeume": [], "hinweis": "Noch kein Durchlauf"}
_publisher = None


# ----------------------------------------------------------- Zeitzone ----

def _zeitzone_uebernehmen() -> None:
    """Die Zeitzone von Home Assistant übernehmen.

    Ohne das rechnet der Container in UTC – ein Zeitplan mit 21:00 Uhr würde
    im Sommer zwei Stunden zu spät schalten.
    """
    try:
        req = urllib.request.Request(
            "http://supervisor/core/api/config",
            headers={"Authorization": f"Bearer {os.environ.get('SUPERVISOR_TOKEN', '')}"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            zone = json.loads(resp.read().decode("utf-8")).get("time_zone")
        if zone:
            os.environ["TZ"] = zone
            time.tzset()
            _LOGGER.info("Zeitzone: %s", zone)
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Zeitzone konnte nicht übernommen werden: %s", err)


# --------------------------------------------------------------- Takt ----

def _takt_ausfuehren() -> dict:
    global _letzter_bericht
    with _takt_lock:
        config = store.load_config()
        state = store.load_state()
        try:
            bericht = regelung.takt(config, state, logbuch.eintragen)
        except Exception as err:  # noqa: BLE001
            _LOGGER.exception("Regeltakt fehlgeschlagen")
            bericht = {"zeit": None, "raeume": [], "fehler": str(err)}
        else:
            store.save_state(state)
        bericht["version"] = VERSION
        _letzter_bericht = bericht
    if _publisher is not None:
        try:
            _publisher.publish_status(bericht)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("MQTT-Meldung fehlgeschlagen: %s", err)
    return bericht


def _takt_schleife() -> None:
    while True:
        bericht = _takt_ausfuehren()
        raeume = len(bericht.get("raeume") or [])
        if bericht.get("fehler"):
            _LOGGER.warning("Takt mit Fehler: %s", bericht["fehler"])
        else:
            _LOGGER.info("Takt: %d Räume, außen %s °C%s", raeume,
                         bericht.get("aussen"),
                         " (Trockenlauf)" if bericht.get("trockenlauf") else "")
        pause = int(store.load_config()["einstellungen"].get("takt_sekunden", 300))
        _wecker.wait(timeout=pause)
        _wecker.clear()


def _sofort_rechnen() -> None:
    """Den Regeltakt vorziehen, etwa nach einer Änderung in der Oberfläche."""
    _wecker.set()


# ---------------------------------------------------------------- MQTT ----

def _mqtt_starten() -> None:
    global _publisher
    host = os.environ.get("MQTT_HOST")
    if not host:
        _LOGGER.warning("Kein MQTT – die Statusentitäten fehlen in Home Assistant")
        return
    import mqtt_publisher
    _publisher = mqtt_publisher.Publisher(
        host, int(os.environ.get("MQTT_PORT", 1883)),
        os.environ.get("MQTT_USER"), os.environ.get("MQTT_PASSWORD"))

    def bereit() -> None:
        _publisher.publish_discovery(store.load_config()["raeume"])
        if _letzter_bericht.get("zeit"):
            _publisher.publish_status(_letzter_bericht)

    _publisher.on_ready = bereit
    _publisher.start()


def _discovery_auffrischen() -> None:
    if _publisher is not None and _publisher.connected.is_set():
        try:
            _publisher.publish_discovery(store.load_config()["raeume"])
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Discovery fehlgeschlagen: %s", err)


# ------------------------------------------------------------ Oberfläche ----

@app.route("/")
def index():
    return send_from_directory(FRONTEND, "index.html")


@app.route("/<path:datei>")
def statisch(datei: str):
    return send_from_directory(FRONTEND, datei)


# ------------------------------------------------------------------ API ----

@app.route("/api/status")
def api_status():
    return jsonify(_letzter_bericht)


@app.route("/api/takt", methods=["POST"])
def api_takt():
    return jsonify(_takt_ausfuehren())


@app.route("/api/config")
def api_config():
    config = store.load_config()
    return jsonify({**config, "version": VERSION})


@app.route("/api/raeume", methods=["GET", "POST"])
def api_raeume():
    if request.method == "GET":
        return jsonify(store.load_config()["raeume"])
    try:
        raum = store.add_raum(request.get_json(force=True) or {})
    except store.ValidationError as err:
        return jsonify({"fehler": str(err)}), 400
    _discovery_auffrischen()
    _sofort_rechnen()
    return jsonify(raum), 201


@app.route("/api/raeume/<raum_id>", methods=["PUT", "DELETE"])
def api_raum(raum_id: str):
    if request.method == "DELETE":
        if not store.delete_raum(raum_id):
            return jsonify({"fehler": "Raum nicht gefunden"}), 404
        zustand = store.load_state()
        zustand["raeume"].pop(raum_id, None)
        store.save_state(zustand)
        _discovery_auffrischen()
        _sofort_rechnen()
        return jsonify({"ok": True})
    try:
        raum = store.update_raum(raum_id, request.get_json(force=True) or {})
    except store.ValidationError as err:
        return jsonify({"fehler": str(err)}), 400
    _discovery_auffrischen()
    _sofort_rechnen()
    return jsonify(raum)


@app.route("/api/einstellungen", methods=["GET", "PUT"])
def api_einstellungen():
    if request.method == "GET":
        return jsonify(store.load_config()["einstellungen"])
    vorher = store.load_config()["einstellungen"].get("aussen_entity")
    try:
        einstellungen = store.update_einstellungen(request.get_json(force=True) or {})
    except store.ValidationError as err:
        return jsonify({"fehler": str(err)}), 400
    if einstellungen.get("aussen_entity") != vorher:
        # Andere Quelle, andere Vorgeschichte: Der geglättete Wert der alten
        # Entität würde sonst noch tagelang nachwirken.
        _anlauf_verwerfen()
    _sofort_rechnen()
    return jsonify(einstellungen)


def _anlauf_verwerfen() -> None:
    """Die gedämpfte Außentemperatur verwerfen – sie läuft neu aus der Historie an."""
    with _takt_lock:
        zustand = store.load_state()
        zustand["aussen_gedaempft"] = None
        store.save_state(zustand)


@app.route("/api/anlauf", methods=["POST"])
def api_anlauf():
    _anlauf_verwerfen()
    logbuch.eintragen("Alle Räume", "Anlauf",
                      "Gedämpfte Außentemperatur zurückgesetzt")
    return jsonify(_takt_ausfuehren())


@app.route("/api/entitaeten")
def api_entitaeten():
    states = ha_api.get_states()
    kandidaten = ha_api.sensor_candidates(states)
    return jsonify({
        "thermostate": ha_api.climate_entities(states),
        "personen": ha_api.person_entities(states),
        **kandidaten,
    })


@app.route("/api/uebernahme", methods=["GET", "POST"])
def api_uebernahme():
    """Vorschlag anzeigen (GET) oder übernehmen (POST)."""
    try:
        vorschlag = uebernahme.vorschlag()
    except Exception as err:  # noqa: BLE001
        _LOGGER.exception("Übernahme fehlgeschlagen")
        return jsonify({"fehler": str(err)}), 500
    if request.method == "GET":
        return jsonify(vorschlag)

    auswahl = (request.get_json(force=True) or {}).get("raeume")
    if isinstance(auswahl, list) and auswahl:
        namen = {str(n) for n in auswahl}
        vorschlag = [r for r in vorschlag if r["name"] in namen]

    config = store.load_config()
    vorhandene = {r["name"] for r in config["raeume"]}
    angelegt = []
    for roh in vorschlag:
        if roh["name"] in vorhandene:
            continue
        roh.pop("_art", None)
        roh.pop("_fuehler_vorschlag", None)
        try:
            angelegt.append(store.validate_raum(roh))
        except store.ValidationError as err:
            _LOGGER.warning("Raum %s übersprungen: %s", roh["name"], err)
    config["raeume"].extend(angelegt)
    store.save_config(config)
    logbuch.eintragen("Alle Räume", "Einrichtung",
                      f"{len(angelegt)} Räume aus Home Assistant übernommen")
    _discovery_auffrischen()
    _sofort_rechnen()
    return jsonify({"angelegt": [r["name"] for r in angelegt]})


@app.route("/api/logbuch", methods=["GET", "DELETE"])
def api_logbuch():
    if request.method == "DELETE":
        logbuch.leeren()
        return jsonify({"ok": True})
    return jsonify(logbuch.lesen(int(request.args.get("grenze", 200))))


@app.route("/api/gesundheit")
def api_gesundheit():
    """Was der Einrichtung im Weg steht – für den Hinweisbalken der Oberfläche."""
    config = store.load_config()
    states = ha_api.get_states()
    vorhanden = {s.get("entity_id") for s in states}
    einst = config["einstellungen"]
    hinweise = []

    if not config["raeume"]:
        hinweise.append({"art": "info",
                         "text": "Noch keine Räume eingerichtet – der Assistent "
                                 "übernimmt sie aus Home Assistant."})
    if einst.get("trockenlauf"):
        hinweise.append({"art": "warnung",
                         "text": "Trockenlauf ist aktiv: Der Planer rechnet, "
                                 "stellt aber kein Thermostat."})
    if not einst.get("automatik"):
        hinweise.append({"art": "warnung", "text": "Die Automatik ist ausgeschaltet."})

    for schluessel, beschriftung in (("aussen_entity", "Außentemperatur"),
                                     ("urlaub_entity", "Urlaubsschalter"),
                                     ("schulfrei_entity", "Schulfrei-Schalter")):
        entity_id = einst.get(schluessel)
        if entity_id and entity_id not in vorhanden:
            hinweise.append({"art": "fehler",
                             "text": f"{beschriftung}: {entity_id} gibt es in "
                                     f"Home Assistant nicht."})

    zustand_je_id = {s.get("entity_id"): s.get("state") for s in states}
    zugeordnete_kontakte = {e for raum in config["raeume"] for e in raum["fenster"]}

    belegt: dict[str, str] = {}
    for raum in config["raeume"]:
        # Ein Kontakt, der nichts meldet, gilt nicht als „geschlossen“ – sonst
        # macht ein leerer Knopf den Raum stillschweigend blind.
        for entity_id in raum["fenster"]:
            if zustand_je_id.get(entity_id) not in ("on", "off"):
                hinweise.append({
                    "art": "warnung",
                    "text": f"Fensterkontakt {entity_id} (Raum „{raum['name']}“) "
                            f"meldet nichts – der Raum fällt auf die "
                            f"Temperatursturz-Erkennung zurück."})
        freigabe = raum.get("freigabe_entity")
        if freigabe and freigabe not in vorhanden:
            hinweise.append({
                "art": "fehler",
                "text": f"Der Freigabeschalter {freigabe} (Raum „{raum['name']}“) "
                        f"gibt es in Home Assistant nicht – der Raum wird "
                        f"deshalb normal geregelt."})
        if raum.get("nur_praesenz") and not raum["praesenz"]:
            hinweise.append({
                "art": "warnung",
                "text": f"Raum „{raum['name']}“ soll allein dem Präsenzmelder "
                        f"folgen, hat aber keinen hinterlegt – er gilt darum "
                        f"immer als belegt."})
        if not raum["thermostate"]:
            hinweise.append({"art": "warnung",
                             "text": f"Raum „{raum['name']}“ hat kein Thermostat."})
        if not raum["zeitplan"]:
            hinweise.append({"art": "warnung",
                             "text": f"Raum „{raum['name']}“ hat keinen Zeitplan – "
                                     f"es gilt dauerhaft die Eco-Temperatur."})
        for entity_id in raum["thermostate"]:
            if entity_id not in vorhanden:
                hinweise.append({"art": "fehler",
                                 "text": f"{entity_id} (Raum „{raum['name']}“) gibt es "
                                         f"in Home Assistant nicht mehr."})
            if entity_id in belegt:
                hinweise.append({"art": "fehler",
                                 "text": f"{entity_id} steht in „{belegt[entity_id]}“ "
                                         f"und in „{raum['name']}“ – zwei Räume würden "
                                         f"dasselbe Thermostat gegeneinander stellen."})
            else:
                belegt[entity_id] = raum["name"]

    # Neu nachgerüstete Fensterkontakte anbieten: Was im Bereich eines Raumes
    # liegt und noch keinem zugeordnet ist, wäre sonst leicht zu übersehen.
    raum_je_name = {raum["name"]: raum for raum in config["raeume"]}
    bereiche = ha_api.bereiche_je_entitaet(("binary_sensor",))
    for s in states:
        eid = s.get("entity_id", "")
        if not eid.startswith("binary_sensor.") or eid in zugeordnete_kontakte:
            continue
        attrs = s.get("attributes") or {}
        name = attrs.get("friendly_name", eid)
        if not ha_api.ist_fensterkontakt(eid, name, attrs.get("device_class")):
            continue
        bereich = bereiche.get(eid)
        raum = raum_je_name.get(bereich) if bereich else None
        if raum:
            hinweise.append({
                "art": "info",
                "text": f"„{name}“ liegt im Bereich „{bereich}“ und ist noch keinem "
                        f"Raum zugeordnet. Im Raum „{raum['name']}“ unter "
                        f"„Fensterkontakte“ eintragen, damit der Planer ihn nutzt.",
                "raum_id": raum["id"], "entity_id": eid})

    return jsonify({"hinweise": hinweise, "mqtt": _publisher is not None
                    and _publisher.connected.is_set()})


# ---------------------------------------------------------------- Start ----

def main() -> None:
    _zeitzone_uebernehmen()
    if not ha_api.available():
        _LOGGER.error("Kein SUPERVISOR_TOKEN – der Planer kann nichts stellen")
    _mqtt_starten()
    threading.Thread(target=_takt_schleife, name="regeltakt", daemon=True).start()
    _LOGGER.info("Heizungsplaner %s startet auf Port 8098", VERSION)
    app.run(host="0.0.0.0", port=8098, threaded=True)


if __name__ == "__main__":
    main()
