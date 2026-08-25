# Heizungsplaner – Anleitung

Diese Anleitung erklärt, was der Planer tut und warum. Für die Installation
genügt die [README](https://github.com/Melle79/HA-heizungsplaner).

## Die Oberfläche

Vier Reiter: Übersicht, Räume, Einstellungen, Protokoll.

### Übersicht

Je Raum der Zielwert, die gemessene Temperatur und in einem Satz die
Begründung. Oben stehen die Außentemperatur, die Partytaste und der Knopf
*Jetzt prüfen*; darunter der Hinweisbalken, wenn etwas Aufmerksamkeit braucht.

![Übersicht mit allen Räumen, Zielwert und Begründung](https://raw.githubusercontent.com/Melle79/HA-heizungsplaner/main/heizungsplaner/doku/bilder/uebersicht.png)

Die Zustandsworte auf den Kacheln:

| Wort | Bedeutung |
|---|---|
| Komfort / Eco / Nacht | der Zeitplan führt |
| Vorheizen | der nächste Wechsel wird vorgezogen |
| Abwesend | niemand Zuständiges im Haus, Karenzzeit abgelaufen |
| Heimkehr | jemand nähert sich, der Raum wird wieder warm |
| Fenster offen | Frostschutz, danach Sperrzeit |
| Von Hand | jemand hat am Thermostat gedreht, der Planer hält sich zurück |
| Gesperrt | Freigabeschalter aus |
| Party | die Partytaste läuft |
| Sommer / Urlaub | Ventile zu bzw. Urlaubstemperatur |

### Räume

![Raumliste mit Betriebsart und Zahl der Thermostate](https://raw.githubusercontent.com/Melle79/HA-heizungsplaner/main/heizungsplaner/doku/bilder/raeume.png)

Jeder Raum öffnet sich in einem Dialog mit fünf Reitern. Unter **Grundlagen**
stehen Name, Betriebsart und die Thermostate des Raumes:

![Grundlagen eines Raumes: Betriebsart und zugeordnete Thermostate](https://raw.githubusercontent.com/Melle79/HA-heizungsplaner/main/heizungsplaner/doku/bilder/raum-grundlagen.png)

Der **Zeitplan** besteht aus Umschaltpunkten (siehe unten). *Vorlage einsetzen*
füllt einen leeren Plan mit einem üblichen Tagesablauf:

![Zeitplan mit Umschaltpunkten für Schultage und schulfreie Tage](https://raw.githubusercontent.com/Melle79/HA-heizungsplaner/main/heizungsplaner/doku/bilder/raum-zeitplan.png)

Unter **Belegung** steht, wer den Raum benutzt – zuständige Personen, ein
eigener Freigabeschalter, eine eigene Karenzzeit – und ob der Raum bei der
Partytaste mitmacht:

![Belegung: Freigabeschalter, zuständige Personen, Karenzzeit](https://raw.githubusercontent.com/Melle79/HA-heizungsplaner/main/heizungsplaner/doku/bilder/raum-belegung.png)

**Temperaturen** hält die vier Sollwerte und die harten Grenzen des Raumes.
Unter **Fühler und Melder** stehen Temperaturfühler, Präsenzmelder und
Fensterkontakte:

![Fühler und Melder mit Filterzeile über jeder Auswahlliste](https://raw.githubusercontent.com/Melle79/HA-heizungsplaner/main/heizungsplaner/doku/bilder/raum-melder.png)

Geräte werden **angehakt**; was zugeordnet ist, sieht man auf einen Blick.
Über jeder Liste sitzt eine Filterzeile – nötig, weil ein Haushalt schnell
mehrere hundert binäre Melder hat. Ohne sie stünde im Wohnzimmer auch der
Briefkastenkontakt zur Auswahl:

* **Häkchen „nur <Raum>“** – zeigt nur, was zu diesem Raum gehört. Das ist
  der Bereich in Home Assistant, aber auch der Name: In dieser Installation
  trägt ausgerechnet der Wohnzimmer-Fensterkontakt keinen Bereich, und ein
  reiner Bereichsfilter würde ihn verstecken. Das Häkchen erscheint nur, wenn
  es für den Raum überhaupt etwas zu finden gibt.
* **Suchfeld** – durchsucht Namen und Entitäts-ID. Sobald etwas darin steht,
  werden auch die *sonstigen Melder* durchsucht.
* Was **angehakt ist, bleibt immer sichtbar**, gleich wie gefiltert wird.
  Eine ausgeblendete Zuordnung würde beim Speichern verlorengehen.
* Rechts steht, wie viele Geräte die Liste gerade zeigt und wie viele davon
  angehakt sind.

Die Gruppe **Sonstige Melder** – alles Binäre, das kein Kontakt ist – bleibt
zunächst zugeklappt und erscheint erst beim Suchen. Die Zeile rechts sagt,
wie viele dort warten.

### Einstellungen

Alles, was fürs ganze Haus gilt: Takt, Heizkurve, Sommerbetrieb, Vorheizen,
Anwesenheit, Fenstererkennung, Urlaub, Partytaste, Überwachung und Meldewege.
Die Beispielwerte unter der Heizkurve rechnen beim Verstellen mit.

![Einstellungen mit Heizkurve und Sommerbetrieb](https://raw.githubusercontent.com/Melle79/HA-heizungsplaner/main/heizungsplaner/doku/bilder/einstellungen.png)

### Protokoll

Jede Änderung mit Begründung, die jüngste zuerst. Störungen sind rot
hinterlegt, Warnungen gelb – so ist auf einen Blick zu sehen, ob etwas
liegengeblieben ist.

![Protokoll der Schaltvorgänge mit Begründung](https://raw.githubusercontent.com/Melle79/HA-heizungsplaner/main/heizungsplaner/doku/bilder/protokoll.png)

## Wie der Sollwert zustande kommt

In jedem Takt (Standard: alle fünf Minuten) durchläuft jeder Raum dieselbe
Rangfolge. Der erste zutreffende Fall gewinnt, die späteren kommen nicht mehr
zum Zug:

Sie gilt für Räume in der Betriebsart *nach Zeitplan führen*; für
*nur absenken* siehe unten.

| Rang | Fall | Ergebnis |
|---|---|---|
| 1 | Raum im Planer abgeschaltet | Ventil zu |
| 2 | Freigabeschalter aus | Ventil zu |
| 3 | Fenster offen | Frostschutz, danach Sperrzeit |
| 4 | Partytaste läuft | Komfort, für die eingestellte Dauer |
| 5 | Urlaubsschalter an | Urlaubstemperatur |
| 6 | Sommerbetrieb | Ventil zu |
| 7 | Zeitplan, ggf. übersteuert | Komfort / Eco / Nacht, ggf. vorgezogen |
| 8 | niemand Zuständiges da | Abwesenheitstemperatur |
| 9 | Heizkurve | Aufschlag nach Außentemperatur |

Die Heizkurve gilt nur für gewollte Raumtemperaturen (Komfort, Eco, Nacht).
Auf die Abwesenheits-, Urlaubs- und Frostschutztemperatur wird sie **nicht**
angewandt: Das sind Haltewerte, kein Zielklima.

Jede Entscheidung trägt ihre Begründung mit. Sie steht auf der Raumkachel und
im Protokoll.

## Der Knopf „Jetzt prüfen“

Von selbst rechnet der Planer alle paar Minuten (einstellbar unter *Takt*) und
außerdem sofort, wenn sich an der Konfiguration etwas ändert. Der Knopf zieht
einen solchen Durchlauf vor: Zustände aus Home Assistant neu einlesen, für
jeden Raum entscheiden, und wo nötig die Thermostate stellen. Danach zeigt er
kurz, wie viele Thermostate dabei gestellt wurden – oder dass nichts zu tun
war.

Nützlich, wenn man eine Einstellung geändert hat und nicht auf den nächsten
Takt warten will.

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

## Übersteuerung: eine Regel statt des Zeitplans

Ein Raum kann Regeln bekommen, die den Zeitplan außer Kraft setzen. Eine Regel
besteht aus einem Modus und beliebig vielen Bedingungen; sie greift, solange
**alle** Bedingungen zutreffen.

![Homeoffice-Regel im Reiter Zeitplan](https://raw.githubusercontent.com/Melle79/HA-heizungsplaner/main/heizungsplaner/doku/bilder/uebersteuerung.png)

Der Anlass ist das Homeoffice. Das Wohnzimmer läuft nach einem Plan, der es
vormittags auf Eco stellt, weil dann üblicherweise niemand da ist. Arbeitet
jemand zu Hause, soll es warm bleiben – ohne Schalter, ohne Zeitplanumbau:

| Bedingung | Entität | Zustand |
|---|---|---|
| Werktag | `binary_sensor.workday_sensor` | ist an |
| keine Ferien | `calendar.ferien_feiertage_bayern` | ist aus |
| Isabel ist da | `person.isabel` | ist an |

Ergebnis: **Komfort** statt Eco. Trifft eine der drei nicht zu, führt wieder
der Zeitplan.

Als Bedingung taugt alles, was an oder aus sein kann: Schalter und Helfer,
Melder, Kalender (`on`, solange ein Termin läuft) und Personen. **Eine Person
zählt als „an", solange sie zu Hause ist** – wer in einer anderen Zone steht,
etwa im Büro, zählt als fort.

Die **Bezeichnung** der Regel ist frei. Sie steht später in der Begründung und
im Protokoll: „Homeoffice – komfort statt Zeitplan" ist dort lesbarer als die
Aufzählung dreier Entitäten. Ohne Bezeichnung werden die Bedingungen genannt.

Sind mehrere Regeln hinterlegt, gewinnt die oberste. Eine Entität, die nichts
meldet, lässt ihre Bedingung durchfallen – dann gilt schlicht der Zeitplan.

**Was die Übersteuerung nicht aushebelt:** ein offenes Fenster, den
Sommerbetrieb, den Urlaubsschalter und die Anwesenheitsabsenkung. Das ist
Absicht: Eine Regel, die sich verhakt, heizt so kein leeres Haus.

Der Modus *Aus* schließt das Ventil – für eine Regel, die einen Raum zeitweise
ganz stilllegt. Zum dauerhaften Sperren gibt es die
[Freigabe](#freigabe-räume-die-nur-zeitweise-gebraucht-werden); sie steht in
der Rangfolge weit oben und gilt auch gegen die Partytaste.

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

**Die geräteeigene Erkennung eines Thermostats ist kein Kontakt.** Manche
Thermostate – die FRITZ!Smart Thermo etwa – erkennen ein offenes Fenster
selbst am Sturz an ihrem eigenen Fühler und melden das als eigene Entität.
Der Planer nimmt eine solche Meldung als Auslöser an, lässt die
Sturz-Erkennung daneben aber weiterlaufen. Sie macht schließlich dasselbe,
nur im Gerät, und schweigt, sobald das Gerät abgeschaltet ist oder in der
Sommerpause steht. Ein Raum, dessen einziger Eintrag eine solche Meldung ist,
stünde sonst ohne Fenstererkennung da. In der Auswahlliste sind sie als
*geräteeigene Erkennung* gekennzeichnet.

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

In der Auswahlliste stehen die Kontakte nach Bereich gruppiert, der eigene
Bereich zuoberst. Als Kontakt gilt, was die Geräteklasse `window`, `door` oder
`opening` trägt **oder** ein entsprechendes Wort im Namen führt – so werden
auch die „Offenes Fenster erkannt“-Meldungen mancher Thermostate gefunden, die
ohne Geräteklasse kommen. Alles übrige Binäre steht unter *Sonstige Melder*
und erscheint erst, wenn man ins Suchfeld tippt.

### Wenn ein Kontakt ausfällt

**Ein Kontakt, der nichts meldet, gilt nicht als „geschlossen“.** Eine leere
Batterie, ein abgezogener Funkstick oder ein noch nicht angelerntes Gerät
würde den Raum sonst stillschweigend blind machen. Meldet ein eingetragener
Kontakt weder `on` noch `off`, springt für diesen Raum die
Temperatursturz-Erkennung wieder ein, die Begründung sagt es
(„… melden nichts – ersatzweise Temperatursturz“), und auf der Übersicht steht
eine Warnung.

## Während Home Assistant startet

Nach einem Neustart liefert Home Assistant seine Entitäten nach und nach. Wer
in dieser Phase rechnet, hält die noch nicht geladenen Geräte für verschwunden.
Der Planer fragt deshalb vor jedem Takt den Zustand von Home Assistant ab und
setzt aus, solange dieser nicht `RUNNING` ist – kein Schalten, keine Störung,
keine Benachrichtigung. Die Oberfläche zeigt in dieser Zeit einen Hinweis statt
einer Mängelliste.

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
| schwache Batterie | wo es eine Anzeige gibt, unterhalb der Schwelle (Vorgabe 20 %) und **nicht älter als zwölf Stunden** |
| nimmt keine Sollwerte an | drei Schreibvorgänge in Folge abgelehnt |
| steht in der Sommerpause | das Gerät meldet `summer`, obwohl geheizt werden soll |

Beim Batteriestand zählt auch sein Alter. Manche Geräte melden ihn nur bei
Änderung – nach einem Batteriewechsel steht dort womöglich noch tagelang der
alte Wert. Eine Warnung darauf wäre falsch, deshalb bleibt ein Stand, der
älter als zwölf Stunden ist, unberücksichtigt. Die Meldung nennt umgekehrt die
Uhrzeit der Messung, damit man sie einordnen kann.

**Die Sommerpause meldet der Planer von sich aus**, sobald der Sommerbetrieb
endet und ein Gerät noch auf `summer` steht. Das ist der Zeitpunkt, an dem der
Hinweis etwas nützt: Vorher wäre er eine Nachricht über den Sommer, nachher
bliebe der Raum kalt. Beenden lässt sie sich nur in der FRITZ!Box – unter
*Smart Home → Gerät bearbeiten → Zeitschaltung → Sommerzeit*. Home Assistant
kann es nicht: Die Integration zeigt den Modus an, und die Liste der
Voreinstellungen enthält dann nichts außer `summer`.

Bis dahin gilt auch der Fall darüber: Ein Gerät in der Sommerpause lehnt jeden
Sollwert ab. Die Meldung nennt das ausdrücklich, damit man nicht nach
Batterien sucht, wo keine fehlen.

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

## Trockenlauf und Automatik aus

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

## Karten fürs Dashboard

Unter `heizungsplaner/dashboard/` im Repository liegt eine fertige Übersicht
zum Einfügen: die Partytaste mit Restzeit, eine Störungsanzeige, die nur
erscheint, wenn es etwas zu melden gibt, und eine Tabelle aller Räume mit
Zielwert, Ist-Temperatur, Zustand und dem nächsten Schaltpunkt. Die Karten
lesen ausschließlich die MQTT-Entitäten und funktionieren deshalb auch von
unterwegs.

## Dateien

| Datei unter `/data` | Inhalt |
|---|---|
| `config.json` | Räume, Zeitpläne, Einstellungen |
| `zustand.json` | zuletzt geschriebene Sollwerte, Laufzeitzustand je Raum |
| `logbuch.json` | Protokoll der letzten 500 Schaltvorgänge |
