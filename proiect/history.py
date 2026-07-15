"""
history.py
----------
Pastreaza un istoric al mutarilor efectuate (sursa -> destinatie), salvat
intr-un fisier JSON, astfel incat utilizatorul sa poata anula (undo)
ultima rulare sau o mutare specifica, daca a fost o greseala.
"""

import json
import os
from datetime import datetime


class History:
    def __init__(self, config, logger=None):
        self.history_file = config.history_cfg.get("history_file", "config/history.json")
        self.logger = logger
        self._entries = self._load()

    def _log(self, msg, level="info"):
        if self.logger:
            getattr(self.logger, level)(msg)

    def _load(self) -> list:
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                self._log(f"Istoricul '{self.history_file}' e corupt, se reporneste gol.", "warning")
        return []

    def _save(self):
        os.makedirs(os.path.dirname(self.history_file) or ".", exist_ok=True)
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(self._entries, f, ensure_ascii=False, indent=2)

    def record_move(self, src: str, dest: str):
        self._entries.append({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "source": src,
            "destination": dest,
        })
        self._save()

    def last_run_entries(self) -> list:
        """Returneaza mutarile din ultima 'sesiune' (grupate dupa cel mai recent timestamp
        aflat la mai putin de 5 minute distanta de ultima intrare)."""
        if not self._entries:
            return []
        last_time = datetime.fromisoformat(self._entries[-1]["timestamp"])
        result = []
        for entry in reversed(self._entries):
            entry_time = datetime.fromisoformat(entry["timestamp"])
            if (last_time - entry_time).total_seconds() > 300:
                break
            result.append(entry)
        return list(reversed(result))

    def undo_last_run(self) -> tuple[int, int]:
        """Muta inapoi fisierele din ultima rulare, la locatia originala.
        Returneaza (numar_reusite, numar_esuate)."""
        entries = self.last_run_entries()
        success, failed = 0, 0

        for entry in entries:
            src, dest = entry["source"], entry["destination"]
            try:
                if os.path.exists(dest):
                    os.makedirs(os.path.dirname(src), exist_ok=True)
                    os.rename(dest, src)
                    self._log(f"Undo: '{dest}' -> '{src}'")
                    success += 1
                else:
                    self._log(f"Undo esuat, fisierul nu mai exista: '{dest}'", "warning")
                    failed += 1
            except OSError as e:
                self._log(f"Undo esuat pentru '{dest}': {e}", "error")
                failed += 1

        # elimina din istoric intrarile procesate
        processed = {(e["source"], e["destination"]) for e in entries}
        self._entries = [
            e for e in self._entries if (e["source"], e["destination"]) not in processed
        ]
        self._save()

        return success, failed