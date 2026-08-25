# Änderungen

## 1.0.5

- Räume mit geschlossenem Ventil zeigen „Aus · Ventil zu“ statt der
  Frostschutztemperatur als große Zahl – die Zahl las sich wie ein Heizziel.
- Deutsches Dezimalkomma in der ganzen Oberfläche.

## 1.0.4

- Knopf „Dämpfung neu anlaufen lassen“ in den Einstellungen: verwirft die
  geglättete Außentemperatur, die dann wieder aus der Historie ansetzt.
- Beim Wechsel der Außentemperatur-Quelle geschieht das von selbst – der
  geglättete Wert der alten Quelle würde sonst tagelang nachwirken.

## 1.0.3

- Die gedämpfte Außentemperatur wird beim ersten Lauf aus der Historie von
  Home Assistant angesetzt. Vorher begann sie beim aktuellen Messwert – an
  einem kühlen Sommertag hätte der Planer dadurch die Heizung angeworfen,
  obwohl die Woche davor mild war.
- Die Zeitkonstante der Dämpfung liegt jetzt bei 24 statt 6 Stunden, näher an
  der üblichen Heizgrenzenbetrachtung.

## 1.0.2

- Der Einrichtungsassistent schlägt für Schlafzimmer eigene Temperaturen vor
  (Komfort 20 °C statt 23 °C).


## 1.0.1

- Die Bereichszuordnung des Einrichtungsassistenten läuft jetzt über eine
  Template-Abfrage statt über die Websocket-API. Diese steht einem Add-on
  nicht offen, weshalb zuvor alle Thermostate in einem Sammelraum „Ohne
  Bereich“ landeten.
- Thermostate ohne Bereich werden als abgeschalteter Raum vorgeschlagen,
  statt stillschweigend zu verschwinden.
- In der Oberfläche bleiben eingestellte Entitäten in den Auswahllisten
  erhalten, auch wenn Home Assistant sie gerade nicht meldet. Vorher konnte
  ein Speichern die Zuordnung löschen.
- Die Heizkurve wirkt nur noch auf Komfort-, Eco- und Nachttemperatur, nicht
  mehr auf Abwesenheits- und Haltewerte.

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
