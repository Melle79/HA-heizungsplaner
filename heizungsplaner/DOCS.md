# Heizungsplaner – Anleitung

## Wie der Sollwert zustande kommt

In jedem Takt (Standard: alle fünf Minuten) durchläuft jeder Raum dieselbe
Rangfolge. Der erste zutreffende Fall gewinnt, die späteren kommen nicht mehr
zum Zug:

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

## Anwesenheit

Jedem Raum lassen sich zuständige Personen zuordnen. Ohne Zuordnung zählt die
ganze Familie. Zusätzlich kann ein Präsenz- oder Bewegungsmelder den Raum als
besetzt melden.

Ist niemand Zuständiges da, wartet der Planer die **Karenzzeit** ab (Vorgabe:
45 Minuten), bevor er absenkt. Ein kurzer Gang zum Bäcker kostet damit nichts.

Die **Heimkehr** wird vorhergesehen: Ist eine zuständige Person näher als die
eingestellte Entfernung zur Heimzone, gilt der Raum wieder als belegt und wird
vorgeheizt. Grundlage sind die Koordinaten der `person`-Entität und der
Heimzone.

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

Zuerst zählen die eingetragenen Fensterkontakte. Wo es keine gibt, greift der
**Temperatursturz**: Fällt die Raumtemperatur um mehr als den eingestellten
Wert innerhalb des Zeitfensters, gilt das Fenster als offen. Danach bleibt der
Raum für die Sperrzeit auf Frostschutz, damit ein kurzes Stoßlüften nicht
sofort wieder gegengeheizt wird.

Der Planer führt dafür je Raum ein Temperaturgedächtnis über eine Stunde.
Als Raumtemperatur dient der eingetragene Fühler, sonst der Mittelwert der
`current_temperature` aller Thermostate des Raumes.

## Handeingriffe

Wird ein Thermostat von Hand verstellt – am Gerät, in Home Assistant oder per
Automation –, erkennt der Planer die Abweichung von seinem zuletzt
geschriebenen Wert und hält sich **bis zum nächsten Zeitplanwechsel** zurück.
Danach führt wieder der Plan. Abschaltbar über *Einstellungen → Betrieb*.

Funkthermostate melden verzögert. Deshalb wertet der Planer eine Abweichung
erst 15 Minuten nach dem eigenen Schreibvorgang als Handeingriff.

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
