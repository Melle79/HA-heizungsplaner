"""Wer ist da, wer kommt gleich – und was heißt das für einen einzelnen Raum.

Ein Raum gilt als besetzt, wenn eine der für ihn zuständigen Personen zu Hause
ist oder ein Präsenzmelder im Raum anschlägt. Sind für einen Raum keine
Personen hinterlegt, zählt die ganze Familie.

Zwei Eigenheiten dieses Hauses sind berücksichtigt:

* Die Tracker melden unterwegs eigene Standzonen statt ``not_home``. Deshalb
  wird ausschließlich auf ``home`` geprüft – eine Prüfung auf ``not_home``
  würde nie greifen.
* Die Heimkehr wird nicht abgewartet, sondern über die Entfernung zur
  Heimzone vorhergesehen, damit der Raum bei der Ankunft schon warm ist.
"""
from __future__ import annotations

import math

ERDRADIUS_KM = 6371.0


def entfernung_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Großkreisentfernung zweier Punkte in Kilometern."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * ERDRADIUS_KM * math.asin(math.sqrt(a))


def personen_status(states_index: dict, heim: tuple[float, float, float] | None) -> dict:
    """Für jede Person: zu Hause? wie weit weg?"""
    out = {}
    for entity_id, eintrag in states_index.items():
        if not entity_id.startswith("person."):
            continue
        attrs = eintrag.get("attributes", {}) or {}
        zuhause = eintrag.get("state") == "home"
        distanz = None
        if heim and not zuhause:
            try:
                lat = float(attrs.get("latitude"))
                lon = float(attrs.get("longitude"))
            except (TypeError, ValueError):
                lat = lon = None
            if lat is not None and lon is not None:
                distanz = round(entfernung_km(lat, lon, heim[0], heim[1]), 2)
        out[entity_id] = {
            "name": attrs.get("friendly_name", entity_id),
            "zuhause": zuhause,
            "zustand": eintrag.get("state"),
            "entfernung_km": distanz,
        }
    return out


def zustaendige(raum: dict, alle_personen: dict) -> list[str]:
    """Die für einen Raum maßgeblichen Personen; leere Liste heißt: alle."""
    personen = [p for p in (raum.get("personen") or []) if p in alle_personen]
    return personen or list(alle_personen.keys())


def praesenz_aktiv(raum: dict, states_index: dict) -> bool:
    for entity_id in raum.get("praesenz") or []:
        eintrag = states_index.get(entity_id)
        if eintrag and eintrag.get("state") == "on":
            return True
    return False


def raum_besetzt(raum: dict, states_index: dict, personen: dict) -> tuple[bool, str]:
    """Ist gerade jemand für diesen Raum da? Mit Begründung für das Protokoll."""
    if praesenz_aktiv(raum, states_index):
        return True, "Präsenzmelder meldet Bewegung"
    for entity_id in zustaendige(raum, personen):
        if personen[entity_id]["zuhause"]:
            return True, f"{personen[entity_id]['name']} ist zu Hause"
    return False, "niemand zu Hause"


def kommt_heim(raum: dict, personen: dict, schwelle_km: float) -> tuple[bool, str]:
    """Ist eine zuständige Person auf dem Heimweg, also näher als die Schwelle?"""
    if schwelle_km <= 0:
        return False, ""
    naechste, name = None, ""
    for entity_id in zustaendige(raum, personen):
        person = personen[entity_id]
        distanz = person.get("entfernung_km")
        if person["zuhause"] or distanz is None:
            continue
        if naechste is None or distanz < naechste:
            naechste, name = distanz, person["name"]
    if naechste is not None and naechste <= schwelle_km:
        return True, f"{name} ist noch {naechste:.1f} km entfernt"
    return False, ""
