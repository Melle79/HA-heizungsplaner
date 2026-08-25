# Änderungen

## 1.0.0

Erste Fassung.

- Zeitplan je Raum mit Umschaltpunkten für Komfort, Eco, Nacht und Aus,
  getrennt nach Schultagen und schulfreien Tagen
- Heizkurve nach Außentemperatur, mit Sommerbetrieb und Hysterese auf einer
  geglätteten Außentemperatur
- Anwesenheitsabsenkung je Raum mit zuständigen Personen, Karenzzeit und
  Heimkehr-Erkennung über die Entfernung zur Heimzone
- Vorheizen mit außentemperaturabhängigem Vorlauf
- Fenstererkennung über Kontakte oder Temperatursturz
- Handeingriffe werden erkannt und bis zum nächsten Zeitplanwechsel geachtet
- Schreiben ausschließlich auf Flanke, jedes Thermostat einzeln
- Assistent zur Übernahme der Räume aus den Bereichen in Home Assistant
- Statusentitäten über MQTT, Protokoll der Schaltvorgänge
- Trockenlauf als Auslieferungszustand
