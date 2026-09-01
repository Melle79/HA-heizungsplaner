"""Alles, was die Außentemperatur mit dem Sollwert macht.

Drei Dinge passieren hier:

* **Dämpfung** – ein Haus reagiert träge. Der Rohwert des Wetterdienstes
  springt, die gedämpfte Temperatur folgt ihm mit einer Zeitkonstante von
  einigen Stunden. Nur die gedämpfte Größe entscheidet über Sommerbetrieb.
* **Heizkurve** – je kälter es draußen ist, desto höher muss der Sollwert
  liegen, damit der Raum die gewünschte Temperatur wirklich erreicht.
* **Vorlaufzeit** – je kälter, desto früher muss die Heizung anlaufen.
"""
from __future__ import annotations

import math
import einheit


def daempfen(alt: float | None, neu: float | None, sekunden: float,
             zeitkonstante_stunden: float) -> float | None:
    """Exponentielle Glättung mit echter Zeitbasis.

    Der Regeltakt darf sich ändern oder ausfallen, ohne dass die Dämpfung
    dadurch schneller oder langsamer wird.
    """
    if neu is None:
        return alt
    if alt is None or zeitkonstante_stunden <= 0 or sekunden <= 0:
        return neu
    anteil = 1.0 - math.exp(-sekunden / (zeitkonstante_stunden * 3600.0))
    return alt + (neu - alt) * anteil


def korrektur(aussen: float | None, heizkurve: dict) -> float:
    """Aufschlag auf den Sollwert nach Außentemperatur, in Kelvin.

    Positiv, wenn es kälter als die Basistemperatur ist; negativ darüber.
    """
    if not heizkurve.get("aktiv") or aussen is None:
        return 0.0
    basis = float(heizkurve.get("basis_aussen", einheit.absolut(15.0)))
    steilheit = float(heizkurve.get("steilheit", 0.06))
    grenze = float(heizkurve.get("max_korrektur", 1.5))
    wert = steilheit * (basis - aussen)
    return round(max(-grenze, min(grenze, wert)), 2)


def sommerbetrieb(aussen_gedaempft: float | None, sommer: dict, aktuell: bool) -> bool:
    """Sommerbetrieb mit Hysterese – sonst kippt er an Grenztagen hin und her."""
    if not sommer.get("aktiv") or aussen_gedaempft is None:
        return False
    grenze = float(sommer.get("grenze", 16.0))
    hysterese = float(sommer.get("hysterese", 1.5))
    if aktuell:
        return aussen_gedaempft > grenze - hysterese
    return aussen_gedaempft > grenze


def vorlaufminuten(aussen: float | None, vorheizen: dict) -> int:
    """Wie lange vor dem Zeitplanwechsel die Heizung anlaufen soll."""
    if not vorheizen.get("aktiv"):
        return 0
    grund = float(vorheizen.get("grund_min", 30))
    je_grad = float(vorheizen.get("min_pro_grad", 2.0))
    obergrenze = float(vorheizen.get("max_min", 120))
    if aussen is None:
        return int(min(grund, obergrenze))
    # Der Bezugspunkt sind 15 °C – in Fahrenheit derselbe Punkt, andere Zahl.
    zuschlag = je_grad * max(0.0, einheit.absolut(15.0) - aussen)
    return int(min(grund + zuschlag, obergrenze))


def aussentemperatur(states_index: dict, entity_id: str) -> float | None:
    """Außentemperatur aus einer Wetter- oder Sensor-Entität lesen."""
    if not entity_id:
        return None
    eintrag = states_index.get(entity_id)
    if not eintrag:
        return None
    attrs = eintrag.get("attributes", {}) or {}
    if entity_id.startswith("weather."):
        rohwert = attrs.get("temperature")
    else:
        rohwert = eintrag.get("state")
    try:
        wert = float(rohwert)
    except (TypeError, ValueError):
        return None
    return wert if wert == wert else None
