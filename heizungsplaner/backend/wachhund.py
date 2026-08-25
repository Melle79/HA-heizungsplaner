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
    "verweigert":   ("nimmt keine Sollwerte an", "fehler"),
    "sommerpause":  ("steht in der Sommerpause und heizt deshalb nicht", "fehler"),
}

# So oft darf ein Schreibvorgang scheitern, bevor es als Störung gilt.
FEHLSCHLAEGE = 3

# Älter als das wird ein Batteriestand nicht mehr für bare Münze genommen.
# Manche Geräte melden ihn nur bei Änderung – nach einem Batteriewechsel steht
# dort womöglich tagelang der alte Wert, und eine Warnung darauf wäre falsch.
BATTERIE_HOECHSTALTER_H = 12


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
            einstellungen: dict, batterien: dict,
            thermostat_zustand: dict | None = None,
            sommerbetrieb: bool = False) -> list[dict]:
    """Alle Thermostate der eingerichteten Räume durchsehen.

    ``thermostat_zustand`` ist das Gedächtnis des Planers je Gerät. Daraus
    stammt die Zahl der vergeblichen Schreibvorgänge: Ein Thermostat, das den
    Sollwert wiederholt nicht annimmt, ist so gut wie ausgefallen, auch wenn es
    sich brav meldet.
    """
    thermostat_zustand = thermostat_zustand or {}
    wacht = einstellungen.get("wachhund") or {}
    if not wacht.get("aktiv", True):
        return []

    stumm_ab = timedelta(hours=float(wacht.get("stumm_stunden", 6)))
    schwelle = float(wacht.get("batterie_prozent", 20))
    # Der Planer rechnet in lokaler Zeit ohne Zeitzone, Home Assistant meldet
    # in UTC. `astimezone` liest eine zeitzonenlose Angabe als Ortszeit – ein
    # `replace(tzinfo=utc)` hätte die Uhr um den Zeitzonenversatz verstellt und
    # jedes Gerät zwei Stunden zu früh für tot erklärt.
    jetzt_utc = jetzt.astimezone(timezone.utc)

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

            # Die Sommerpause eines FRITZ!-Thermostats ist ein Zustand in der
            # FRITZ!Box, nicht in Home Assistant: Das Gerät lehnt jeden
            # Sollwert ab, solange sie läuft, und nichts hier kann sie
            # beenden. Gemeldet wird sie, sobald der Planer wieder heizen
            # will – dann ist der Hinweis eine Handlungsanweisung und keine
            # Nachricht über den Sommer.
            if not sommerbetrieb and (eintrag.get("attributes") or {}).get(
                    "preset_mode") == "summer":
                stoerungen.append(_bauen(entity_id, name, raum, "sommerpause",
                                         "in der FRITZ!Box beenden"))
                continue

            fehler = (thermostat_zustand.get(entity_id) or {}).get("schreib_fehler", 0)
            if fehler >= FEHLSCHLAEGE:
                zusatz = f"{fehler} Versuche vergeblich"
                if (eintrag.get("attributes") or {}).get("preset_mode") == "summer":
                    zusatz += ", das Gerät steht in der Sommerpause"
                stoerungen.append(_bauen(entity_id, name, raum, "verweigert", zusatz))
                continue

            batterie_id = batterien.get(entity_id)
            batterie = states_index.get(batterie_id) if batterie_id else None
            stand = ha_api.as_float((batterie or {}).get("state"))
            if stand is not None and stand <= schwelle:
                # Wie alt ist die Angabe? Ein Gerät, das seinen Ladestand nur
                # bei Änderung meldet, zeigt nach einem Batteriewechsel weiter
                # den alten Wert – davor zu warnen wäre schlicht falsch.
                gemessen = _zeit((batterie or {}).get("last_reported")
                                 or (batterie or {}).get("last_updated"))
                alter = ((jetzt_utc - gemessen).total_seconds() / 3600
                         if gemessen else None)
                if alter is not None and alter > BATTERIE_HOECHSTALTER_H:
                    _LOGGER.info("Batteriestand von %s ist %.0f Stunden alt "
                                 "(%.0f %%) – keine Warnung", batterie_id, alter, stand)
                else:
                    zusatz = f"{stand:.0f} %"
                    if gemessen:
                        zusatz += f", Stand {gemessen.astimezone().strftime('%H:%M')} Uhr"
                    stoerungen.append(_bauen(entity_id, name, raum, "batterie", zusatz))

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
