# Änderungen

## 1.8.10

- **„Mittelwert der Thermostate“ sagt jetzt, welcher.** Gemeint waren immer
  die Thermostate des Raumes – die im Reiter *Grundlagen* angehakten –, aber
  das stand nirgends. Der Hinweis nennt sie beim Namen und zählt sie mit; er
  folgt der Auswahl, während man sie ändert.

## 1.8.9

- **Geräte werden angehakt statt markiert.** Thermostate, Präsenzmelder,
  Fensterkontakte, Personen und Meldewege stehen jetzt in Häkchenlisten. In
  einer Mehrfachauswahl musste man scrollen und eine Markierung deuten, um zu
  sehen, was zugeordnet ist.
- Eine Zeile je Gerät: Name und Entitäts-ID laufen zusammen und werden am Ende
  gekürzt, der volle Text steht im Tooltip. Die ID entfällt, wo sie dem Namen
  entspricht – bei den Meldewegen stand sonst alles doppelt.
- Der Knopf *Zuordnen* aus dem Hinweisbalken setzt das Häkchen und scrollt die
  Zeile in die Mitte.

## 1.8.8

- **Die Auswahllisten im Raum lassen sich filtern.** Über jeder Liste steht
  jetzt ein Suchfeld und ein Häkchen „nur dieser Raum“. Bisher standen unter
  den Fensterkontakten des Wohnzimmers auch die Haustür, der Briefkasten und
  gut zweihundert sonstige Melder.
- Als „gehört zu diesem Raum“ zählt nicht nur der Bereich, sondern auch der
  Name: `binary_sensor.heizung_wohnzimmer_offenes_fenster_erkannt` trägt gar
  keinen Bereich, ein reiner Bereichsfilter hätte im Wohnzimmer genau den
  Kontakt verborgen, den man dort sucht.
- Die Gruppe **Sonstige Melder** erscheint erst beim Suchen. Sie ungefragt
  unter die fünf echten Kontakte zu hängen machte die Liste unbrauchbar.
- Zugeordnete Geräte bleiben immer sichtbar, gleich wie gefiltert wird – eine
  ausgeblendete Zuordnung ginge beim Speichern verloren.
- Die Thermostatliste ist jetzt ebenfalls nach Bereich gruppiert, der eigene
  Bereich zuoberst.

## 1.8.7

- **Eigenes Icon und Logo.** Ein Heizkörper, darüber die Stufenkurve eines
  Tagesplans – im Add-on-Store und in der Seitenleiste stand bisher ein
  allgemeines Symbol.
- **Dokumentation mit Bildern.** README und Anleitung zeigen jetzt die
  Oberfläche: Übersicht, Räume, Raum-Dialog, Einstellungen und Protokoll. Die
  Anleitung beginnt mit einem Rundgang und einer Tabelle der Zustandsworte.
- In der Anleitung fehlten in der Rangfolge die Freigabe und die Partytaste;
  die Tabelle stimmt jetzt mit der Regelkette überein. Der Abschnitt über den
  Knopf „Jetzt prüfen“ stand zweimal darin.
- Beim Öffnen eines Raumes lag der Fokus auf „Schließen“. Er sitzt jetzt im
  Namensfeld, wenn ein Raum neu angelegt wird, und sonst nirgends.

## 1.8.6

- Der Knopf „Jetzt rechnen“ heißt jetzt **„Jetzt prüfen“**, erklärt sich beim
  Überfahren und meldet nach dem Durchlauf, wie viele Thermostate gestellt
  wurden – oder dass nichts zu tun war. Vorher blieb offen, was er überhaupt
  bewirkt.

## 1.8.5

- Die Dashboard-Karten liegen jetzt im Repository unter
  `heizungsplaner/dashboard/`: als fertige YAML-Fassung zum Einfügen, dazu der
  Baukasten und ein Erzeuger. Bisher gab es sie nur auf dem Rechner, von dem
  aus sie eingespielt wurden.

## 1.8.4

- **Im Raum-Dialog ließ sich das Ende nicht erreichen.** Die Innenhöhe war
  ausgerechnet (`84vh − 168px`); bei niedrigen Fenstern ging die Rechnung nicht
  auf und die Fußzeile legte sich über den Inhalt. Der Dialog ist jetzt ein
  Flex-Behälter – Kopf, Reiter und Fußzeile behalten ihre Höhe, das Blatt
  dazwischen nimmt den Rest und scrollt. Geprüft bis hinunter zu 300 Pixeln
  Fensterhöhe.
- Beim Wechsel des Reiters beginnt der Inhalt wieder oben.

## 1.8.3

- Die Störungsentität trennt Meldungen nach Schwere (`fehler`, `warnungen`
  samt Anzahl). Damit kann ein Dashboard Ausfälle und bloße Hinweise
  unterschiedlich darstellen, statt beides in eine Liste zu werfen.

## 1.8.1

- Das Protokoll färbt Einträge nach ihrer Schwere: Störungen rot, Fehlschläge
  und Handeingriffe gelb, Entwarnungen grün. Die Einordnung geschieht auch
  beim Lesen, damit bereits vorhandene Einträge mitgefärbt werden.

## 1.8.0

- **Der Planer setzt aus, solange Home Assistant startet.** Nach einem Neustart
  liefert Home Assistant seine Entitäten nach und nach; die Oberfläche meldete
  in dieser Phase ein Dutzend angeblich verschwundener Thermostate und Melder.
  Vor jedem Takt wird nun geprüft, ob Home Assistant `RUNNING` meldet – sonst
  wird nicht geschaltet, nichts gemeldet und nichts benachrichtigt.

## 1.7.6

- **Veraltete Batteriestände warnen nicht mehr.** Manche Geräte melden den
  Ladestand nur bei Änderung; nach einem Batteriewechsel steht dort noch der
  alte Wert, und die Warnung schickte jemanden nach Batterien, die längst
  gewechselt waren. Stände, die älter als zwölf Stunden sind, bleiben
  unberücksichtigt; die Meldung nennt jetzt die Uhrzeit der Messung.

## 1.7.4

- **Ein verschluckter Befehl wird nicht mehr für einen Handeingriff gehalten.**
  Im Betrieb aufgefallen: Ein Thermostat quittierte den Sollwert und stand
  danach unverändert da. Nach Ablauf der Bestätigungsfrist hätte der Planer das
  als Handeingriff gewertet und sich bis zum nächsten Zeitplanwechsel
  zurückgezogen – der Raum wäre auf einem Wert geblieben, den niemand wollte.
  Jetzt merkt er sich den Wert vor dem Befehl: Steht das Gerät noch genau
  darauf, versucht er es erneut und meldet es nach drei Fehlschlägen.

## 1.7.3

- Die Partytaste meldet die Restzeit als fertigen Text (`anzeige`), etwa
  „noch 2 h 47 min, bis 19:03 Uhr“ – die Kachel zeigt damit die verbleibende
  Zeit statt eines „Ein“, das ohnehin am Schalter steht.
- Die Auswahl der Party-Räume speichert sich beim Anklicken selbst. Bisher
  hing sie am gemeinsamen „Speichern“ und wurde mitgeschrieben, sobald jemand
  nur die Dauer änderte – dabei konnte eine veraltete Liste die Auswahl still
  überschreiben.
- Party-Symbol in der Raumübersicht ergänzt.

## 1.7.2

- Die Partytaste liefert das Ende zusätzlich als fertige Uhrzeit
  (`bis_uhrzeit`). In Lovelace-Templates gibt es kein `strftime`; die
  Zeitrechnerei dort war eine Fehlerquelle, die im Zweifel eine ganze Karte
  lahmlegt.

## 1.7.1

- **Thermostate, die Sollwerte ablehnen, werden gemeldet.** Im Betrieb
  aufgefallen: Die beiden FRITZ!-Geräte stehen in der Sommerpause und nehmen
  nichts an – der Planer versuchte es bei jedem Takt aufs Neue. Nach drei
  Fehlschlägen gilt das jetzt als Störung, die Meldung nennt die Sommerpause
  als mögliche Ursache, und weitere Versuche erfolgen nur noch alle 30 Minuten.
- Die Partytaste liegt jetzt auch als Kachel auf der Dashboard-Ansicht.

## 1.7.0

**Partytaste.** Einmal drücken, und die gewählten Räume gehen für die
eingestellte Dauer (Vorgabe drei Stunden) auf Komfort. Danach stellt sie sich
von selbst zurück.

- Bedienbar über den Knopf in der Oberfläche (zeigt die Restzeit), über
  `switch.heizungsplaner_party` in Home Assistant und über `POST /api/party`.
- In den Einstellungen lässt sich festlegen, **welche Räume mitmachen** und mit
  welchem Sollwert.
- Rangfolge: vor Urlaub und Sommerbetrieb, aber nach dem offenen Fenster.

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
