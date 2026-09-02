// Die Übersetzungsmechanik – ohne eine einzige Vokabel.
//
// Die Sprachen liegen unter `sprachen/<code>.js` und melden sich selbst an
// (`window.SPRACHEN.en = {…}`). Diese Datei lädt die passende, übersetzt den
// vorhandenen Inhalt und danach alles, was die Oberfläche nachträglich
// aufbaut – Listen, Kacheln und Dialoge entstehen laufend neu.
//
// Deutsch ist die Quelle: Der deutsche Text ist zugleich der Schlüssel. Das
// klingt unorthodox, hat aber einen handfesten Vorteil – ein vergessener
// Eintrag fällt nicht aus, er bleibt deutsch stehen, statt als „missing.key“
// zu erscheinen.

const QUELLSPRACHE = 'de';
const AUSWEICH_SPRACHE = 'en';

let _sprache = null;      // die geladene Sprachdatei, oder null für Deutsch

// Im HTML stehen längere Sätze über mehrere Zeilen. Verglichen wird deshalb
// mit zusammengefasstem Leerraum – sonst bliebe jeder umbrochene Absatz
// deutsch, obwohl er im Wörterbuch steht.
const _glatt = (text) => text.replace(/\s+/g, ' ').trim();

function _uebersetze(text) {
  if (!_sprache) return null;
  const roh = _glatt(text);
  if (!roh) return null;
  if (_sprache.woerter[roh] !== undefined) return _sprache.woerter[roh];
  for (const [muster, ersatz] of _sprache.muster) {
    if (muster.test(roh)) return roh.replace(muster, ersatz);
  }
  return null;
}

// Was ein Mensch benannt hat – Räume, Geräte, Regeln – bleibt unangetastet.
// Sonst würde aus einem Raum namens „Schlafzimmer“ ein „Bedroom“, und wer ihn
// so wiederfinden will, sucht vergebens.
function _istDaten(el) {
  return !!(el && el.closest && el.closest('[data-roh]'));
}

function _knotenUebersetzen(wurzel) {
  const lauf = document.createTreeWalker(wurzel, NodeFilter.SHOW_TEXT);
  const zu_aendern = [];
  while (lauf.nextNode()) {
    const knoten = lauf.currentNode;
    if (knoten.parentElement && ['SCRIPT', 'STYLE'].includes(knoten.parentElement.tagName))
      continue;
    if (_istDaten(knoten.parentElement)) continue;
    const neu = _uebersetze(knoten.nodeValue);
    if (neu !== null && neu !== knoten.nodeValue) zu_aendern.push([knoten, neu]);
  }
  for (const [knoten, neu] of zu_aendern) knoten.nodeValue = neu;

  const elemente = wurzel.nodeType === 1 ? [wurzel, ...wurzel.querySelectorAll('*')]
                                         : [...wurzel.querySelectorAll('*')];
  for (const el of elemente) {
    if (_istDaten(el)) continue;
    for (const attr of ['placeholder', 'title']) {
      const wert = el.getAttribute && el.getAttribute(attr);
      if (!wert) continue;
      const neu = _uebersetze(wert);
      if (neu !== null && neu !== wert) el.setAttribute(attr, neu);
    }
  }
}

function _beobachten() {
  new MutationObserver((eintraege) => {
    for (const eintrag of eintraege) {
      for (const knoten of eintrag.addedNodes) {
        if (knoten.nodeType === 1) _knotenUebersetzen(knoten);
        else if (knoten.nodeType === 3 && !_istDaten(knoten.parentElement)) {
          const neu = _uebersetze(knoten.nodeValue);
          if (neu !== null && neu !== knoten.nodeValue) knoten.nodeValue = neu;
        }
      }
      if (eintrag.type === 'characterData' && !_istDaten(eintrag.target.parentElement)) {
        const neu = _uebersetze(eintrag.target.nodeValue);
        if (neu !== null && neu !== eintrag.target.nodeValue)
          eintrag.target.nodeValue = neu;
      }
    }
  }).observe(document.body, {childList: true, subtree: true, characterData: true});
}

function _anwenden(datei) {
  _sprache = datei;
  window.ORTSFORM = datei.locale || QUELLSPRACHE;
  // Die Vorlagen des Zeitplans heißen wie mögliche Raumnamen („Schlafzimmer“).
  // Sie werden deshalb über ihren Wert übersetzt, nicht über ihren Text.
  const vorlage = document.getElementById('r-vorlage');
  if (vorlage && datei.vorlagen) {
    for (const option of vorlage.options) {
      if (datei.vorlagen[option.value]) option.textContent = datei.vorlagen[option.value];
    }
  }
  _knotenUebersetzen(document.body);
  _beobachten();
}

function _laden(code) {
  return new Promise((fertig, fehlt) => {
    if (window.SPRACHEN && window.SPRACHEN[code]) return fertig(window.SPRACHEN[code]);
    const tag = document.createElement('script');
    tag.src = `sprachen/${code}.js`;
    tag.onload = () => (window.SPRACHEN && window.SPRACHEN[code])
      ? fertig(window.SPRACHEN[code]) : fehlt(new Error('leer'));
    tag.onerror = () => fehlt(new Error('nicht gefunden'));
    document.head.appendChild(tag);
  });
}

/**
 * Die Oberfläche in die Sprache von Home Assistant bringen.
 *
 * Deutsch ist die Quelle und braucht keine Datei. Fehlt die Datei zu einer
 * Sprache, wird Englisch versucht; fehlt auch das, bleibt es bei Deutsch –
 * eine unvollständige Übersetzung soll die Oberfläche nicht leerräumen.
 */
async function spracheAnwenden(code) {
  window.ORTSFORM = QUELLSPRACHE;
  if (!code || code === QUELLSPRACHE) return QUELLSPRACHE;
  for (const versuch of [code, AUSWEICH_SPRACHE]) {
    try {
      _anwenden(await _laden(versuch));
      return versuch;
    } catch (fehler) {
      console.info(`Sprache ${versuch} nicht verfügbar:`, fehler.message);
    }
  }
  return QUELLSPRACHE;
}

window.spracheAnwenden = spracheAnwenden;
