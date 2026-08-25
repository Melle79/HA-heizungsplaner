# Heizungsplaner – Anleitung

## Wie der Sollwert zustande kommt

In jedem Takt (Standard: alle fünf Minuten) durchläuft jeder Raum dieselbe
Rangfolge. Der erste zutreffende Fall gewinnt, die späteren kommen nicht mehr
zum Zug:

Sie gilt für Räume in der Betriebsart *nach Zeitplan führen*; für
*nur absenken* siehe unten.

| Rang | Fall | Ergebnis |
|---|---|---|
| 1 | Raum im Planer abgeschaltet | Ventil zu |
| 2 | Fenster offen | Frostschutz, danach Sperrzeit |
| 3 | Urlaubsschalter an | Urlaubstemperatur |
| 4 | Sommerbetrieb | Ventil zu |
| 5 | Zeitplan | Komfort / Eco / Nacht, ggf. vorgezogen |
| 6 | niemand Zuständiges da | Abwesenheitstemperatur |
| 7 | Heizkurve | Aufschlag nach Außentemperatur |

Die Heizkurve gilt nur für gewollte Raumtemperaturen (Komfort, Eco, Nacht).
Auf die Abwesenheits-, Urlaubs- und Frostschutztemperatur wird sie **nicht**
angewandt: Das sind Haltewerte, kein Zielklima.

Jede Entscheidung trägt ihre Begründung mit. Sie steht auf der Raumkachel und
im Protokoll.

## Betriebsarten je Raum

**Nach Zeitplan führen** (Vorgabe) – der Planer bestimmt den Sollwert
durchgehend, wie in der Rangfolge oben beschrieben.

**Von Hand – nur zu festen Zeiten absenken** – der Raum wird von Hand gestellt,
am Thermostat oder in Home Assistant. Der Planer greift allein zu den
Zeitpunkten des Plans ein und lässt ihn sonst in Ruhe, auch wenn jemand
hochdreht. Für Räume, die man nach Bedarf warm macht und abends nur
zuverlässig heruntergefahren haben will – ein Gäste-WC etwa.

In dieser Betriebsart gelten Anwesenheit, Vorheizen und Heizkurve nicht; sie
setzen ein durchgehend geführtes Ziel voraus. Was weiter gilt:

* Ein **Absenkzeitpunkt** stellt die Temperatur seines Modus einmal ein. Er
  überschreibt dabei ausdrücklich eine Handeinstellung – dafür ist er da.
  Danach gehört der Raum wieder der Hand.
* Ein **verpasster** Zeitpunkt wird nicht nachgeholt. Startet das Add-on um
  22 Uhr, holt es die Absenkung von 21 Uhr nicht nach und überfährt so keine
  Handeinstellung. Innerhalb von 30 Minuten nach dem Zeitpunkt versucht es
  weiter – das überbrückt einen ausgefallenen Takt.
* **Fenster, Urlaub und Sommerbetrieb** greifen weiterhin. Der Planer merkt
  sich dabei den vorgefundenen Sollwert und **stellt ihn wieder her**, sobald
  der Sonderzustand vorbei ist. Ohne das bliebe der Raum nach einmal Lüften
  für immer auf Frostschutz stehen.

## Zeitplan

Ein Zeitplan besteht aus **Umschaltpunkten**, nicht aus Zeitfenstern. Jeder
Punkt sagt: ab dieser Uhrzeit, an diesen Wochentagen, gilt dieser Modus – bis
der nächste Punkt kommt. Der letzte Punkt eines Tages reicht über Mitternacht
in den nächsten. Dadurch kann keine Lücke entstehen, in der kein Modus gilt.

Jeder Punkt gilt wahlweise **immer**, nur an **Schultagen** oder nur an
**schulfreien** Tagen. Welcher Fall vorliegt, entscheidet die in den
Einstellungen hinterlegte Entität (hier: `input_boolean.wochenende_feiertag`).
Ist sie nicht gesetzt, greifen ausschließlich die „immer“-Punkte.

Vier Temperaturen je Raum:

* **Komfort** – wenn der Raum benutzt wird
* **Eco** – tagsüber, wenn der Raum nur bereitgehalten wird
* **Nacht** – Nachtabsenkung
* **Abwesend** – wenn niemand Zuständiges im Haus ist

Dazu **Nie unter** / **Nie über** als harte Grenzen des Raumes. Sie deckeln
auch die Heizkurve.

### Rezept: ein Raum soll nur vor dem Auskühlen geschützt werden

Für Räume, in denen man nicht heizen, aber auch nicht frieren will – ein
Schlafzimmer etwa:

* **ein einziger Schaltpunkt**, etwa `00:00 → Eco`,
* **Eco** auf die gewünschte Untergrenze, etwa 18 °C,
* **Heizkurve aus** – sie würde den Sollwert bei Kälte anheben und damit genau
  das tun, was hier nicht gewollt ist,
* **Anwesenheitsabsenkung aus** – die Untergrenze gilt unabhängig davon, ob
  jemand im Haus ist.

Der Sollwert steht dann rund um die Uhr auf 18 °C. Das Thermostat regelt
selbst: Es heizt erst, wenn der Raum darunter fällt, und sonst nie.

Eine Handeinstellung bleibt dabei möglich und hält **bis zum nächsten
Schaltpunkt** – bei einem einzigen Punkt also bis Mitternacht. Wer abends auf
21 °C dreht, findet am nächsten Morgen wieder die 18 °C vor.

Im Sommerbetrieb ist auch dieser Raum zu; die Untergrenze greift erst wieder,
wenn die gedämpfte Außentemperatur unter die Sommergrenze fällt.

## Heizkurve

```
Aufschlag = Steilheit × (Basis-Außentemperatur − Außentemperatur)
```

begrenzt auf den eingestellten Höchstwert. Mit den Vorgaben (Basis 15 °C,
Steilheit 0,06, Höchstwert 1,5 K) heißt das: bei 0 °C draußen +0,9 K, bei
−10 °C +1,5 K, bei 20 °C −0,3 K. Die Oberfläche rechnet die Beispiele beim
Verstellen mit.

Die Kurve gleicht aus, dass ein Heizkörper bei Kälte mehr Vorlauf braucht, um
dieselbe Raumtemperatur zu halten. Sie ersetzt keine Vorlauftemperatur­regelung
am Kessel.

## Sommerbetrieb

Die Außentemperatur wird exponentiell geglättet (Vorgabe: 24 Stunden
Zeitkonstante). Beim ersten Lauf holt sich der Planer den Anlauf aus der
Historie von Home Assistant, damit die Glättung nicht bei einem
Momentanwert beginnt. Steigt der geglättete Wert über die Grenze, schließen die
Ventile; er muss um die Hysterese darunter fallen, bevor wieder geheizt wird.
Ohne Glättung würde ein sonniger Februarnachmittag die Heizung abstellen.

Thermostate, die `off` können, werden abgeschaltet – das spart Batterie und
schließt das Ventil vollständig. Alle anderen bekommen den Frostschutzwert.

**Wenn ein Gerät sich nicht abschalten lässt:** Manche Matter-Thermostate
nehmen den Befehl an und stehen eine Minute später wieder auf `heat`. Ohne
Gegenmaßnahme schickt der Planer bei jedem Takt ein neues „aus“ – Dauerfeuer,
das nichts bewirkt außer die Batterie zu leeren. Nach zwei vergeblichen
Versuchen schließt er das Ventil deshalb dauerhaft über den Frostschutzwert
und vermerkt das im Protokoll. Meldet sich das Gerät später doch einmal als
abgeschaltet, gilt wieder der normale Weg.

## Partytaste

Einmal drücken, und die gewählten Räume gehen für die eingestellte Dauer auf
Komfort – gleich, was der Zeitplan sagt. Danach führt wieder der Plan; niemand
muss daran denken, die Taste zurückzustellen.

Zu finden an drei Stellen: als Knopf oben in der Oberfläche (mit Restzeit), als
`switch.heizungsplaner_party` in Home Assistant – also auch auf dem Dashboard,
per Sprachbefehl oder in Automationen – und über `POST /api/party`, wahlweise
mit abweichender Dauer (`{"stunden": 5}`).

**Welche Räume mitmachen**, steht in den Einstellungen unter *Partytaste*; ein
Schlafzimmer will man dort meist nicht dabei haben. Dieselbe Einstellung findet
sich auch im Raum selbst unter *Belegung*.

In der Rangfolge steht die Party **vor Urlaub und Sommerbetrieb**: Wer sie
drückt, ist im Haus und will es warm haben, gleich was der Kalender sagt. Nur
ein **offenes Fenster** bleibt stärker – dagegen anzuheizen wäre sinnlos. Läuft
gerade Sommerbetrieb, sagt die Begründung dazu, dass die Anlage möglicherweise
gar nicht heizt.

## Freigabe: Räume, die nur zeitweise gebraucht werden

Ein Raum kann an einen Schalter in Home Assistant gehängt werden (*Freigabe*).
Steht der auf aus, bleibt der Raum kalt – ganz gleich, was Zeitplan und
Anwesenheit sagen. Gedacht für ein Gästezimmer, das nur geheizt werden soll,
wenn tatsächlich Gäste da sind: Schalter an, und der hinterlegte Zeitplan
greift wie bei jedem anderen Raum.

Fehlt der Schalter in Home Assistant oder meldet er nichts, wird der Raum
**normal geregelt** und der Hinweisbalken meldet es. Einen Raum wegen eines
kaputten Schalters kalt zu lassen wäre die unangenehmere Überraschung.

## Anwesenheit

Jedem Raum lassen sich zuständige Personen zuordnen. Ohne Zuordnung zählt die
ganze Familie. Zusätzlich kann ein Präsenz- oder Bewegungsmelder den Raum als
besetzt melden.

**Nur der Präsenzmelder zählt** – für Räume, die man betritt und wieder
verlässt, statt sich dort aufzuhalten: ein Büro, eine Werkstatt. Dann bleiben
Personen außer Betracht, und allein der Melder im Raum entscheidet. Ohne diese
Einstellung wäre ein Raum ohne Personenzuordnung immer belegt, sobald irgendwer
im Haus ist, und der Melder bliebe wirkungslos.

In dieser Betriebsart ist auch das Vorheizen bei Heimkehr abgeschaltet: Sonst
liefe die Heizung an, sobald jemand nach Hause fährt, obwohl niemand den Raum
betritt.

**Ein Melder, der nichts meldet, gilt nicht als „niemand da“.** Bei einem
ausgefallenen oder falsch eingetragenen Melder stünde der Raum sonst dauerhaft
auf der Abwesenheitstemperatur, ohne dass es auffällt. Antwortet kein einziger
Melder des Raumes, gilt er als belegt und der Hinweisbalken meldet es.

Ist niemand Zuständiges da, wartet der Planer die **Karenzzeit** ab (Vorgabe:
45 Minuten), bevor er absenkt. Ein kurzer Gang zum Bäcker kostet damit nichts.
Jeder Raum kann eine eigene Karenzzeit bekommen – ein Büro, dessen
Bewegungsmelder nach zwei Minuten abfällt, braucht eine kürzere als ein
Wohnzimmer.

Die **Heimkehr** wird vorhergesehen. Dafür müssen drei Dinge zutreffen:

1. die Person ist näher als die eingestellte Entfernung zur Heimzone,
2. sie steht **in keiner Zone** – wer in der Schule oder im Büro sitzt, ist
   dort angekommen, auch wenn das nur einen Kilometer entfernt ist,
3. ihre Entfernung hat in den letzten 15 Minuten um die eingestellte
   **Mindestannäherung** abgenommen.

Die Entfernung allein genügt nicht. Liegt die Schule einen Kilometer
entfernt, wären die Kinder den ganzen Vormittag „nah" – ihre Zimmer würden
durchheizen und die Anwesenheitsabsenkung liefe ins Leere. Die
Mindestannäherung filtert zugleich das GPS-Rauschen heraus: Ein Wert von
0,3 km spricht nicht auf die hundert Meter an, um die eine ruhende Position
schwankt.

Geprüft wird ausschließlich auf `home`. Tracker, die unterwegs eigene
Standzonen melden statt `not_home`, funktionieren damit korrekt.

## Vorheizen

```
Vorlauf = Grundvorlauf + Zuschlag × (15 °C − Außentemperatur)
```

begrenzt auf den Höchstwert. Der Planer schaut voraus, wann der Zeitplan das
nächste Mal etwas Wärmeres verlangt, und zieht den Wechsel um den Vorlauf vor.
Auch mehrstufige Übergänge (Nacht → Eco → Komfort) werden erkannt.

## Fenstererkennung

Zwei Wege, in dieser Rangfolge:

**Fensterkontakte.** Was im Raum unter *Fensterkontakte* eingetragen ist,
entscheidet. Sobald ein Raum mindestens einen Kontakt hat, der etwas meldet,
tritt die Temperatursturz-Erkennung für diesen Raum zurück – ein echter
Kontakt ist genauer, und der Sturz schlägt gelegentlich grundlos an, wenn ein
anlaufender Heizkörper die Luft am Thermostatfühler verwirbelt. Wer beides
will, schaltet am Raum *Zusätzlich auf Temperatursturz achten* ein.

**Temperatursturz.** Für Räume ohne Kontakte: Fällt die Raumtemperatur um mehr
als den eingestellten Wert innerhalb des Zeitfensters, gilt das Fenster als
offen. Der Planer führt dafür je Raum ein Temperaturgedächtnis über eine
Stunde. Als Raumtemperatur dient der eingetragene Fühler, sonst der Mittelwert
der `current_temperature` aller Thermostate des Raumes.

Nach beiden Wegen bleibt der Raum für die Sperrzeit auf Frostschutz, damit ein
kurzes Stoßlüften nicht sofort wieder gegengeheizt wird.

### Kontakte nachrüsten

Neue Kontakte müssen nur in Home Assistant einem **Bereich** zugeordnet sein,
der einem Raum des Planers entspricht. Dann erscheint auf der Übersicht ein
Hinweis samt Knopf *Zuordnen*, der den Raum mit vorgewähltem Kontakt öffnet –
Speichern genügt. Dasselbe gilt für neue Präsenz- und Bewegungsmelder.

Was man dort nicht haben will, verschwindet mit *Nicht nötig* dauerhaft aus
den Hinweisen.

In der Auswahlliste stehen die Kontakte nach Bereich gruppiert. Als Kontakt
gilt, was die Geräteklasse `window`, `door` oder `opening` trägt **oder** ein
entsprechendes Wort im Namen führt – so werden auch die
„Offenes Fenster erkannt“-Meldungen mancher Thermostate gefunden, die ohne
Geräteklasse kommen. Alles übrige Binäre steht unter *Sonstige Melder*.

### Wenn ein Kontakt ausfällt

**Ein Kontakt, der nichts meldet, gilt nicht als „geschlossen“.** Eine leere
Batterie, ein abgezogener Funkstick oder ein noch nicht angelerntes Gerät
würde den Raum sonst stillschweigend blind machen. Meldet ein eingetragener
Kontakt weder `on` noch `off`, springt für diesen Raum die
Temperatursturz-Erkennung wieder ein, die Begründung sagt es
(„… melden nichts – ersatzweise Temperatursturz“), und auf der Übersicht steht
eine Warnung.

## Überwachung: wenn ein Thermostat ausfällt

Der Anlass ist ein Vorfall: Während eines Urlaubs fielen vier Thermostate wegen
leerer Batterien aus, und niemand bemerkte es.

Eine Batteriewarnung allein hilft dabei nicht. Die SwitchBot-Thermostate melden
über Matter **gar keinen Ladestand** – es gibt nichts zu überwachen. Was sie
melden, ist ihr Zustand, und zwar regelmäßig. Bleibt das aus, ist das Gerät tot,
gleich aus welchem Grund. Der Planer wacht deshalb über das **Lebenszeichen**:

| Fall | Wann |
|---|---|
| gibt es nicht mehr | die Entität ist aus Home Assistant verschwunden |
| nicht erreichbar | Zustand `unavailable` oder `unknown` |
| meldet sich nicht mehr | seit der Schweigefrist kein Lebenszeichen (Vorgabe 6 Stunden) |
| schwache Batterie | wo es eine Anzeige gibt, unterhalb der Schwelle (Vorgabe 20 %) |
| nimmt keine Sollwerte an | drei Schreibvorgänge in Folge abgelehnt |

Der letzte Fall ist nicht zwangsläufig ein Defekt: Ein FRITZ!-Thermostat in der
**Sommerpause** lehnt jeden Sollwert ab, solange dieser Modus läuft. Die
Meldung nennt das ausdrücklich, damit man nicht nach Batterien sucht, wo keine
fehlen. Vor der Heizperiode gehört die Sommerpause am Gerät oder in der
FRITZ!Box beendet – sonst bleibt der Raum kalt, ohne dass der Planer etwas
dagegen ausrichten könnte.

Nach drei Fehlschlägen versucht der Planer es nur noch alle 30 Minuten. Sonst
füllte ein solches Gerät bei jedem Takt das Protokoll, ohne dass sich etwas
ändert.

Gemeldet wird **auf Flanke**: einmal beim Auftreten, einmal bei der Behebung.
Eine Warnung, die stündlich erneut aufs Telefon kommt, wird nach dem dritten
Mal weggewischt und beim vierten Mal übersehen. Wird aus einer schwachen
Batterie ein Ausfall, gilt das als neue Nachricht.

Die Meldewege wählt man in den Einstellungen aus den `notify`-Diensten von Home
Assistant – für die Ferne taugt die Companion-App, für zu Hause zusätzlich die
dauerhafte Benachrichtigung in der Oberfläche. Jede Störung steht außerdem im
Protokoll und im Hinweisbalken.

Für eigene Automationen gibt es `binary_sensor.heizungsplaner_stoerung`
(Geräteklasse `problem`) mit den Meldungen als Attribut sowie
`sensor.heizungsplaner_stoerungen` mit der Zahl der ausgefallenen Geräte.

## Handeingriffe

Wird ein Thermostat von Hand verstellt – am Gerät, in Home Assistant oder per
Automation –, erkennt der Planer die Abweichung von seinem zuletzt
geschriebenen Wert und hält sich **bis zum nächsten Zeitplanwechsel** zurück.
Danach führt wieder der Plan. Abschaltbar über *Einstellungen → Betrieb*.

Funkthermostate melden verzögert. Deshalb wertet der Planer eine Abweichung
erst 15 Minuten nach dem eigenen Schreibvorgang als Handeingriff.

**Nicht jede Abweichung ist eine Hand.** Manche Geräte quittieren einen
Sollwert und setzen ihn trotzdem nicht um – sie stehen danach unverändert da.
Der Planer merkt sich deshalb, welcher Wert *vor* seinem Befehl am Gerät
stand: Ist es noch genau dieser, hat niemand gedreht, sondern das Gerät hat
den Befehl verschluckt. Er versucht es dann erneut und meldet es nach drei
Fehlschlägen als Störung. Diese Unterscheidung ist wichtig – als Handeingriff
gedeutet, zöge sich der Planer zurück und der Raum bliebe auf einem Wert, den
niemand gewollt hat.

## Wie geschrieben wird

Ein Sollwert geht nur dann an ein Thermostat, wenn dort tatsächlich etwas
anderes eingestellt ist – **auf Flanke, nicht auf Pegel**. Ein Add-on, das in
jedem Takt stur denselben Wert schreibt, wird zum Besitzer der Entität und
überfährt jede andere Bedienung.

Jedes Thermostat wird **einzeln** angesprochen. Ein Sammelaufruf würde an
einem einzigen abgeschalteten Gerät scheitern und alle übrigen mitreißen.
Nimmt ein Thermostat den Sollwert nicht an, schaltet der Planer es einmal auf
`heat` und versucht es erneut.

Der zuletzt geschriebene Wert liegt in `/data/zustand.json` und überlebt einen
Neustart. Ohne dieses Gedächtnis würde jeder Add-on-Start in jedes Thermostat
schreiben.

## Betriebsarten

**Trockenlauf** – der Planer rechnet, protokolliert und meldet über MQTT, aber
stellt kein Thermostat. Der richtige Zustand für die ersten Tage.

**Automatik aus** – der Planer rechnet nicht mehr in die Thermostate hinein
und lässt sie, wie sie sind.

### Zurück zur vorherigen Steuerung

1. Trockenlauf einschalten (oder Automatik aus).
2. Die zuvor abgeschalteten Zeitpläne und Automationen wieder aktivieren.

Die Thermostate behalten in beiden Fällen den zuletzt gestellten Wert – der
Planer räumt beim Abschalten nichts auf, damit ein versehentliches Umschalten
kein kaltes Haus hinterlässt.

## Ersteinrichtung

Der Assistent liest die Bereiche aus Home Assistant und legt je Bereich mit
Thermostat einen Raum an: mit den Thermostaten dieses Bereichs, einem üblichen
Zeitplan und – wo der Bereichsname einen Vornamen enthält – der zuständigen
Person. Gruppen-Helfer bleiben außen vor; der Planer stellt jeden Heizkörper
einzeln. Doppelt registrierte Geräte mit gleichem Anzeigenamen werden nur
einmal übernommen.

Der Vorschlag wird angezeigt, bevor er gespeichert wird. Danach gehören
Zeitpläne, Temperaturen und Personenzuordnung geprüft – geraten ist nicht
entschieden.

## Umstieg von der Scheduler-Integration

Solange beide laufen, schreiben zwei Systeme auf dieselben Sollwerte und
überstimmen sich gegenseitig. Deshalb:

1. Räume im Planer einrichten und einige Tage im Trockenlauf beobachten.
2. Das Protokoll gegen die tatsächlichen Zeiten halten.
3. Die Scheduler-Einträge für die Heizung **ausschalten**.
4. Erst dann den Trockenlauf abschalten.

Der Hinweisbalken der Oberfläche warnt, wenn ein Thermostat in zwei Räumen
steht – dann würden sich die beiden Räume gegenseitig verstellen.

## Dateien

| Datei unter `/data` | Inhalt |
|---|---|
| `config.json` | Räume, Zeitpläne, Einstellungen |
| `zustand.json` | zuletzt geschriebene Sollwerte, Laufzeitzustand je Raum |
| `logbuch.json` | Protokoll der letzten 500 Schaltvorgänge |
