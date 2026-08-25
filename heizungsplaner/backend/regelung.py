"""Die Regelkette: aus Zeitplan, Wetter und Anwesenheit wird ein Sollwert.

Für jeden Raum entsteht in jedem Takt eine Entscheidung aus einer festen
Rangfolge. Der erste zutreffende Fall gewinnt:

1. Raum abgeschaltet      → Ventil zu
2. Fenster offen          → Frostschutz, für eine Sperrzeit
3. Urlaub                 → Urlaubstemperatur
4. Sommerbetrieb          → Ventil zu
5. Zeitplan               → Komfort / Eco / Nacht, ggf. vorgezogen (Vorheizen)
6. niemand zuständig da   → auf Abwesenheitstemperatur absenken
7. Heizkurve              → Aufschlag nach Außentemperatur

Jede Entscheidung trägt ihre Begründung mit sich; sie steht später in der
Oberfläche und im Protokoll. Wer wissen will, warum ein Raum gerade 17 °C
bekommt, soll das nicht aus dem Quelltext erschließen müssen.

Geschrieben wird ausschließlich auf **Flanke**: Ein Sollwert geht nur dann an
ein Thermostat, wenn dort tatsächlich etwas anderes eingestellt ist. Ein
Pegelabgleich, der bei jedem Takt stur denselben Wert schreibt, macht ein
Add-on zum Besitzer der Entität und überfährt jede andere Bedienung.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

import anwesenheit
import ha_api
import wachhund
import witterung
import zeitplan as zp

_LOGGER = logging.getLogger(__name__)

# So lange bekommt ein Thermostat Zeit, einen geschriebenen Wert zu bestätigen,
# bevor erneut geschrieben oder eine Abweichung als Handeingriff gewertet wird.
# Funkthermostate melden sich nur alle paar Minuten.
BESTAETIGUNG_MIN = 15

# Feinere Sollwerte als ein halbes Grad kann kein Heizkörperthermostat.
SCHRITT = 0.5

# Betriebsart „nur absenken“: So lange nach einem Absenkzeitpunkt versucht der
# Planer, den Wert zu setzen. Danach gehört der Raum wieder der Hand, die ihn
# stellt. Das Fenster überbrückt einen ausgefallenen Takt oder ein Thermostat,
# das gerade nicht antwortet – ein einzelner Schuss ginge dabei verloren.
AUSLOESE_FENSTER_MIN = 30


def _jetzt() -> datetime:
    return datetime.now()


def _iso(zeitpunkt: datetime | None) -> str | None:
    return zeitpunkt.isoformat(timespec="seconds") if zeitpunkt else None


def _aus_iso(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _runden(wert: float) -> float:
    return round(round(wert / SCHRITT) * SCHRITT, 1)


def _bool_state(states_index: dict, entity_id: str) -> bool | None:
    eintrag = states_index.get(entity_id)
    if not eintrag:
        return None
    zustand = eintrag.get("state")
    if zustand in ("on", "off"):
        return zustand == "on"
    return None


# ------------------------------------------------------------ Raumklima ----

def raumtemperatur(raum: dict, states_index: dict) -> float | None:
    """Ist-Temperatur des Raumes: eigener Fühler, sonst Mittel der Thermostate."""
    eigener = raum.get("raumtemp")
    if eigener:
        eintrag = states_index.get(eigener)
        if eintrag:
            wert = ha_api.as_float(eintrag.get("state"))
            if wert is not None:
                return wert
    werte = []
    for entity_id in raum.get("thermostate") or []:
        eintrag = states_index.get(entity_id)
        if not eintrag:
            continue
        wert = ha_api.as_float((eintrag.get("attributes") or {}).get("current_temperature"))
        if wert is not None:
            werte.append(wert)
    return round(sum(werte) / len(werte), 1) if werte else None


def fenster_offen(raum: dict, states_index: dict, rz: dict, ist: float | None,
                  jetzt: datetime, fenster_cfg: dict) -> tuple[bool, str, str]:
    """Fenstererkennung: erst die Kontakte, dann ersatzweise der Temperatursturz.

    Rückgabe: offen, Begründung, Hinweis zum Verfahren.

    Sobald ein Raum verlässliche Kontakte hat, entscheiden allein sie – der
    Temperatursturz ist der Notbehelf für Räume ohne Kontakte und schlägt
    sonst auch mal grundlos an (ein anlaufender Heizkörper verwirbelt die
    Luft am Thermostatfühler). Wer beides will, schaltet es am Raum zu.

    **Ein Kontakt, der nichts meldet, gilt nicht als „geschlossen“.** Ein
    leerer Knopf, ein abgezogener Zigbee-Stick oder ein noch nicht angelernter
    Sensor würde den Raum sonst stillschweigend blind machen. In dem Fall
    springt die Sturzerkennung wieder ein.
    """
    if not fenster_cfg.get("aktiv"):
        return False, "", ""

    kontakte = raum.get("fenster") or []
    verlaesslich, stumm = 0, []
    for entity_id in kontakte:
        zustand = _bool_state(states_index, entity_id)
        if zustand is None:
            stumm.append(entity_id)
            continue
        verlaesslich += 1
        if zustand:
            name = (states_index[entity_id].get("attributes") or {}).get(
                "friendly_name", entity_id)
            return True, f"{name} ist offen", ""

    hinweis = ""
    if stumm:
        hinweis = (f"{len(stumm)} Fensterkontakt(e) melden nichts – "
                   f"ersatzweise Temperatursturz")
    sturz_erlaubt = verlaesslich == 0 or raum.get("sturz_auch_mit_kontakten") or stumm
    if not sturz_erlaubt or ist is None:
        return False, "", hinweis

    fenster_min = int(fenster_cfg.get("sturz_min", 10))
    schwelle = float(fenster_cfg.get("sturz_k", 1.2))
    verlauf = rz.get("verlauf") or []
    grenze = jetzt - timedelta(minutes=fenster_min)
    frueher = [wert for stempel, wert in verlauf
               if (_aus_iso(stempel) or jetzt) >= grenze]
    if frueher:
        hoechster = max(frueher)
        if hoechster - ist >= schwelle:
            return True, (f"Temperatursturz um {hoechster - ist:.1f} K "
                          f"in {fenster_min} Minuten"), hinweis
    return False, "", hinweis


def _verlauf_fortschreiben(rz: dict, ist: float | None, jetzt: datetime) -> None:
    """Kurzes Temperaturgedächtnis je Raum, eine Stunde tief."""
    if ist is None:
        return
    verlauf = rz.get("verlauf") or []
    verlauf.append([_iso(jetzt), ist])
    grenze = jetzt - timedelta(hours=1)
    rz["verlauf"] = [[stempel, wert] for stempel, wert in verlauf
                     if (_aus_iso(stempel) or jetzt) >= grenze][-60:]


# ----------------------------------------------------------- Entscheidung ----

def entscheide(raum: dict, rz: dict, umgebung: dict) -> dict:
    """Zielwert und Zustand für einen Raum ermitteln.

    ``rz`` ist der gespeicherte Laufzeitzustand des Raumes und wird dabei
    fortgeschrieben (Leerzeit, Fenstersperre, Temperaturverlauf).
    """
    jetzt = umgebung["jetzt"]
    einst = umgebung["einstellungen"]
    states_index = umgebung["states_index"]
    frostschutz = float(einst["frostschutz"])

    ist = raumtemperatur(raum, states_index)
    _verlauf_fortschreiben(rz, ist, jetzt)
    nur_absenken = raum.get("betriebsart") == "nur_absenken"

    def ergebnis(zustand: str, ziel: float, begruendung: str, **extra) -> dict:
        ziel = _runden(max(float(raum["min"]), min(float(raum["max"]), ziel)))
        # In der Betriebsart „nur absenken“ gehört der Sollwert der Hand, die
        # ihn gestellt hat. Greift ein Sonderzustand ein, wird der vorgefundene
        # Wert gemerkt und hinterher wiederhergestellt – sonst bliebe der Raum
        # nach einmal Lüften für immer auf Frostschutz stehen.
        if nur_absenken and zustand in ("fenster", "urlaub", "sommer"):
            extra.setdefault("merken", True)
            extra.setdefault("erzwingen", True)
        return {"zustand": zustand, "ziel": ziel, "begruendung": begruendung,
                "ist": ist, **extra}

    # 1 — Raum abgeschaltet oder nicht freigegeben
    if not raum.get("aktiv", True):
        return ergebnis("aus", frostschutz, "Raum ist im Planer abgeschaltet",
                        ventil_zu=True)

    # Ein Raum, der nur zeitweise gebraucht wird – ein Gästezimmer etwa –
    # hängt an einem Schalter in Home Assistant. Steht der auf aus, bleibt der
    # Raum kalt, ganz gleich was Zeitplan und Anwesenheit sagen.
    freigabe = raum.get("freigabe_entity")
    if freigabe:
        zustand_freigabe = _bool_state(states_index, freigabe)
        if zustand_freigabe is False:
            name = (states_index.get(freigabe, {}).get("attributes") or {}).get(
                "friendly_name", freigabe)
            return ergebnis("gesperrt", frostschutz,
                            f"\u201e{name}\u201c ist aus \u2013 der Raum wird "
                            f"nicht geheizt", ventil_zu=True)
        if zustand_freigabe is None:
            # Der Schalter fehlt oder meldet nichts. Den Raum deswegen kalt zu
            # lassen wäre die unangenehmere Überraschung, also wird geheizt und
            # der Hinweisbalken meldet den fehlenden Schalter.
            _LOGGER.warning("Freigabe %s für Raum %s meldet nichts – der Raum "
                            "wird normal geregelt", freigabe, raum["name"])

    # 2 — Fenster
    sperre_bis = _aus_iso(rz.get("fenster_bis"))
    offen, fenster_grund, fenster_hinweis = fenster_offen(
        raum, states_index, rz, ist, jetzt, einst["fenster"])
    if offen:
        sperre_bis = jetzt + timedelta(minutes=int(einst["fenster"]["sperre_min"]))
        rz["fenster_bis"] = _iso(sperre_bis)
        return ergebnis("fenster", frostschutz, fenster_grund)
    if sperre_bis and sperre_bis > jetzt:
        rest = int((sperre_bis - jetzt).total_seconds() // 60) + 1
        return ergebnis("fenster", frostschutz,
                        f"Fenster war offen – Sperre noch {rest} Minuten")
    rz["fenster_bis"] = None

    # 3 — Urlaub
    if umgebung.get("urlaub"):
        return ergebnis("urlaub", float(einst["urlaub_temperatur"]),
                        "Urlaub ist eingeschaltet")

    # 4 — Sommerbetrieb
    if umgebung.get("sommerbetrieb"):
        gedaempft = umgebung.get("aussen_gedaempft")
        return ergebnis("sommer", frostschutz,
                        f"Sommerbetrieb – Außentemperatur liegt im Mittel bei "
                        f"{gedaempft:.1f} °C" if gedaempft is not None
                        else "Sommerbetrieb", ventil_zu=True)

    # 5a — Betriebsart „nur absenken“: der Plan stößt an, statt zu führen
    plan = raum.get("zeitplan") or []
    if nur_absenken:
        return _nur_absenken(raum, rz, umgebung, plan, ist, ergebnis,
                             fenster_hinweis)

    # 5 — Zeitplan, ggf. vorgezogen
    eintrag = zp.aktueller_eintrag(plan, jetzt, umgebung.get("schulfrei"))
    modus = eintrag["modus"] if eintrag else "eco"
    basis = zp.modus_temperatur(raum, modus, frostschutz)
    begruendung = (f"Zeitplan: {modus} ab {eintrag['start']} Uhr" if eintrag
                   else "Kein Zeitplan hinterlegt – Eco-Temperatur")

    vorlauf = witterung.vorlaufminuten(umgebung.get("aussen"), einst["vorheizen"])
    if vorlauf:
        kommend = zp.naechster_waermerer_wechsel(
            raum, jetzt, umgebung.get("schulfrei"), basis, frostschutz)
        if kommend:
            zeitpunkt, kommender_eintrag = kommend
            if jetzt + timedelta(minutes=vorlauf) >= zeitpunkt:
                basis = zp.modus_temperatur(raum, kommender_eintrag["modus"], frostschutz)
                modus = kommender_eintrag["modus"]
                begruendung = (f"Vorheizen für {kommender_eintrag['modus']} um "
                               f"{kommender_eintrag['start']} Uhr "
                               f"({vorlauf} Minuten Vorlauf)")

    # 6 — Anwesenheit
    zustand = modus
    if einst["anwesenheit"]["aktiv"] and raum.get("anwesenheit", True):
        besetzt, anwesenheits_grund = anwesenheit.raum_besetzt(
            raum, states_index, umgebung["personen"])
        if besetzt:
            rz["leer_seit"] = None
        else:
            leer_seit = _aus_iso(rz.get("leer_seit"))
            if leer_seit is None:
                leer_seit = jetzt
                rz["leer_seit"] = _iso(leer_seit)
            karenz = raum.get("karenz_min")
            if karenz is None:
                karenz = einst["anwesenheit"]["karenz_min"]
            karenz = int(karenz)
            leer_minuten = (jetzt - leer_seit).total_seconds() / 60.0
            if leer_minuten >= karenz:
                # Zählt allein der Melder, darf die Entfernung einer Person
                # nichts bewirken: Sonst liefe die Heizung an, sobald jemand
                # nach Hause fährt – auch wenn niemand den Raum betritt.
                schwelle = 0.0
                if einst["vorheizen"].get("aktiv") and not raum.get("nur_praesenz"):
                    schwelle = float(einst["vorheizen"].get("heimkehr_km", 0))
                heimweg, heimweg_grund = anwesenheit.kommt_heim(
                    raum, umgebung["personen"], schwelle)
                if heimweg:
                    begruendung = f"Heimkehr erwartet – {heimweg_grund}"
                    zustand = "heimkehr"
                else:
                    abwesend = float(raum["abwesend"])
                    if abwesend < basis:
                        basis = abwesend
                        zustand = "abwesend"
                        begruendung = (f"{anwesenheits_grund}, seit "
                                       f"{int(leer_minuten)} Minuten leer")
            else:
                rest = int(karenz - leer_minuten) + 1
                begruendung += f" – {anwesenheits_grund}, Absenkung in {rest} Minuten"

    # 7 — Heizkurve
    #
    # Nur auf gewollte Raumtemperaturen, nicht auf Sparwerte: Die Kurve soll
    # dafür sorgen, dass ein Raum sein Komfortziel auch bei Kälte erreicht.
    # Die Abwesenheitstemperatur ist dagegen ein reiner Haltewert – dort wäre
    # ein Aufschlag genau das Gegenteil dessen, wofür er gedacht ist.
    korrektur = 0.0
    if raum.get("heizkurve", True) and zustand in ("komfort", "eco", "nacht", "heimkehr"):
        korrektur = witterung.korrektur(umgebung.get("aussen"), einst["heizkurve"])
        if abs(korrektur) >= 0.05:
            vorzeichen = "+" if korrektur > 0 else ""
            begruendung += f" · Heizkurve {vorzeichen}{korrektur:.1f} K"

    if fenster_hinweis:
        begruendung += f" · {fenster_hinweis}"

    return ergebnis(zustand, basis + korrektur, begruendung, korrektur=korrektur)


def _eingestellter_sollwert(raum: dict, states_index: dict) -> float | None:
    """Was gerade an den Thermostaten des Raumes steht – Mittel über alle."""
    werte = []
    for entity_id in raum.get("thermostate") or []:
        eintrag = states_index.get(entity_id)
        if not eintrag:
            continue
        wert = ha_api.as_float((eintrag.get("attributes") or {}).get("temperature"))
        if wert is not None:
            werte.append(wert)
    return round(sum(werte) / len(werte), 1) if werte else None


def _nur_absenken(raum: dict, rz: dict, umgebung: dict, plan: list[dict],
                  ist: float | None, ergebnis, fenster_hinweis: str) -> dict:
    """Betriebsart „von Hand, nur zu festen Zeiten absenken“.

    Der Raum wird von Hand gestellt. Der Planer greift allein zu den
    Zeitpunkten des Plans ein und lässt ihn sonst in Ruhe – auch dann, wenn
    jemand hochdreht. Das ist der Unterschied zum geführten Zeitplan, bei dem
    der letzte Umschaltpunkt dauerhaft gilt.

    Beim ersten Lauf wird der zurückliegende Zeitpunkt nur vermerkt, nicht
    ausgeführt: Ein Add-on-Start um 22 Uhr soll nicht die Absenkung von 21 Uhr
    nachholen und dabei eine Handeinstellung überfahren.
    """
    jetzt = umgebung["jetzt"]
    einst = umgebung["einstellungen"]
    frostschutz = float(einst["frostschutz"])
    eingestellt = _eingestellter_sollwert(raum, umgebung["states_index"])

    def ruhen(begruendung: str) -> dict:
        # Angezeigt wird, was von Hand eingestellt ist. Meldet das Thermostat
        # keinen Sollwert – FRITZ-Geräte tun das in der Sommerpause nicht –,
        # bleibt das Feld leer, statt ersatzweise die Ist-Temperatur als Ziel
        # auszugeben. Eine Zahl, die kein Sollwert ist, liest sich wie einer.
        anzeige = eingestellt if eingestellt is not None else (ist or frostschutz)
        if fenster_hinweis:
            begruendung += f" · {fenster_hinweis}"
        return ergebnis("manuell", anzeige, begruendung, handwert=eingestellt,
                        nicht_schreiben=True, wiederherstellen=True)

    treffer = zp.letzter_zeitpunkt(plan, jetzt, umgebung.get("schulfrei"))
    if not treffer:
        return ruhen("Von Hand gestellt – kein Absenkzeitpunkt hinterlegt")

    zeitpunkt, eintrag = treffer
    zuletzt = _aus_iso(rz.get("zuletzt_ausgeloest"))
    naechster = zp.naechster_wechsel(plan, jetzt, umgebung.get("schulfrei"))
    ausblick = (f" – nächste Absenkung {naechster[1]['start']} Uhr"
                if naechster else "")

    if zuletzt is None:
        rz["zuletzt_ausgeloest"] = _iso(zeitpunkt)
        return ruhen(f"Von Hand gestellt{ausblick}")

    if zeitpunkt > zuletzt:
        faellig_seit = jetzt - zeitpunkt
        if faellig_seit <= timedelta(minutes=AUSLOESE_FENSTER_MIN):
            ziel = zp.modus_temperatur(raum, eintrag["modus"], frostschutz)
            # Genau dieser Eingriff soll die Handeinstellung überschreiben –
            # sonst hielte ihn die Handeingriff-Erkennung für einen Konflikt.
            return ergebnis("absenkung", ziel,
                            f"Absenkung um {eintrag['start']} Uhr auf "
                            f"{ziel:.1f} °C", erzwingen=True)
        # Verpasst – etwa weil das Add-on stand. Nicht nachholen, nur vermerken.
        rz["zuletzt_ausgeloest"] = _iso(zeitpunkt)
        return ruhen(f"Absenkung um {eintrag['start']} Uhr verpasst, "
                     f"nicht nachgeholt{ausblick}")

    return ruhen(f"Von Hand gestellt{ausblick}")


# ------------------------------------------------------------- Ausführung ----

def _thermostat_grenzen(attrs: dict) -> tuple[float, float]:
    return (ha_api.as_float(attrs.get("min_temp")) or 5.0,
            ha_api.as_float(attrs.get("max_temp")) or 30.0)


def anwenden(raum: dict, entscheidung: dict, state: dict, umgebung: dict,
             protokoll) -> list[dict]:
    """Die Entscheidung an die Thermostate des Raumes weitergeben.

    Gibt zurück, was tatsächlich geschaltet wurde – für Protokoll und Anzeige.
    """
    jetzt = umgebung["jetzt"]
    einst = umgebung["einstellungen"]
    states_index = umgebung["states_index"]
    trockenlauf = bool(einst.get("trockenlauf"))
    ventil_zu = bool(entscheidung.get("ventil_zu"))
    aktionen = []

    for entity_id in raum.get("thermostate") or []:
        eintrag = states_index.get(entity_id)
        if not eintrag:
            protokoll(raum["name"], "fehlt", f"{entity_id} ist in Home Assistant nicht vorhanden")
            continue
        attrs = eintrag.get("attributes") or {}
        gedaechtnis = state["thermostate"].setdefault(entity_id, {})
        zuletzt_am = _aus_iso(gedaechtnis.get("gesetzt_am"))
        frisch = bool(zuletzt_am and (jetzt - zuletzt_am) < timedelta(minutes=BESTAETIGUNG_MIN))
        ist_soll_jetzt = ha_api.as_float(attrs.get("temperature"))

        # -- Handeinstellung vor einem Sonderzustand sichern ------------------
        if entscheidung.get("merken") and gedaechtnis.get("vor_sonderzustand") is None:
            if ist_soll_jetzt is not None:
                gedaechtnis["vor_sonderzustand"] = ist_soll_jetzt

        # -- Raum ruht: nur eine gesicherte Handeinstellung zurückgeben -------
        if entscheidung.get("nicht_schreiben"):
            gesichert = gedaechtnis.get("vor_sonderzustand")
            if entscheidung.get("wiederherstellen") and gesichert is not None:
                gedaechtnis["vor_sonderzustand"] = None
                if trockenlauf:
                    aktionen.append({"entity_id": entity_id, "aktion": "zurück",
                                     "wert": gesichert, "trocken": True})
                elif ist_soll_jetzt is None or abs(ist_soll_jetzt - gesichert) >= SCHRITT / 2:
                    if ha_api.set_temperature(entity_id, gesichert):
                        gedaechtnis.update({"soll": gesichert, "gesetzt_am": _iso(jetzt),
                                            "hvac": "heat"})
                        aktionen.append({"entity_id": entity_id, "aktion": "zurück",
                                         "wert": gesichert})
                        protokoll(raum["name"], f"zurück auf {gesichert:.1f} °C",
                                  "Sonderzustand vorbei – die Handeinstellung von "
                                  "vorher gilt wieder", entity_id)
            continue

        # -- Ventil schließen (Sommer / Raum abgeschaltet) --------------------
        #
        # Nicht jedes Thermostat lässt sich abschalten. Manche Matter-Geräte
        # nehmen den Befehl an und springen eine Minute später von selbst
        # zurück auf „heat“. Wer das nicht bemerkt, schickt bei jedem Takt
        # aufs Neue ein „aus“ – Dauerfeuer, das nichts bewirkt außer die
        # Batterie zu leeren. Nach zwei vergeblichen Versuchen weicht der
        # Planer deshalb dauerhaft auf den Frostschutzwert aus; das schließt
        # das Ventil genauso, nur über den Sollwert.
        kann_aus = "off" in (attrs.get("hvac_modes") or [])
        if ventil_zu and kann_aus and not gedaechtnis.get("aus_vergeblich"):
            if eintrag.get("state") == "off":
                gedaechtnis.update({"hvac": "off", "aus_fehlversuche": 0})
                continue
            if frisch and gedaechtnis.get("hvac") == "off":
                continue  # eben erst geschickt, Thermostat meldet noch nicht zurück
            if gedaechtnis.get("hvac") == "off":
                # Wir hatten ausgeschaltet, das Gerät steht wieder auf „heat“.
                fehlversuche = gedaechtnis.get("aus_fehlversuche", 0) + 1
                gedaechtnis["aus_fehlversuche"] = fehlversuche
                if fehlversuche >= 2:
                    gedaechtnis["aus_vergeblich"] = True
                    protokoll(raum["name"], "bleibt an",
                              f"{attrs.get('friendly_name', entity_id)} nimmt das "
                              f"Ausschalten nicht an – von nun an schließt der "
                              f"Planer das Ventil über den Frostschutzwert",
                              entity_id)
                    # kein continue: unten wird jetzt der Sollwert gesetzt
                else:
                    if trockenlauf:
                        aktionen.append({"entity_id": entity_id, "aktion": "aus",
                                         "trocken": True})
                        continue
                    if ha_api.set_hvac_mode(entity_id, "off"):
                        gedaechtnis.update({"hvac": "off", "gesetzt_am": _iso(jetzt)})
                        aktionen.append({"entity_id": entity_id, "aktion": "aus"})
                    continue
            else:
                if trockenlauf:
                    aktionen.append({"entity_id": entity_id, "aktion": "aus",
                                     "trocken": True})
                    continue
                if ha_api.set_hvac_mode(entity_id, "off"):
                    gedaechtnis.update({"hvac": "off", "gesetzt_am": _iso(jetzt),
                                        "soll": None})
                    aktionen.append({"entity_id": entity_id, "aktion": "aus"})
                    protokoll(raum["name"], "aus", entscheidung["begruendung"], entity_id)
                continue

        ziel = float(entscheidung["ziel"])
        unten, oben = _thermostat_grenzen(attrs)
        ziel = _runden(max(unten, min(oben, ziel)))
        ist_soll = ha_api.as_float(attrs.get("temperature"))

        # -- Handeingriff erkennen -------------------------------------------
        # Weicht der Sollwert am Gerät von unserem zuletzt geschriebenen Wert
        # ab, hat jemand von Hand gedreht. Das gilt bis zum nächsten
        # Zeitplanwechsel, danach führt wieder der Plan.
        erzwingen = bool(entscheidung.get("erzwingen"))
        if einst.get("manuell_respektieren") and not frisch and not erzwingen:
            geschrieben = gedaechtnis.get("soll")
            if (geschrieben is not None and ist_soll is not None
                    and abs(ist_soll - geschrieben) >= SCHRITT
                    and abs(ist_soll - ziel) >= SCHRITT):
                manuell_bis = umgebung["raum_wechsel"].get(raum["id"])
                gedaechtnis["manuell_bis"] = _iso(manuell_bis)
                gedaechtnis["soll"] = ist_soll
                aktionen.append({"entity_id": entity_id, "aktion": "manuell",
                                 "wert": ist_soll})
                protokoll(raum["name"], "manuell",
                          f"Von Hand auf {ist_soll:.1f} °C gestellt – der Planer "
                          f"hält sich bis zum nächsten Zeitplanwechsel zurück",
                          entity_id)
                continue
        manuell_bis = _aus_iso(gedaechtnis.get("manuell_bis"))
        if manuell_bis and manuell_bis > jetzt and not erzwingen:
            continue
        if manuell_bis:
            gedaechtnis["manuell_bis"] = None

        # -- Betriebsart sicherstellen ---------------------------------------
        if eintrag.get("state") == "off" and not trockenlauf:
            if not frisch or gedaechtnis.get("hvac") != "heat":
                ha_api.set_hvac_mode(entity_id, "heat")
                gedaechtnis["hvac"] = "heat"
                gedaechtnis["gesetzt_am"] = _iso(jetzt)

        # -- Sollwert nur auf Flanke -----------------------------------------
        if ist_soll is not None and abs(ist_soll - ziel) < SCHRITT / 2:
            gedaechtnis["soll"] = ziel
            continue
        if frisch and gedaechtnis.get("soll") is not None \
                and abs(gedaechtnis["soll"] - ziel) < SCHRITT / 2:
            continue  # bereits geschickt, Bestätigung steht noch aus

        if trockenlauf:
            aktionen.append({"entity_id": entity_id, "aktion": "soll",
                             "wert": ziel, "vorher": ist_soll, "trocken": True})
            continue

        if ha_api.set_temperature(entity_id, ziel):
            gedaechtnis.update({"soll": ziel, "gesetzt_am": _iso(jetzt), "hvac": "heat"})
            aktionen.append({"entity_id": entity_id, "aktion": "soll",
                             "wert": ziel, "vorher": ist_soll})
            protokoll(raum["name"],
                      f"{ziel:.1f} °C",
                      entscheidung["begruendung"], entity_id)
        else:
            protokoll(raum["name"], "fehlgeschlagen",
                      f"{entity_id} hat den Sollwert {ziel:.1f} °C nicht angenommen",
                      entity_id)

    return aktionen


# ----------------------------------------------------------------- Takt ----

def takt(config: dict, state: dict, protokoll) -> dict:
    """Ein vollständiger Regeldurchlauf über alle Räume."""
    jetzt = _jetzt()
    einst = config["einstellungen"]

    states = ha_api.get_states()
    if not states:
        _LOGGER.warning("Keine Zustände von Home Assistant erhalten – Takt übersprungen")
        return {"zeit": _iso(jetzt), "fehler": "Home Assistant nicht erreichbar",
                "raeume": []}
    states_index = {s.get("entity_id"): s for s in states}

    aussen = witterung.aussentemperatur(states_index, einst.get("aussen_entity", ""))
    letzter_takt = _aus_iso(state.get("letzter_takt"))
    sekunden = (jetzt - letzter_takt).total_seconds() if letzter_takt else 0.0

    vorgeschichte = state.get("aussen_gedaempft")
    if vorgeschichte is None and aussen is not None:
        # Erster Lauf: Die Dämpfung braucht einen Anlauf. Ohne ihn beginnt sie
        # beim aktuellen Messwert – an einem kühlen Sommertag hieße das
        # Heizbetrieb, obwohl die Woche davor mild war.
        vorgeschichte = ha_api.historien_mittel(
            einst.get("aussen_entity", ""),
            max(24.0, float(einst["daempfung_stunden"]) * 2))
        if vorgeschichte is not None:
            protokoll("Alle Räume", "Anlauf",
                      f"Gedämpfte Außentemperatur aus der Historie übernommen: "
                      f"{vorgeschichte:.1f} °C")

    gedaempft = witterung.daempfen(vorgeschichte, aussen,
                                   sekunden, float(einst["daempfung_stunden"]))
    sommer = witterung.sommerbetrieb(gedaempft, einst["sommer"],
                                     bool(state.get("sommerbetrieb")))
    if sommer != bool(state.get("sommerbetrieb")):
        protokoll("Alle Räume", "Sommerbetrieb " + ("ein" if sommer else "aus"),
                  f"Gedämpfte Außentemperatur {gedaempft:.1f} °C" if gedaempft is not None
                  else "Außentemperatur unbekannt")

    urlaub = _bool_state(states_index, einst.get("urlaub_entity", "")) or False
    schulfrei = _bool_state(states_index, einst.get("schulfrei_entity", ""))
    heim = ha_api.zone_home(states)
    zonen = anwesenheit.zonennamen(states_index)
    personen = anwesenheit.personen_status(states_index, heim, zonen)
    anwesenheit.bewegung_fortschreiben(
        personen, state.setdefault("personen", {}), jetzt,
        float(einst["vorheizen"].get("heimkehr_annaeherung_km", 0.3)))

    raum_wechsel = {}
    for raum in config["raeume"]:
        treffer = zp.naechster_wechsel(raum.get("zeitplan") or [], jetzt, schulfrei)
        raum_wechsel[raum["id"]] = treffer[0] if treffer else jetzt + timedelta(hours=12)

    umgebung = {
        "jetzt": jetzt, "einstellungen": einst, "states_index": states_index,
        "aussen": aussen, "aussen_gedaempft": gedaempft, "sommerbetrieb": sommer,
        "urlaub": urlaub, "schulfrei": schulfrei, "personen": personen,
        "raum_wechsel": raum_wechsel,
    }

    automatik = bool(einst.get("automatik"))
    ergebnisse = []
    for raum in config["raeume"]:
        rz = state["raeume"].setdefault(raum["id"], {})
        entscheidung = entscheide(raum, rz, umgebung)
        aktionen = []
        if automatik:
            aktionen = anwenden(raum, entscheidung, state, umgebung, protokoll)
        vorher = rz.get("zustand")
        if vorher != entscheidung["zustand"]:
            rz["seit"] = _iso(jetzt)
        rz.update({
            "zustand": entscheidung["zustand"],
            "ziel": entscheidung["ziel"],
            "ist": entscheidung.get("ist"),
            "begruendung": entscheidung["begruendung"],
            "aktualisiert": _iso(jetzt),
        })
        naechster = raum_wechsel.get(raum["id"])
        ergebnisse.append({
            "id": raum["id"], "name": raum["name"],
            "zustand": entscheidung["zustand"], "ziel": entscheidung["ziel"],
            "ist": entscheidung.get("ist"), "begruendung": entscheidung["begruendung"],
            "handwert": entscheidung.get("handwert"),
            "seit": rz.get("seit"), "aktionen": aktionen,
            "naechster_wechsel": _iso(naechster),
            "thermostate": [
                {
                    "entity_id": eid,
                    "name": (states_index.get(eid, {}).get("attributes") or {}).get(
                        "friendly_name", eid),
                    "soll": ha_api.as_float(
                        (states_index.get(eid, {}).get("attributes") or {}).get("temperature")),
                    "ist": ha_api.as_float(
                        (states_index.get(eid, {}).get("attributes") or {}).get(
                            "current_temperature")),
                    "betriebsart": states_index.get(eid, {}).get("state"),
                    "manuell_bis": state["thermostate"].get(eid, {}).get("manuell_bis"),
                    "vorhanden": eid in states_index,
                }
                for eid in raum.get("thermostate") or []
            ],
        })

    # Der Wachhund läuft nach den Räumen: Er soll auch ein Thermostat sehen,
    # das gerade eben erst als fehlend aufgefallen ist.
    try:
        stoerungen = wachhund.pruefen(config, states_index, jetzt, einst,
                                      _batterien_holen(jetzt, state))
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Überwachung fehlgeschlagen: %s", err)
        stoerungen = []

    state.update({
        "aussen_gedaempft": round(gedaempft, 2) if gedaempft is not None else None,
        "sommerbetrieb": sommer,
        "letzter_takt": _iso(jetzt),
    })

    return {
        "zeit": _iso(jetzt),
        "aussen": aussen,
        "aussen_gedaempft": round(gedaempft, 2) if gedaempft is not None else None,
        "sommerbetrieb": sommer,
        "urlaub": urlaub,
        "schulfrei": schulfrei,
        "automatik": automatik,
        "trockenlauf": bool(einst.get("trockenlauf")),
        "personen": personen,
        "raeume": ergebnisse,
        "stoerungen": stoerungen,
    }


_BATTERIEN: dict = {"stand": None, "geholt": None}


def _batterien_holen(jetzt: datetime, state: dict) -> dict:
    """Die Zuordnung Thermostat → Batterieanzeige, einmal je Stunde erneuert.

    Sie ändert sich nur, wenn Geräte dazukommen – eine Template-Abfrage in
    jedem Takt wäre Verschwendung.
    """
    letzte = _BATTERIEN["geholt"]
    if _BATTERIEN["stand"] is None or letzte is None or \
            (jetzt - letzte) > timedelta(hours=1):
        _BATTERIEN["stand"] = wachhund.batterien_je_thermostat()
        _BATTERIEN["geholt"] = jetzt
    return _BATTERIEN["stand"]
