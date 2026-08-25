# Heizungsplaner

Ein Home-Assistant-Add-on, das Heizkörperthermostate vorausschauend stellt –
nach Zeitplan, Außentemperatur und Anwesenheit.

Statt fester Uhrzeiten je Thermostat rechnet der Planer für jeden Raum in
jedem Takt einen Sollwert aus und begründet ihn. In der Oberfläche steht nicht
nur, dass das Wohnzimmer 21,5 °C bekommt, sondern warum: „Vorheizen für
komfort um 12:30 Uhr (50 Minuten Vorlauf) · Heizkurve +0,6 K“.

## Was der Planer berücksichtigt

* **Zeitplan je Raum** – Umschaltpunkte für Komfort, Eco, Nacht und Aus,
  getrennt nach Schultagen und schulfreien Tagen.
* **Außentemperatur** – eine Heizkurve führt den Sollwert nach: je kälter
  draußen, desto höher der Sollwert. Bei milder Witterung geht die Anlage in
  den Sommerbetrieb und schließt die Ventile.
* **Anwesenheit je Raum** – jedem Raum lassen sich die zuständigen Personen
  zuordnen. Ist niemand von ihnen da, senkt der Planer nach einer Karenzzeit
  ab; nähert sich jemand dem Haus, heizt er wieder vor.
* **Vorheizen** – der Vorlauf richtet sich nach der Außentemperatur. Bei 12 °C
  reichen 30 Minuten, bei −10 °C sind es zwei Stunden.
* **Fenster** – über Fensterkontakte oder, wo es keine gibt, über den
  Temperatursturz im Raum. Nachgerüstete Kontakte meldet der Planer von selbst
  zur Zuordnung; fällt einer aus, gilt er nicht als „geschlossen“.
* **Urlaub** – ein Schalter in Home Assistant legt das ganze Haus auf die
  Urlaubstemperatur.
* **Überwachung** – meldet ein Thermostat sich nicht mehr, kommt eine
  Benachrichtigung. Weil die Geräte keinen Batteriestand liefern, wacht der
  Planer über das Lebenszeichen statt über die Batterie.
* **Handbetrieb je Raum** – wer einen Raum selbst stellen will, lässt den
  Planer nur zu festen Zeiten absenken. Dazwischen rührt er ihn nicht an.
* **Freigabe je Raum** – ein Gästezimmer wird nur geheizt, wenn ein Schalter
  in Home Assistant es freigibt.
* **Partytaste** – hebt die gewählten Räume für ein paar Stunden auf Komfort
  und stellt sich danach von selbst zurück.

## Installation

1. In Home Assistant unter **Einstellungen → Add-ons → Add-on-Store** über das
   Dreipunktmenü **Repositories** öffnen und diese Adresse hinzufügen:

   ```
   https://github.com/Melle79/HA-heizungsplaner
   ```

2. Das Add-on **Heizungsplaner** installieren und starten.
3. Die Oberfläche öffnen. Sie startet im **Trockenlauf**: Der Planer rechnet
   und protokolliert, stellt aber noch kein Thermostat.
4. Über **Räume aus Home Assistant übernehmen** die Räume anlegen lassen,
   Zeitpläne und Temperaturen prüfen.
5. Wenn das Ergebnis stimmt: in den Einstellungen den Trockenlauf abschalten.

Die ausführliche Anleitung steht in [DOCS.md](heizungsplaner/DOCS.md).

## Entitäten in Home Assistant

Über MQTT legt das Add-on ein Gerät „Heizungsplaner“ an:

| Entität | Bedeutung |
|---|---|
| `sensor.heizungsplaner_status` | Kurzfassung des Betriebszustands |
| `sensor.heizungsplaner_aussentemperatur_gedaempft` | geglättete Außentemperatur |
| `binary_sensor.heizungsplaner_sommerbetrieb` | Sommerbetrieb aktiv |
| `binary_sensor.heizungsplaner_trockenlauf` | Trockenlauf aktiv |
| `sensor.heizungsplaner_raum_<name>` | Zielwert je Raum, mit Begründung als Attribut |
| `switch.heizungsplaner_party` | Partytaste, mit Restzeit als Attribut |
| `binary_sensor.heizungsplaner_stoerung` | ein Thermostat meldet sich nicht mehr; Meldungen nach Schwere getrennt als Attribute |
| `sensor.heizungsplaner_stoerungen` | Zahl der ausgefallenen Thermostate |

## Prüflauf

Die Regellogik lässt sich ohne Home Assistant und ohne Fremdpakete prüfen:

```
python3 heizungsplaner/tests/test_logik.py
```

Geprüft werden Zeitplan über Tagesgrenzen, Heizkurve und Sommerhysterese,
Anwesenheit samt Heimkehr, Fenstererkennung, die Betriebsart „nur absenken“
und das Schreiben auf Flanke. Etliche Fälle stehen dort, weil sie einmal
falsch waren – etwa eine Schule in einem Kilometer Entfernung, die das
Kinderzimmer den ganzen Vormittag als „auf dem Heimweg“ gelten ließ.

## Lizenz

MIT
