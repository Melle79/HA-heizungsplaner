"""Vorschlag für die Ersteinrichtung aus dem Bestand in Home Assistant.

Statt dreizehn Thermostate von Hand einzutragen, liest der Assistent die
Bereiche aus Home Assistant, ordnet ihnen ihre Thermostate zu und rät die
zuständigen Personen aus den Namen. Der Vorschlag wird angezeigt, bevor er
gespeichert wird – geraten ist nicht entschieden.
"""
from __future__ import annotations

import json
import os
import urllib.request

import zeitplan as zp

API_BASE = "http://supervisor/core/api"

# Räume, in denen dauerhaft niemand wohnt: niedriger Grundplan, keine
# personenbezogene Absenkung (dort ist ohnehin nie jemand gemeldet).
NEBENRAUM_WORTE = ("wc", "toilette", "bad", "flur", "eingang", "diele", "keller",
                   "garage", "waschk", "treppenh", "gäste", "gaeste", "hobby",
                   "abstell", "speis")
SCHLAF_WORTE = ("schlafzimmer", "elternschlaf")
KINDER_WORTE = ("zimmer",)


def _ws_kommando(kommando: dict):
    """Register-Abfragen gehen nur über die Websocket-API.

    Ein winziger Roh-Client genügt: eine Verbindung, ein Kommando, fertig.
    """
    import base64
    import socket
    import struct

    token = os.environ.get("SUPERVISOR_TOKEN", "")
    sock = socket.create_connection(("supervisor", 80), timeout=20)
    try:
        key = base64.b64encode(os.urandom(16)).decode()
        sock.sendall((
            "GET /core/websocket HTTP/1.1\r\nHost: supervisor\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        ).encode())
        puffer = b""
        while b"\r\n\r\n" not in puffer:
            teil = sock.recv(4096)
            if not teil:
                raise ConnectionError("Verbindung abgewiesen")
            puffer += teil

        def lesen(anzahl: int) -> bytes:
            daten = b""
            while len(daten) < anzahl:
                teil = sock.recv(anzahl - len(daten))
                if not teil:
                    raise ConnectionError("Verbindung beendet")
                daten += teil
            return daten

        def empfangen():
            while True:
                erstes = lesen(1)[0]
                opcode = erstes & 0x0F
                zweites = lesen(1)[0]
                maskiert = zweites & 0x80
                laenge = zweites & 0x7F
                if laenge == 126:
                    laenge = struct.unpack(">H", lesen(2))[0]
                elif laenge == 127:
                    laenge = struct.unpack(">Q", lesen(8))[0]
                maske = lesen(4) if maskiert else None
                nutzlast = lesen(laenge) if laenge else b""
                if maske:
                    nutzlast = bytes(b ^ maske[i % 4] for i, b in enumerate(nutzlast))
                if opcode == 0x9:          # Ping beantworten, sonst bricht die Verbindung
                    senden_frame(0xA, nutzlast)
                    continue
                if opcode == 0x8:
                    raise ConnectionError("Gegenstelle hat geschlossen")
                if opcode in (0x0, 0x1, 0x2):
                    return json.loads(nutzlast.decode("utf-8"))

        def senden_frame(opcode: int, nutzlast: bytes) -> None:
            kopf = bytearray([0x80 | opcode])
            laenge = len(nutzlast)
            maske = os.urandom(4)
            if laenge < 126:
                kopf.append(0x80 | laenge)
            elif laenge < 65536:
                kopf.append(0x80 | 126)
                kopf += struct.pack(">H", laenge)
            else:
                kopf.append(0x80 | 127)
                kopf += struct.pack(">Q", laenge)
            kopf += maske
            sock.sendall(bytes(kopf) + bytes(b ^ maske[i % 4]
                                             for i, b in enumerate(nutzlast)))

        def senden(objekt: dict) -> None:
            senden_frame(0x1, json.dumps(objekt).encode())

        empfangen()                                    # auth_required
        senden({"type": "auth", "access_token": token})
        if empfangen().get("type") != "auth_ok":
            raise PermissionError("Anmeldung an Home Assistant fehlgeschlagen")
        senden({**kommando, "id": 1})
        while True:
            antwort = empfangen()
            if antwort.get("id") == 1 and antwort.get("type") == "result":
                return antwort.get("result") if antwort.get("success") else None
    finally:
        sock.close()


def _bereiche() -> dict:
    """Entity-ID → Bereichsname, über Geräte- und Entitätenregister."""
    try:
        bereiche = _ws_kommando({"type": "config/area_registry/list"}) or []
        geraete = _ws_kommando({"type": "config/device_registry/list"}) or []
        entitaeten = _ws_kommando({"type": "config/entity_registry/list"}) or []
    except Exception:  # noqa: BLE001
        return {}
    name_je_bereich = {b["area_id"]: b["name"] for b in bereiche}
    bereich_je_geraet = {g["id"]: g.get("area_id") for g in geraete}
    zuordnung = {}
    for eintrag in entitaeten:
        bereich = eintrag.get("area_id") or bereich_je_geraet.get(eintrag.get("device_id"))
        if bereich:
            zuordnung[eintrag["entity_id"]] = name_je_bereich.get(bereich, "")
    return zuordnung


def _states() -> list[dict]:
    req = urllib.request.Request(
        f"{API_BASE}/states",
        headers={"Authorization": f"Bearer {os.environ.get('SUPERVISOR_TOKEN', '')}"})
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
    states = _states()
    zuordnung = _bereiche()

    personen = []
    for eintrag in states:
        eid = eintrag.get("entity_id", "")
        if eid.startswith("person."):
            personen.append({
                "entity_id": eid,
                "name": (eintrag.get("attributes") or {}).get("friendly_name", eid),
                "vorname": eid.split(".", 1)[1].split("_")[0].lower(),
            })

    raumtemperaturen: dict[str, list[str]] = {}
    for eintrag in states:
        eid = eintrag.get("entity_id", "")
        attrs = eintrag.get("attributes") or {}
        if (eid.startswith("sensor.") and attrs.get("device_class") == "temperature"
                and zuordnung.get(eid)):
            raumtemperaturen.setdefault(zuordnung[eid], []).append(eid)

    gruppiert: dict[str, list[str]] = {}
    for eintrag in states:
        eid = eintrag.get("entity_id", "")
        if not eid.startswith("climate."):
            continue
        attrs = eintrag.get("attributes") or {}
        if attrs.get("total_member_count"):
            continue                      # Gruppen-Helfer überspringen
        bereich = zuordnung.get(eid) or "Ohne Bereich"
        gruppiert.setdefault(bereich, []).append(eid)

    raeume = []
    for bereich, thermostate in sorted(gruppiert.items()):
        # Doppelt registrierte Geräte erzeugen zwei Entitäten mit gleichem
        # Anzeigenamen. Die Zweitfassung würde nur denselben Heizkörper ein
        # weiteres Mal stellen, deshalb bleibt sie außen vor.
        gesehen, eindeutig = set(), []
        for eid in sorted(thermostate):
            name = next((( e.get("attributes") or {}).get("friendly_name", eid)
                         for e in states if e.get("entity_id") == eid), eid)
            if name in gesehen:
                continue
            gesehen.add(name)
            eindeutig.append(eid)

        zugeordnet = [p["entity_id"] for p in personen
                      if p["vorname"] and p["vorname"] in bereich.lower()]
        art = _art(bereich, zugeordnet)
        fuehler = raumtemperaturen.get(bereich) or []
        raeume.append({
            "name": bereich,
            "aktiv": True,
            "thermostate": eindeutig,
            "personen": zugeordnet,
            "praesenz": [],
            "fenster": [],
            "raumtemp": "",
            "komfort": 21.0 if art == "nebenraum" else 23.0,
            "eco": 18.0 if art == "nebenraum" else 19.0,
            "abwesend": 16.0 if art == "nebenraum" else 17.0,
            "nacht": 17.0 if art == "nebenraum" else 19.0,
            "min": 5.0,
            "max": 26.0,
            "heizkurve": True,
            "anwesenheit": art != "nebenraum",
            "zeitplan": zp.standardplan(art),
            "_art": art,
            "_fuehler_vorschlag": fuehler,
        })
    return raeume
