# Änderungen

## 1.6.1

- Anleitung um das Rezept „ein Raum soll nur vor dem Auskühlen geschützt
  werden“ ergänzt, samt Prüffällen: ein Schaltpunkt als Untergrenze, keine
  Heizkurve, keine Anwesenheitsabsenkung – und eine Handeinstellung, die bis
  zum nächsten Schaltpunkt hält.

## 1.6.0

- Jeder Raum meldet jetzt nicht nur, **wann** der nächste Umschaltpunkt fällig
  ist, sondern auch **worauf** er stellt: Uhrzeit, Modus und Zielwert. Der
  Zeitpunkt allein sagt wenig – wer auf die Übersicht schaut, will wissen, was
  gleich passiert. Als Attribute an `sensor.heizungsplaner_raum_<name>`.

## 1.5.5

- **Ein Wechsel des Raumfühlers löst keinen Fensteralarm mehr aus.** Zwei
  Fühler in einem Raum zeigen selten dasselbe; der Sprung beim Umschalten sah
  aus wie ein Temperatursturz und schickte den Raum auf Frostschutz. Beim
  Quellenwechsel wird das Temperaturgedächtnis nun verworfen.

## 1.5.4

- Wird ein Raum umbenannt oder gelöscht, verschwindet jetzt auch seine Entität
  aus Home Assistant. Bisher blieb ein Geisterraum stehen: Die
  Discovery-Nachricht ist „retained“ und überlebte das Add-on.

## 1.5.3

- **Thermostate, die sich nicht abschalten lassen.** Im Betrieb beobachtet:
  Ein SwitchBot-Thermostat nimmt das „aus“ an und steht eine Minute später
  wieder auf `heat`. Der Planer hätte das bei jedem Takt wiederholt –
  Dauerfeuer, das nur Batterie kostet. Nach zwei vergeblichen Versuchen
  schließt er das Ventil nun über den Frostschutzwert und schreibt es ins
  Protokoll.

## 1.5.2

- Zeitzonenfehler in der Überwachung behoben: Die zeitzonenlose Ortszeit des
  Planers wurde als UTC gelesen, wodurch jedes Gerät um den Zeitzonenversatz
  zu alt erschien – im Sommer zwei Stunden. Bei einer Schweigefrist von sechs
  Stunden hätte das zu frühem Alarm geführt.

## 1.5.1

- Knopf „Probemeldung senden“ in den Einstellungen. Ob ein Meldeweg trägt,
  merkte man sonst erst im Ernstfall – und dann ist es zu spät.

## 1.5.0

**Überwachung der Thermostate.** Anlass: Während eines Urlaubs fielen vier
Thermostate wegen leerer Batterien aus, ohne dass es jemand mitbekam.

- Der Planer wacht über das **Lebenszeichen** jedes Thermostats. Eine
  Batteriewarnung allein trüge nicht weit – die SwitchBot-Geräte melden über
  Matter gar keinen Ladestand.
- Erkannt werden: verschwundene Entitäten, `unavailable`, ausbleibende
  Meldungen (Vorgabe: 6 Stunden) und – wo es eine Anzeige gibt – schwache
  Batterien.
- Gemeldet wird über frei wählbare `notify`-Dienste, **einmal beim Auftreten
  und einmal bei der Behebung**.
- Neue Entitäten `binary_sensor.heizungsplaner_stoerung` und
  `sensor.heizungsplaner_stoerungen` für eigene Automationen.

## 1.4.3

- Der Prüflauf liegt jetzt im Repository unter `heizungsplaner/tests/` und
  läuft ohne Home Assistant und ohne Fremdpakete.
- Anleitung um den Rückweg zur vorherigen Steuerung ergänzt.

## 1.4.2

- Abstand zwischen Name und Aufenthalt in der Personenübersicht.

## 1.4.1

- **Die Heimkehr-Erkennung sah nur die Entfernung an.** Wer eine Schule in
  einem Kilometer Abstand besucht, galt damit den ganzen Vormittag als „auf
  dem Heimweg", und die Anwesenheitsabsenkung des Kinderzimmers lief ins
  Leere. Jetzt zählt eine Person nur dann als heimkehrend, wenn sie zusätzlich
  **in keiner Zone steht** und ihre Entfernung über die letzten 15 Minuten um
  eine einstellbare Mindestannäherung (Vorgabe 0,3 km) abgenommen hat.
- Die Personenübersicht zeigt jetzt den Zonennamen („Realschule") statt einer
  Entfernung und vermerkt, wer näher kommt.

## 1.4.0

Die Oberfläche ist neu aufgebaut. Sie war über die vorangegangenen
Erweiterungen gewachsen, ohne dass die Anordnung mitgewachsen wäre.

- **Übersicht:** Eine Lage-Leiste über den Raumkacheln beantwortet die vier
  Fragen, die man zuerst stellt – Betriebszustand, Außentemperatur, wie viele
  Räume geregelt werden, wann der nächste Wechsel kommt. Die Kacheln zeigen
  Zielwert und Begründung; die Thermostate liegen darunter in einem
  aufklappbaren Fach statt immer sichtbar.
- **Raum-Dialog:** statt einer Scrollstrecke aus sieben Abschnitten nun fünf
  Reiter – Grundlagen, Temperaturen, Zeitplan, Belegung, Fühler und Melder.
- **Raumliste:** feste Spalten statt Fließtext, damit sich Räume vergleichen
  lassen.
- **Einstellungen:** in benannte Tafeln mit Unterabschnitten gegliedert.
- Zustände heißen auf Deutsch („Fenster offen“ statt „fenster“), Personen
  stehen als Kennzeichen statt in einer Tabelle, und das Ganze ist auf
  Handybreite brauchbar.

## 1.3.4

- Zuordnungsvorschläge sind kürzer gefasst und liegen ab dreien in einem
  zugeklappten Fach, damit sie die echten Hinweise nicht zudecken.

## 1.3.3

- Zuordnungsvorschläge lassen sich mit *Nicht nötig* dauerhaft abweisen. Ein
  Hinweisbalken, den man wegen Dauerrauschen überliest, ist schlechter als
  keiner.

## 1.3.2

- Nicht nur nachgerüstete Fensterkontakte, auch neue **Präsenz- und
  Bewegungsmelder** im Bereich eines Raumes werden zur Zuordnung angeboten.


## 1.3.1

- **Ein Präsenzmelder, der nichts meldet, gilt nicht als „niemand da“.** Bei
  einem ausgefallenen oder falsch eingetragenen Melder stünde ein Raum mit
  „nur der Präsenzmelder zählt“ sonst dauerhaft auf der Abwesenheitstemperatur,
  ohne dass es auffällt. Jetzt gilt er als belegt, und der Hinweisbalken meldet
  den stummen Melder.

## 1.3.0

- **Freigabe je Raum:** Ein Raum kann an einen Schalter in Home Assistant
  gehängt werden und bleibt kalt, solange der aus ist – für ein Gästezimmer,
  das nur bei Gästen geheizt werden soll. Fehlt der Schalter, wird der Raum
  normal geregelt und der Hinweisbalken meldet es.
- **Nur der Präsenzmelder zählt:** neue Raumoption für Räume wie ein Büro.
  Personen im Haus bleiben dann außer Betracht; auch das Vorheizen bei
  Heimkehr entfällt, sonst liefe die Heizung an, sobald jemand nach Hause
  fährt, ohne den Raum zu betreten.
- **Eigene Karenzzeit je Raum** – ein Bewegungsmelder, der nach zwei Minuten
  abfällt, braucht eine kürzere Nachlaufzeit als ein Wohnzimmer.

## 1.2.1

- Räume im Handbetrieb zeigen auf der Kachel den von Hand eingestellten Wert
  mit dem Zusatz „von Hand“. Meldet das Thermostat gar keinen Sollwert – die
  FRITZ-Geräte tun das in der Sommerpause nicht –, steht dort „Von Hand“ statt
  einer Zahl, die keine Zielvorgabe ist.

## 1.2.0

Neue Betriebsart je Raum: **von Hand, nur zu festen Zeiten absenken**.

- Der Raum wird von Hand gestellt; der Planer greift allein zu den Zeitpunkten
  des Plans ein und lässt ihn sonst unangetastet, auch wenn jemand hochdreht.
- Ein Absenkzeitpunkt überschreibt die Handeinstellung ausdrücklich – dafür
  ist er da. Ein verpasster Zeitpunkt wird nicht nachgeholt.
- Fenster, Urlaub und Sommerbetrieb greifen weiterhin; der vorgefundene
  Sollwert wird gemerkt und danach wiederhergestellt, damit der Raum nach
  einmal Lüften nicht auf Frostschutz stehen bleibt.

## 1.1.2

- Türkontakte werden nur noch über die Geräteklasse `door` erkannt, nicht mehr
  über das Wort „Tür“ im Namen. Sonst galten die Nebenmelder eines Thermostats,
  dessen Gerät „Heizung Eingangstür“ heißt (Sommermodus, Tastensperre), alle
  als Fensterkontakt.

## 1.1.1

- Die Erkennung von Fensterkontakten trennt jetzt zwei Fallgruben ab: Die
  Öffnungszeiten von Tankstellen kommen als `device_class: opening` und sind
  keine Kontakte; die Diagnosemelder eines Rolladens („Obstacle Detection“,
  „Blocking Detection“, „Sun Program Active“) führen das Fenster nur im Namen,
  an dem sie hängen.

## 1.1.0

Fensterkontakte lassen sich jetzt schrittweise nachrüsten.

- Die Auswahl der Fensterkontakte ist nach Bereich gruppiert und enthält nur
  noch, was nach Geräteklasse oder Namen ein Kontakt ist. Alles übrige Binäre
  steht getrennt unter „Sonstige Melder“.
- Ein neuer Kontakt im Bereich eines Raumes wird auf der Übersicht gemeldet,
  mit Knopf „Zuordnen“, der den Raum mit vorgewähltem Kontakt öffnet.
- **Ein Kontakt, der nichts meldet, gilt nicht mehr als „geschlossen“.** Bei
  leerer Batterie oder gestörtem Funk fällt der Raum auf die
  Temperatursturz-Erkennung zurück, statt blind zu werden; die Übersicht warnt.
- Sobald ein Raum verlässliche Kontakte hat, entscheiden allein sie. Die neue
  Raumoption „Zusätzlich auf Temperatursturz achten“ schaltet beides zu.
- Die Ersteinrichtung übernimmt Fensterkontakte und Präsenzmelder des Bereichs
  gleich mit.

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
