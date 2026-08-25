#!/usr/bin/env python3
"""Trockenprüfung der Regellogik – ohne Home Assistant, ohne Fremdpakete.

Aufruf aus dem Repo:

    python3 heizungsplaner/tests/test_logik.py

Geprüft wird alles, was ohne laufende Anlage prüfbar ist: Zeitplan über
Tagesgrenzen, Heizkurve und Sommerhysterese, Anwesenheit samt Heimkehr,
Fenstererkennung, die Betriebsart „nur absenken“ und das Schreiben auf Flanke.
Mehrere dieser Fälle stehen hier, weil sie in der Praxis einmal falsch waren –
etwa die Schule in einem Kilometer Entfernung, die das Kinderzimmer den ganzen
Vormittag als „auf dem Heimweg“ gelten ließ.
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta

os.environ["DATA_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "backend"))

import anwesenheit
import regelung
import store
import witterung
import zeitplan as zp

fehler = []


def pruefe(bedingung, text):
    if bedingung:
        print(f"  ok   {text}")
    else:
        print(f"  FEHL {text}")
        fehler.append(text)


print("\n=== Zeitplan ===")
plan = zp.standardplan("wohnraum")
# Montag, 25.08.2026 ist ein Dienstag -> nehmen wir einen echten Montag
montag = datetime(2026, 8, 24, 6, 0)      # Montag 06:00
pruefe(zp.aktueller_eintrag(plan, montag, False)["modus"] == "komfort",
       "Montag 06:00 Schultag -> komfort (05:30-Punkt)")
pruefe(zp.aktueller_eintrag(plan, montag.replace(hour=8), False)["modus"] == "eco",
       "Montag 08:00 Schultag -> eco")
pruefe(zp.aktueller_eintrag(plan, montag.replace(hour=14), False)["modus"] == "komfort",
       "Montag 14:00 Schultag -> komfort")
pruefe(zp.aktueller_eintrag(plan, montag.replace(hour=22), False)["modus"] == "nacht",
       "Montag 22:00 -> nacht")
nacht = zp.aktueller_eintrag(plan, montag.replace(hour=2), False)
pruefe(nacht and nacht["modus"] == "nacht",
       "Montag 02:00 -> nacht von gestern Abend (über Mitternacht)")
sonntag = datetime(2026, 8, 23, 10, 0)
pruefe(zp.aktueller_eintrag(plan, sonntag, True)["modus"] == "komfort",
       "Sonntag 10:00 schulfrei -> komfort (09:00-Punkt)")
pruefe(zp.aktueller_eintrag(plan, sonntag.replace(hour=7), True)["modus"] == "nacht",
       "Sonntag 07:00 schulfrei -> noch nacht")

wechsel = zp.naechster_wechsel(plan, montag.replace(hour=8), False)
pruefe(wechsel and wechsel[1]["start"] == "12:30", "nächster Wechsel nach 08:00 ist 12:30")

raum = dict(store.STANDARD_RAUM, name="Test", zeitplan=plan,
            komfort=23.0, eco=19.0, nacht=19.0, abwesend=17.0)
waermer = zp.naechster_waermerer_wechsel(raum, montag.replace(hour=4), False, 19.0, 8.0)
pruefe(waermer and waermer[1]["start"] == "05:30", "nächster wärmerer Wechsel ab 04:00 = 05:30")

print("\n=== Witterung ===")
pruefe(witterung.korrektur(-10, {"aktiv": True, "basis_aussen": 15, "steilheit": 0.06,
                                 "max_korrektur": 1.5}) == 1.5,
       "-10 °C -> Deckel +1.5 K")
pruefe(witterung.korrektur(15, {"aktiv": True, "basis_aussen": 15, "steilheit": 0.06,
                                "max_korrektur": 1.5}) == 0.0,
       "15 °C -> keine Korrektur")
pruefe(witterung.korrektur(0, {"aktiv": True, "basis_aussen": 15, "steilheit": 0.06,
                               "max_korrektur": 1.5}) == 0.9,
       "0 °C -> +0.9 K")
sommer = {"aktiv": True, "grenze": 16.0, "hysterese": 1.5}
pruefe(witterung.sommerbetrieb(18.0, sommer, False) is True, "18 °C -> Sommer an")
pruefe(witterung.sommerbetrieb(15.0, sommer, True) is True, "15 °C bleibt Sommer (Hysterese)")
pruefe(witterung.sommerbetrieb(14.0, sommer, True) is False, "14.4 °C -> Sommer aus")
pruefe(witterung.sommerbetrieb(15.0, sommer, False) is False, "15 °C startet nicht neu")
g = witterung.daempfen(10.0, 20.0, 3600, 6.0)
pruefe(9.0 < g < 12.0, f"Dämpfung über eine Stunde bleibt träge ({g:.2f})")
pruefe(witterung.vorlaufminuten(0, {"aktiv": True, "grund_min": 30,
                                    "min_pro_grad": 2.0, "max_min": 120}) == 60,
       "0 °C -> 60 Minuten Vorlauf")
pruefe(witterung.vorlaufminuten(20, {"aktiv": True, "grund_min": 30,
                                     "min_pro_grad": 2.0, "max_min": 120}) == 30,
       "20 °C -> Grundvorlauf")

print("\n=== Anwesenheit ===")
personen = {
    "person.sven": {"name": "Sven", "zuhause": False, "entfernung_km": 5.0, "zustand": "StatZon1"},
    "person.luna": {"name": "Luna", "zuhause": True, "entfernung_km": None, "zustand": "home"},
}
r_luna = dict(store.STANDARD_RAUM, name="Luna", personen=["person.luna"])
r_sven = dict(store.STANDARD_RAUM, name="Büro", personen=["person.sven"])
besetzt, grund = anwesenheit.raum_besetzt(r_luna, {}, personen)
pruefe(besetzt, f"Lunas Zimmer besetzt ({grund})")
besetzt, grund = anwesenheit.raum_besetzt(r_sven, {}, personen)
pruefe(not besetzt, f"Büro leer ({grund})")
# Heimkehr setzt voraus, dass die Person sich auch naehert
personen["person.sven"]["naehert_sich"] = True
heim, grund = anwesenheit.kommt_heim(r_sven, personen, 8.0)
pruefe(heim, f"Sven auf dem Heimweg erkannt ({grund})")
heim, _ = anwesenheit.kommt_heim(r_sven, personen, 2.0)
pruefe(not heim, "bei 2 km Schwelle noch keine Heimkehr")

print("\n--- Schule in Sichtweite ---")
# Nele ist in der Realschule, 1 km Luftlinie. Ohne weitere Pruefung waere sie
# den ganzen Schultag \"auf dem Heimweg\".
schulkind = {"person.nele": {"name": "Nele", "zuhause": False, "entfernung_km": 1.0,
                             "zustand": "Realschule", "in_zone": "Realschule",
                             "naehert_sich": False}}
r_nele = dict(store.STANDARD_RAUM, name="Nele Zimmer", personen=["person.nele"])
heim, grund = anwesenheit.kommt_heim(r_nele, schulkind, 8.0)
pruefe(not heim, "Kind in der Schulzone gilt nicht als heimkehrend")

# Auch ohne Zonenmeldung darf blosse Naehe nicht genuegen
ohne_zone = {"person.nele": {**schulkind["person.nele"], "in_zone": None,
                             "naehert_sich": False}}
heim, grund = anwesenheit.kommt_heim(r_nele, ohne_zone, 8.0)
pruefe(not heim, "blosse Naehe ohne Annaeherung genuegt nicht")

# Auf dem Heimweg: Zone verlassen und Entfernung nimmt ab
unterwegs = {"person.nele": {**schulkind["person.nele"], "in_zone": None,
                             "naehert_sich": True, "entfernung_km": 0.6}}
heim, grund = anwesenheit.kommt_heim(r_nele, unterwegs, 8.0)
pruefe(heim, f"auf dem Heimweg erkannt ({grund})")

print("\n--- Annaeherung aus dem Verlauf ---")
from datetime import timedelta
def lauf(werte, mindest=0.3):
    """werte: Liste (minuten_vor_jetzt, km) -> naehert_sich beim letzten Takt"""
    jetzt = datetime(2026, 8, 25, 12, 0)
    gedaechtnis = {}
    ergebnis = None
    for minuten, km in werte:
        zeitpunkt = jetzt + timedelta(minutes=minuten)
        p = {"person.x": {"name": "X", "zuhause": False, "entfernung_km": km,
                          "zustand": "not_home", "in_zone": None,
                          "naehert_sich": False}}
        anwesenheit.bewegung_fortschreiben(p, gedaechtnis, zeitpunkt, mindest)
        ergebnis = p["person.x"]["naehert_sich"]
    return ergebnis

pruefe(lauf([(0, 1.0), (5, 1.0), (10, 1.0), (16, 1.0), (21, 1.0)]) is False,
       "gleichbleibende Entfernung (Schule) -> keine Annaeherung")
pruefe(lauf([(0, 5.0), (5, 4.0), (10, 3.0), (16, 2.0), (21, 1.0)]) is True,
       "abnehmende Entfernung -> Annaeherung")
pruefe(lauf([(0, 1.0), (5, 2.0), (10, 3.0), (16, 4.0), (21, 5.0)]) is False,
       "zunehmende Entfernung -> keine Annaeherung")
pruefe(lauf([(0, 1.0), (5, 1.05), (10, 0.95), (16, 1.0), (21, 0.9)]) is False,
       "GPS-Rauschen um 100 m loest nichts aus")
pruefe(lauf([(0, 1.0), (5, 1.0), (10, 1.0), (16, 1.0), (21, 0.5)]) is True,
       "Aufbruch nach Hause wird erkannt")
alle = dict(store.STANDARD_RAUM, name="Wohnzimmer", personen=[])
besetzt, _ = anwesenheit.raum_besetzt(alle, {}, personen)
pruefe(besetzt, "Raum ohne Personenzuordnung folgt der ganzen Familie")

print("\n=== Regelkette ===")
einst = store.validate_einstellungen({})
einst["trockenlauf"] = True


def umgebung(jetzt, **extra):
    basis = {
        "jetzt": jetzt, "einstellungen": einst, "states_index": {},
        "aussen": 5.0, "aussen_gedaempft": 6.0, "sommerbetrieb": False,
        "urlaub": False, "schulfrei": False, "personen": personen,
        "raum_wechsel": {},
    }
    basis.update(extra)
    return basis


wohnzimmer = store.validate_raum({
    "name": "Wohnzimmer", "thermostate": ["climate.a"], "personen": [],
    "komfort": 23.0, "eco": 19.0, "nacht": 19.0, "abwesend": 17.0,
    "min": 5.0, "max": 26.0, "zeitplan": plan,
})

rz = {}
e = regelung.entscheide(wohnzimmer, rz, umgebung(montag.replace(hour=14)))
pruefe(e["zustand"] == "komfort" and e["ziel"] == 23.5,
       f"Montag 14:00, 5 °C außen -> komfort 23.5 ({e['ziel']}, {e['begruendung']})")

e = regelung.entscheide(wohnzimmer, {}, umgebung(montag.replace(hour=14), urlaub=True))
pruefe(e["zustand"] == "urlaub" and e["ziel"] == 12.0, "Urlaub schlägt den Zeitplan")

e = regelung.entscheide(wohnzimmer, {}, umgebung(montag.replace(hour=14), sommerbetrieb=True))
pruefe(e["zustand"] == "sommer" and e.get("ventil_zu"), "Sommerbetrieb schließt das Ventil")

# Abwesenheit: Raum seit zwei Stunden leer, niemand in der Nähe
leer_personen = {"person.sven": {"name": "Sven", "zuhause": False,
                                 "entfernung_km": 40.0, "zustand": "StatZon1",
                                 "in_zone": None, "naehert_sich": False}}
rz_leer = {"leer_seit": (montag.replace(hour=12)).isoformat(timespec="seconds")}
e = regelung.entscheide(wohnzimmer, rz_leer,
                        umgebung(montag.replace(hour=14), personen=leer_personen))
pruefe(e["zustand"] == "abwesend" and e["ziel"] == 17.0,
       f"leeres Haus -> Abwesenheitstemperatur ({e['ziel']}, {e['begruendung']})")

# Heimkehr hebt die Absenkung auf - naeher kommend und in keiner Zone
nah = {"person.sven": {"name": "Sven", "zuhause": False, "entfernung_km": 4.0,
                       "zustand": "not_home", "in_zone": None,
                       "naehert_sich": True}}
e = regelung.entscheide(wohnzimmer, dict(rz_leer),
                        umgebung(montag.replace(hour=14), personen=nah))
pruefe(e["zustand"] == "heimkehr" and e["ziel"] > 20,
       f"Heimkehr hebt die Absenkung auf ({e['ziel']}, {e['begruendung']})")

# Karenzzeit: gerade erst gegangen -> noch keine Absenkung
rz_frisch = {"leer_seit": (montag.replace(hour=13, minute=50)).isoformat(timespec="seconds")}
e = regelung.entscheide(wohnzimmer, rz_frisch,
                        umgebung(montag.replace(hour=14), personen=leer_personen))
pruefe(e["zustand"] == "komfort", f"innerhalb der Karenzzeit bleibt es warm ({e['begruendung']})")

# Vorheizen: 05:00 Uhr, Wechsel auf komfort um 05:30, bei 5 °C = 50 min Vorlauf
e = regelung.entscheide(wohnzimmer, {}, umgebung(montag.replace(hour=5, minute=0)))
pruefe(e["ziel"] > 22, f"05:00 Uhr wird für 05:30 vorgeheizt ({e['ziel']}, {e['begruendung']})")

# Fenstersturz
rz_fenster = {"verlauf": [
    [(montag.replace(hour=13, minute=55)).isoformat(timespec="seconds"), 22.5],
    [(montag.replace(hour=13, minute=58)).isoformat(timespec="seconds"), 21.6],
]}
states_index = {"climate.a": {"entity_id": "climate.a", "state": "heat",
                              "attributes": {"current_temperature": 20.9,
                                             "temperature": 23.0,
                                             "min_temp": 5, "max_temp": 30,
                                             "hvac_modes": ["off", "heat"]}}}
e = regelung.entscheide(wohnzimmer, rz_fenster,
                        umgebung(montag.replace(hour=14), states_index=states_index))
pruefe(e["zustand"] == "fenster" and e["ziel"] == 8.0,
       f"Temperatursturz erkannt ({e['begruendung']})")

# Sperre wirkt nach
rz_sperre = {"fenster_bis": (montag.replace(hour=14, minute=20)).isoformat(timespec="seconds")}
e = regelung.entscheide(wohnzimmer, rz_sperre, umgebung(montag.replace(hour=14)))
pruefe(e["zustand"] == "fenster", f"Fenstersperre läuft nach ({e['begruendung']})")

# Grenzen des Raumes werden eingehalten: Komfort 20.0 plus Heizkurve wäre 20.6
eng = store.validate_raum({**wohnzimmer, "max": 20.0, "komfort": 20.0,
                           "eco": 19.0, "nacht": 19.0, "abwesend": 17.0})
e = regelung.entscheide(eng, {}, umgebung(montag.replace(hour=14)))
pruefe(e["ziel"] == 20.0, f"Obergrenze des Raumes deckelt die Heizkurve ({e['ziel']})")

# Ein Komfortwert außerhalb der Raumgrenzen ist ein Konfigurationsfehler
try:
    store.validate_raum({**wohnzimmer, "max": 20.0, "komfort": 23.0})
    pruefe(False, "Komfort über dem Raum-Maximum wird abgelehnt")
except store.ValidationError:
    pruefe(True, "Komfort über dem Raum-Maximum wird abgelehnt")

print("\n=== Fensterkontakte ===")

def fensterlage(kontakte, zustaende, verlauf_sturz=True, zusatz=False):
    """Hilfskonstrukt: Raum mit Kontakten, dazu ein Temperatursturz im Verlauf."""
    r = store.validate_raum({**wohnzimmer, "fenster": kontakte,
                             "sturz_auch_mit_kontakten": zusatz})
    idx = {"climate.a": {"entity_id": "climate.a", "state": "heat",
                         "attributes": {"current_temperature": 20.9, "temperature": 23.0,
                                        "min_temp": 5, "max_temp": 30,
                                        "hvac_modes": ["off", "heat"]}}}
    for eid, zustand in zustaende.items():
        idx[eid] = {"entity_id": eid, "state": zustand,
                    "attributes": {"friendly_name": eid.split(".")[-1]}}
    rz = {"verlauf": [
        [(montag.replace(hour=13, minute=55)).isoformat(timespec="seconds"), 22.5],
    ]} if verlauf_sturz else {}
    return regelung.entscheide(r, rz, umgebung(montag.replace(hour=14),
                                               states_index=idx))

e = fensterlage(["binary_sensor.fenster_wz"], {"binary_sensor.fenster_wz": "on"})
pruefe(e["zustand"] == "fenster" and "offen" in e["begruendung"],
       f"offener Kontakt schlaegt an ({e['begruendung']})")

e = fensterlage(["binary_sensor.fenster_wz"], {"binary_sensor.fenster_wz": "off"})
pruefe(e["zustand"] != "fenster",
       f"geschlossener Kontakt unterdrueckt die Sturzerkennung ({e['zustand']})")

e = fensterlage(["binary_sensor.fenster_wz"], {"binary_sensor.fenster_wz": "off"},
                zusatz=True)
pruefe(e["zustand"] == "fenster",
       "mit Zusatzoption greift der Sturz auch bei geschlossenem Kontakt")

e = fensterlage(["binary_sensor.fenster_wz"], {"binary_sensor.fenster_wz": "unavailable"})
pruefe(e["zustand"] == "fenster",
       f"ausgefallener Kontakt faellt auf den Sturz zurueck ({e['begruendung']})")

e = fensterlage(["binary_sensor.fenster_wz"], {"binary_sensor.fenster_wz": "unavailable"},
                verlauf_sturz=False)
pruefe("melden nichts" in e["begruendung"],
       f"ausgefallener Kontakt wird benannt ({e['begruendung']})")

e = fensterlage(["binary_sensor.a", "binary_sensor.b"],
                {"binary_sensor.a": "off", "binary_sensor.b": "on"})
pruefe(e["zustand"] == "fenster", "ein offener unter mehreren genuegt")

e = fensterlage([], {})
pruefe(e["zustand"] == "fenster", "ohne Kontakte greift weiterhin der Sturz")

print("\n=== Erkennung von Fensterkontakten ===")
import ha_api
# Die Namen stammen aus dem echten Bestand dieses Hauses.
faelle = [
    ("binary_sensor.fenster_kueche", "Küche Fenster", None, True),
    ("binary_sensor.wz_kontakt", "Wohnzimmer", "window", True),
    ("binary_sensor.heizung_luna_offenes_fenster_erkannt",
     "Heizung Gästetoilette Offenes Fenster erkannt", None, True),
    ("binary_sensor.haustur_tur", "Haustür Cloud Tür", "door", True),
    ("binary_sensor.terrassentuer_kontakt", "Terrassentür", "door", True),
    # Nebenmelder eines Thermostats, dessen Gerät „Eingangstür“ heißt
    ("binary_sensor.heizung_eingangstuer_sommermodus",
     "Heizung Eingangstür Sommermodus", None, False),
    ("binary_sensor.heizung_eingangstuer_tastensperre_am_gerat",
     "Heizung Eingangstür Tastensperre am Gerät", None, False),
    ("binary_sensor.haustur_cloud_calibration", "Haustür Cloud Calibration",
     None, False),
    # Öffnungszeiten von Tankstellen: device_class opening, aber kein Kontakt
    ("binary_sensor.aral_an_der_westumgehung_1_status",
     "ARAL An der Westumgehung  1 Status", "opening", False),
    ("binary_sensor.shell_rosenheimer_landstr_81_status",
     "Shell Rosenheimer Landstr. 81 Status", "opening", False),
    # Diagnosemelder eines Rolladens, die das Fenster nur im Namen führen
    ("binary_sensor.rollo_fenster_luna_obstacle_detection",
     "Rollo Fenster Luna Obstacle Detection", None, False),
    ("binary_sensor.rollo_balkontur_luna_blocking_detection",
     "Rollo Balkontür Luna Blocking Detection", None, False),
    ("binary_sensor.rollo_terrassentur_sun_program_active",
     "Rollo Terrassentür Sun Program Active", None, False),
    ("binary_sensor.bewegung_flur", "Bewegung Flur", "motion", False),
    ("binary_sensor.tv_aufnahme", "65PUS6412/12 Aufnahme läuft", None, False),
]
for eid, name, klasse, erwartet in faelle:
    treffer = ha_api.ist_fensterkontakt(eid, name, klasse)
    pruefe(treffer == erwartet,
           f"{name!r} -> {'Fenster' if erwartet else 'kein Fenster'}")

print("\n=== Praesenzsteuerung und Freigabe ===")

melder = {"binary_sensor.buero": {"entity_id": "binary_sensor.buero",
                                  "state": "off", "attributes": {}}}
buero = store.validate_raum({
    "name": "Buero", "thermostate": ["climate.b"], "personen": [],
    "praesenz": ["binary_sensor.buero"], "nur_praesenz": True, "karenz_min": 20,
    "komfort": 21.0, "eco": 18.0, "nacht": 17.0, "abwesend": 16.0,
    "min": 5.0, "max": 26.0, "zeitplan": plan,
})

# Melder aus, Familie zu Hause -> trotzdem leer
besetzt, grund = anwesenheit.raum_besetzt(buero, melder, personen)
pruefe(not besetzt, f"nur_praesenz: Familie daheim zaehlt nicht ({grund})")

melder_an = {"binary_sensor.buero": {"entity_id": "binary_sensor.buero",
                                     "state": "on", "attributes": {}}}
besetzt, grund = anwesenheit.raum_besetzt(buero, melder_an, personen)
pruefe(besetzt, f"Melder an -> besetzt ({grund})")

# Ohne hinterlegten Melder waere der Raum sonst fuer immer leer
ohne = store.validate_raum({**buero, "praesenz": []})
besetzt, grund = anwesenheit.raum_besetzt(ohne, {}, personen)
pruefe(besetzt, f"nur_praesenz ohne Melder friert den Raum nicht ein ({grund})")

# Ein falsch eingetragener oder ausgefallener Melder darf nicht dauerhaft
# absenken - genau der Fehler, der beim Einrichten des Bueros passiert ist
besetzt, grund = anwesenheit.raum_besetzt(buero, {}, personen)
pruefe(besetzt, f"fehlender Melder gilt nicht als leer ({grund})")
tot = {"binary_sensor.buero": {"entity_id": "binary_sensor.buero",
                               "state": "unavailable", "attributes": {}}}
besetzt, grund = anwesenheit.raum_besetzt(buero, tot, personen)
pruefe(besetzt, f"ausgefallener Melder gilt nicht als leer ({grund})")

# Zwei Melder, einer tot, einer meldet niemanden -> Raum ist leer
zwei = store.validate_raum({**buero,
                            "praesenz": ["binary_sensor.buero", "binary_sensor.tot"]})
gemischt = {"binary_sensor.buero": {"entity_id": "binary_sensor.buero",
                                    "state": "off", "attributes": {}},
            "binary_sensor.tot": {"entity_id": "binary_sensor.tot",
                                  "state": "unavailable", "attributes": {}}}
besetzt, grund = anwesenheit.raum_besetzt(zwei, gemischt, personen)
pruefe(not besetzt, f"ein antwortender Melder genuegt fuer die Aussage ({grund})")

# Raumeigene Karenzzeit: nach 25 Minuten leer wird abgesenkt (global waeren 45)
rz_b = {"leer_seit": montag.replace(hour=13, minute=35).isoformat(timespec="seconds")}
e = regelung.entscheide(buero, rz_b, umgebung(montag.replace(hour=14),
                                              states_index=melder))
pruefe(e["zustand"] == "abwesend",
       f"raumeigene Karenzzeit von 20 Minuten greift ({e['begruendung']})")

# Mit globaler Karenzzeit waere es noch zu frueh
buero_global = store.validate_raum({**buero, "karenz_min": None})
e = regelung.entscheide(buero_global, dict(rz_b),
                        umgebung(montag.replace(hour=14), states_index=melder))
pruefe(e["zustand"] != "abwesend",
       f"ohne eigene Karenzzeit gilt weiter die globale ({e['begruendung']})")

# Freigabeschalter
gast = store.validate_raum({
    "name": "Gaestezimmer", "thermostate": ["climate.g"], "personen": [],
    "freigabe_entity": "input_boolean.gaeste", "anwesenheit": False,
    "komfort": 21.0, "eco": 18.0, "nacht": 17.0, "abwesend": 16.0,
    "min": 5.0, "max": 26.0, "zeitplan": plan,
})
aus = {"input_boolean.gaeste": {"entity_id": "input_boolean.gaeste",
                                "state": "off",
                                "attributes": {"friendly_name": "Gaeste da"}}}
e = regelung.entscheide(gast, {}, umgebung(montag.replace(hour=14), states_index=aus))
pruefe(e["zustand"] == "gesperrt" and e.get("ventil_zu"),
       f"Freigabe aus -> Raum gesperrt ({e['begruendung']})")

an = {"input_boolean.gaeste": {"entity_id": "input_boolean.gaeste",
                               "state": "on",
                               "attributes": {"friendly_name": "Gaeste da"}}}
e = regelung.entscheide(gast, {}, umgebung(montag.replace(hour=14), states_index=an))
pruefe(e["zustand"] == "komfort" and e["ziel"] > 20,
       f"Freigabe an -> normaler Zeitplan ({e['ziel']}, {e['begruendung']})")

# Fehlender Schalter darf den Raum nicht kalt stellen
e = regelung.entscheide(gast, {}, umgebung(montag.replace(hour=14), states_index={}))
pruefe(e["zustand"] != "gesperrt",
       f"fehlender Freigabeschalter sperrt nicht ({e['zustand']})")

print("\n=== Betriebsart: nur absenken ===")

wc = store.validate_raum({
    "name": "Gästetoilette", "betriebsart": "nur_absenken",
    "thermostate": ["climate.wc"], "personen": [],
    "komfort": 21.0, "eco": 18.0, "nacht": 18.0, "abwesend": 16.0,
    "min": 5.0, "max": 26.0,
    "zeitplan": [{"start": "21:00", "modus": "nacht", "gilt": "immer",
                  "tage": [t[0] for t in [("mon",), ("tue",), ("wed",), ("thu",),
                                          ("fri",), ("sat",), ("sun",)]]}],
})

def wc_umgebung(jetzt, soll=21.0, **extra):
    idx = {"climate.wc": {"entity_id": "climate.wc", "state": "heat",
                          "attributes": {"current_temperature": 22.0,
                                         "temperature": soll, "min_temp": 5,
                                         "max_temp": 30,
                                         "hvac_modes": ["off", "heat"]}}}
    return umgebung(jetzt, states_index=idx, **extra)

# Erster Lauf: nur vermerken, nichts nachholen
rz_wc = {}
e = regelung.entscheide(wc, rz_wc, wc_umgebung(montag.replace(hour=22)))
pruefe(e["zustand"] == "manuell" and e.get("nicht_schreiben"),
       f"erster Lauf holt die Absenkung nicht nach ({e['begruendung']})")
pruefe(rz_wc.get("zuletzt_ausgeloest", "").endswith("21:00:00"),
       "der verpasste Zeitpunkt wird vermerkt")
pruefe(e["ziel"] == 21.0, f"angezeigt wird der von Hand gestellte Wert ({e['ziel']})")

# Nächster Tag, 21:05 -> Absenkung faellig
e = regelung.entscheide(wc, rz_wc, wc_umgebung(
    montag.replace(day=25, hour=21, minute=5)))
pruefe(e["zustand"] == "absenkung" and e["ziel"] == 18.0 and e.get("erzwingen"),
       f"Absenkung wird ausgeloest ({e['ziel']}, {e['begruendung']})")

# Mitten am Tag: keine Einmischung, auch wenn jemand hochgedreht hat
e = regelung.entscheide(wc, dict(rz_wc), wc_umgebung(
    montag.replace(day=25, hour=14), soll=24.0))
pruefe(e["zustand"] == "manuell" and e.get("nicht_schreiben") and e["ziel"] == 24.0,
       f"tagsueber keine Einmischung ({e['begruendung']})")

# Weit nach dem Zeitpunkt: nicht nachholen
rz_alt = {"zuletzt_ausgeloest": montag.replace(day=24, hour=21).isoformat(
    timespec="seconds")}
e = regelung.entscheide(wc, rz_alt, wc_umgebung(montag.replace(day=25, hour=23)))
pruefe(e["zustand"] == "manuell" and "verpasst" in e["begruendung"],
       f"laengst vergangener Zeitpunkt wird nicht nachgeholt ({e['begruendung']})")

# Im Zeitfenster nach dem Zeitpunkt wird weiter versucht
rz_fenster_zeit = {"zuletzt_ausgeloest": montag.replace(day=24, hour=21).isoformat(
    timespec="seconds")}
e = regelung.entscheide(wc, rz_fenster_zeit, wc_umgebung(
    montag.replace(day=25, hour=21, minute=25)))
pruefe(e["zustand"] == "absenkung",
       "innerhalb des Ausloesefensters wird weiter versucht")

# Sonderzustand: Urlaub greift durch, merkt sich aber den Handwert
e = regelung.entscheide(wc, dict(rz_wc), wc_umgebung(
    montag.replace(day=25, hour=14), urlaub=True))
pruefe(e["zustand"] == "urlaub" and e.get("merken") and e.get("erzwingen"),
       "Urlaub greift auch im Handbetrieb und merkt sich den Wert")

# Wiederherstellung nach dem Sonderzustand
zustand_wc = {"thermostate": {"climate.wc": {"vor_sonderzustand": 21.0}},
              "raeume": {}}
protokolliert_wc = []
umg_wc = wc_umgebung(montag.replace(day=25, hour=14), soll=12.0)
umg_wc["raum_wechsel"] = {wc["id"]: montag.replace(day=25, hour=21)}
einst["trockenlauf"] = True
aktionen = regelung.anwenden(
    wc, {"zustand": "manuell", "ziel": 21.0, "begruendung": "x",
         "nicht_schreiben": True, "wiederherstellen": True},
    zustand_wc, umg_wc, lambda *a, **k: protokolliert_wc.append(a))
pruefe(len(aktionen) == 1 and aktionen[0]["aktion"] == "zurück"
       and aktionen[0]["wert"] == 21.0,
       f"nach dem Sonderzustand wird die Handeinstellung zurueckgegeben ({aktionen})")
pruefe(zustand_wc["thermostate"]["climate.wc"]["vor_sonderzustand"] is None,
       "der gemerkte Wert wird danach verworfen")

# Ohne gemerkten Wert passiert im Ruhezustand gar nichts
zustand_leer = {"thermostate": {}, "raeume": {}}
aktionen = regelung.anwenden(
    wc, {"zustand": "manuell", "ziel": 21.0, "begruendung": "x",
         "nicht_schreiben": True, "wiederherstellen": True},
    zustand_leer, umg_wc, lambda *a, **k: None)
pruefe(not aktionen, "ohne gemerkten Wert bleibt der Raum unangetastet")

print("\n=== Flankenschreiben ===")
zustand = {"thermostate": {}, "raeume": {}}
protokolliert = []


def protokoll(raum, was, warum, entity_id=""):
    protokolliert.append((raum, was, warum))


umg = umgebung(montag.replace(hour=14), states_index=states_index)
umg["raum_wechsel"] = {wohnzimmer["id"]: montag.replace(hour=21)}
entscheidung = {"zustand": "komfort", "ziel": 23.0, "begruendung": "Test"}
aktionen = regelung.anwenden(wohnzimmer, entscheidung, zustand, umg, protokoll)
pruefe(not aktionen, "Sollwert steht schon richtig -> kein Schreibvorgang")

entscheidung = {"zustand": "komfort", "ziel": 21.0, "begruendung": "Test"}
aktionen = regelung.anwenden(wohnzimmer, entscheidung, zustand, umg, protokoll)
pruefe(len(aktionen) == 1 and aktionen[0]["trocken"],
       "abweichender Sollwert -> im Trockenlauf nur gemeldet")

print("\n=== Validierung ===")
try:
    store.validate_raum({"name": "", "thermostate": []})
    pruefe(False, "leerer Name wird abgelehnt")
except store.ValidationError:
    pruefe(True, "leerer Name wird abgelehnt")
try:
    store.validate_raum({"name": "X", "min": 20, "max": 18})
    pruefe(False, "Maximum unter Minimum wird abgelehnt")
except store.ValidationError:
    pruefe(True, "Maximum unter Minimum wird abgelehnt")
try:
    store.validate_zeitplan([{"start": "25:00", "modus": "komfort", "tage": ["mon"]}])
    pruefe(False, "ungültige Uhrzeit wird abgelehnt")
except store.ValidationError:
    pruefe(True, "ungültige Uhrzeit wird abgelehnt")

print(f"\n{'ALLE PRÜFUNGEN BESTANDEN' if not fehler else str(len(fehler)) + ' FEHLER'}")
sys.exit(1 if fehler else 0)
