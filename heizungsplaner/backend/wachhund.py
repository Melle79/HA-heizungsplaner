"""Überwachung der Thermostate: Wer nicht mehr antwortet, wird gemeldet.

Der Anlass ist ein konkreter Vorfall: Während eines Urlaubs fielen vier
Thermostate wegen leerer Batterien aus, und niemand bemerkte es.

Eine Batteriewarnung allein hilft hier nicht – die zehn SwitchBot-Thermostate
dieses Hauses melden über Matter **gar keinen Ladestand**. Was sie melden, ist
ihr Zustand, und zwar regelmäßig. Bleibt diese Meldung aus, ist das Gerät tot,
gleich aus welchem Grund: leere Batterie, abgezogener Funkstick, Defekt.
Deshalb wacht der Planer über das **Lebenszeichen**, nicht über die Batterie –
und nimmt den Ladestand nur mit, wo es ihn gibt.

Gemeldet wird auf Flanke: einmal beim Auftreten, einmal bei der Behebung. Eine
Warnung, die stündlich erneut aufs Telefon kommt, wird nach dem dritten Mal
weggewischt und beim vierten Mal übersehen.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import ha_api

_LOGGER = logging.getLogger(__name__)

# Wie eine Störung benannt und wie dringend sie ist.
ARTEN = {
    "fehlt":        ("gibt es in Home Assistant nicht mehr", "fehler"),
    "unerreichbar": ("ist nicht erreichbar", "fehler"),
    "stumm":        ("meldet sich nicht mehr", "fehler"),
    "batterie":     ("hat eine schwache Batterie", "warnung"),
}


def _zeit(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        wert = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return wert if wert.tzinfo else wert.replace(tzinfo=timezone.utc)


def batterien_je_thermostat() -> dict:
    """Thermostat → Batterieanzeige am selben Gerät, sofern es eine gibt.

    Die meisten Thermostate dieses Hauses haben keine. Wo es eine gibt, ist sie
    die frühere Warnung – der ausbleibende Lebenszeichen-Ping kommt erst, wenn
    das Gerät schon steht.
    """
    vorlage = (
        "{%- for c in states.climate if c.attributes.total_member_count is not defined %}"
        "{{ c.entity_id }}|"
        "{% for e in device_entities(device_id(c.entity_id)) %}"
        "{% if e.startswith('sensor.') and state_attr(e, 'device_class') == 'battery' %}"
        "{{ e }}{% endif %}{% endfor %}\n{% endfor -%}")
    zuordnung = {}
    for zeile in ha_api.template(vorlage).splitlines():
        thermostat, _, batterie = zeile.partition("|")
        if thermostat and batterie:
            zuordnung[thermostat.strip()] = batterie.strip()
    return zuordnung


def pruefen(config: dict, states_index: dict, jetzt: datetime,
            einstellungen: dict, batterien: dict) -> list[dict]:
    """Alle Thermostate der eingerichteten Räume durchsehen."""
    wacht = einstellungen.get("wachhund") or {}
    if not wacht.get("aktiv", True):
        return []

    stumm_ab = timedelta(hours=float(wacht.get("stumm_stunden", 6)))
    schwelle = float(wacht.get("batterie_prozent", 20))
    jetzt_utc = jetzt.astimezone(timezone.utc) if jetzt.tzinfo else \
        jetzt.replace(tzinfo=timezone.utc).astimezone(timezone.utc)

    stoerungen = []
    for raum in config["raeume"]:
        for entity_id in raum.get("thermostate") or []:
            eintrag = states_index.get(entity_id)
            name = ((eintrag or {}).get("attributes") or {}).get(
                "friendly_name", entity_id)

            if eintrag is None:
                stoerungen.append(_bauen(entity_id, name, raum, "fehlt", ""))
                continue

            if eintrag.get("state") in ("unavailable", "unknown"):
                stoerungen.append(_bauen(entity_id, name, raum, "unerreichbar", ""))
                continue

            gemeldet = _zeit(eintrag.get("last_reported")
                             or eintrag.get("last_updated"))
            if gemeldet and jetzt_utc - gemeldet > stumm_ab:
                stunden = (jetzt_utc - gemeldet).total_seconds() / 3600
                stoerungen.append(_bauen(entity_id, name, raum, "stumm",
                                         f"zuletzt vor {stunden:.0f} Stunden"))
                continue

            batterie_id = batterien.get(entity_id)
            stand = ha_api.as_float((states_index.get(batterie_id) or {}).get("state")) \
                if batterie_id else None
            if stand is not None and stand <= schwelle:
                stoerungen.append(_bauen(entity_id, name, raum, "batterie",
                                         f"{stand:.0f} %"))

    return stoerungen


def _bauen(entity_id: str, name: str, raum: dict, art: str, zusatz: str) -> dict:
    text, schwere = ARTEN[art]
    return {
        "entity_id": entity_id,
        "name": name,
        "raum": raum["name"],
        "art": art,
        "schwere": schwere,
        "text": f"{name} ({raum['name']}) {text}" + (f" – {zusatz}" if zusatz else ""),
    }


def vergleichen(neu: list[dict], gemerkt: dict) -> tuple[list[dict], list[dict]]:
    """Was ist neu hinzugekommen, was hat sich erledigt?

    Verglichen wird über Entität **und** Art: Wird aus „schwache Batterie“ ein
    „meldet sich nicht mehr“, ist das eine neue Nachricht wert – das Gerät ist
    inzwischen ganz ausgefallen.
    """
    jetzt = {f"{s['entity_id']}|{s['art']}": s for s in neu}
    vorher = set(gemerkt or {})
    hinzu = [s for schluessel, s in jetzt.items() if schluessel not in vorher]
    weg = [gemerkt[schluessel] for schluessel in vorher if schluessel not in jetzt]
    return hinzu, weg


def als_gedaechtnis(stoerungen: list[dict]) -> dict:
    return {f"{s['entity_id']}|{s['art']}": s for s in stoerungen}


def meldung_bauen(hinzu: list[dict], weg: list[dict]) -> tuple[str, str] | None:
    """Titel und Text für die Benachrichtigung – oder nichts zu melden."""
    if not hinzu and not weg:
        return None
    if hinzu:
        schwer = [s for s in hinzu if s["schwere"] == "fehler"]
        titel = ("Heizung: %d Thermostat%s ausgefallen" %
                 (len(schwer), "" if len(schwer) == 1 else "e")) if schwer \
            else "Heizung: Batterie wird schwach"
        zeilen = [s["text"] for s in hinzu]
        if weg:
            zeilen.append("")
            zeilen += ["Wieder in Ordnung: " + s["name"] for s in weg]
        return titel, "\n".join(zeilen)
    return ("Heizung: wieder in Ordnung",
            "\n".join(s["text"].replace(ARTEN[s["art"]][0], "meldet sich wieder")
                      for s in weg))
