"""Temperatureinheit: Celsius oder Fahrenheit, wie Home Assistant sie führt.

Home Assistant rechnet Klima-Entitäten in die Einheit seines Maßsystems um.
Ein Thermostat in einem amerikanischen Haushalt meldet also 68 und erwartet
68 – der Planer muss die Zahlen nicht umrechnen, sondern nur richtig deuten.

Falsch wären dagegen alle **festen** Werte: Ein Komfortwert von 21 ist in
Fahrenheit bittere Kälte, eine Sommergrenze von 16 ebenso. Diese Datei hält
deshalb die Vorgaben in Celsius und rechnet sie beim Anlegen um.

Zwei Arten von Werten, die man nicht verwechseln darf:

* **absolute** Temperaturen (21 °C → 69,8 °F) – Sollwerte, Grenzen, Schwellen;
* **Differenzen** (1,5 K → 2,7 °F) – Hysterese, Temperatursturz, der Aufschlag
  der Heizkurve. Wer sie wie absolute Werte umrechnet, addiert 32 auf eine
  Spanne und bekommt Unsinn.

Die Steilheit der Heizkurve bleibt in beiden Systemen dieselbe Zahl: Sie ist
ein Verhältnis von Differenz zu Differenz und damit einheitenlos.
"""
from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)

CELSIUS = "°C"
FAHRENHEIT = "°F"

_einheit = CELSIUS


def einheit_setzen(wert: str | None) -> str:
    """Einheit aus Home Assistant übernehmen (``/config`` → ``unit_system``)."""
    global _einheit
    text = (wert or "").strip().upper()
    _einheit = FAHRENHEIT if "F" in text and "C" not in text else CELSIUS
    return _einheit


def einheit() -> str:
    return _einheit


def ist_fahrenheit() -> bool:
    return _einheit == FAHRENHEIT


# ── Umrechnen ───────────────────────────────────────────────────────────────

def absolut(celsius: float, ziel: str | None = None) -> float:
    """Eine Temperatur aus der Vorgabe (Celsius) in die geltende Einheit."""
    if (ziel or _einheit) == FAHRENHEIT:
        return round(celsius * 9 / 5 + 32, 1)
    return round(float(celsius), 1)


def nach_celsius(wert: float, quelle: str | None = None) -> float:
    if (quelle or _einheit) == FAHRENHEIT:
        return round((float(wert) - 32) * 5 / 9, 1)
    return round(float(wert), 1)


def differenz(kelvin: float, ziel: str | None = None) -> float:
    """Eine Spanne (Kelvin) in die geltende Einheit – ohne den Nullpunkt."""
    if (ziel or _einheit) == FAHRENHEIT:
        return round(float(kelvin) * 9 / 5, 1)
    return round(float(kelvin), 1)


def differenz_nach_kelvin(wert: float, quelle: str | None = None) -> float:
    if (quelle or _einheit) == FAHRENHEIT:
        return round(float(wert) * 5 / 9, 2)
    return round(float(wert), 2)


def umrechnen(wert: float, von: str, nach: str, spanne: bool = False) -> float:
    """Einen gespeicherten Wert von einer Einheit in die andere bringen."""
    if von == nach:
        return round(float(wert), 1)
    if spanne:
        return (round(float(wert) * 9 / 5, 1) if nach == FAHRENHEIT
                else round(float(wert) * 5 / 9, 1))
    return (round(float(wert) * 9 / 5 + 32, 1) if nach == FAHRENHEIT
            else round((float(wert) - 32) * 5 / 9, 1))


def schritt() -> float:
    """Kleinste sinnvolle Änderung: ein halbes Grad, in Fahrenheit ein ganzes.

    Thermostate in Fahrenheit stellen üblicherweise in ganzen Graden; ein
    halber Grad Fahrenheit wäre feiner als die Geräte auflösen.
    """
    return 1.0 if ist_fahrenheit() else 0.5
