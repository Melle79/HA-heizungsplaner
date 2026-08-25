"""Protokoll der Schaltvorgänge – was wurde wann warum gestellt.

Nur Ereignisse, keine Takte: Ein Eintrag entsteht, wenn sich tatsächlich etwas
geändert hat. Damit bleibt das Protokoll lesbar und beantwortet die einzige
Frage, die man ihm später stellt – warum steht dieser Raum auf diesem Wert.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime

DATA_DIR = os.environ.get("DATA_DIR", "./data")
LOGBUCH_FILE = os.path.join(DATA_DIR, "logbuch.json")
MAX_EINTRAEGE = 500

_lock = threading.Lock()


def _load() -> list[dict]:
    if not os.path.exists(LOGBUCH_FILE):
        return []
    try:
        with open(LOGBUCH_FILE, encoding="utf-8") as f:
            daten = json.load(f)
        return daten if isinstance(daten, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save(eintraege: list[dict]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = LOGBUCH_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(eintraege, f, ensure_ascii=False, indent=1)
    os.replace(tmp, LOGBUCH_FILE)


def eintragen(raum: str, was: str, warum: str, entity_id: str = "") -> None:
    with _lock:
        eintraege = _load()
        eintraege.append({
            "zeit": datetime.now().isoformat(timespec="seconds"),
            "raum": raum,
            "was": was,
            "warum": warum,
            "entity_id": entity_id,
        })
        _save(eintraege[-MAX_EINTRAEGE:])


def lesen(grenze: int = 200) -> list[dict]:
    with _lock:
        eintraege = _load()
    return list(reversed(eintraege[-grenze:]))


def leeren() -> None:
    with _lock:
        _save([])
