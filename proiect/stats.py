import json
import os
import time
from datetime import datetime


class Stats:
    def __init__(self, config=None):
        self._counters = {
            "moved": 0,
            "duplicates": 0,
            "unsorted": 0,
            "errors": 0,
            "skipped_incomplete": 0,
        }
        self._start_time = time.time()
        self._recent_additions = []  # [{filename, destination, timestamp}]

        self.config = config
        self.stats_file = None
        self._global = {"total_files_organized": 0, "history_additions": []}

        if config is not None:
            self.stats_file = config.get("stats", "stats_file", default="config/stats.json")
            self._global = self._load_global()

    # --- Statistici per rulare (in memorie) ---

    def increment(self, key: str, amount: int = 1):
        self._counters[key] = self._counters.get(key, 0) + amount

    def get(self, key: str) -> int:
        return self._counters.get(key, 0)

    def elapsed_seconds(self) -> float:
        return round(time.time() - self._start_time, 2)

    def record_addition(self, filename: str, destination: str):
        """Inregistreaza o mutare reusita, pentru lista de 'adaugari recente'."""
        entry = {
            "filename": filename,
            "destination": destination,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        self._recent_additions.append(entry)
        self._global.setdefault("history_additions", []).append(entry)
        # pastram doar ultimele 200 de intrari in istoricul global, ca fisierul sa nu creasca la infinit
        self._global["history_additions"] = self._global["history_additions"][-200:]

    # --- Statistici globale (persistente) ---

    def _load_global(self) -> dict:
        if self.stats_file and os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {"total_files_organized": 0, "history_additions": []}

    def save_global(self):
        if not self.stats_file:
            return
        self._global["total_files_organized"] = self._global.get("total_files_organized", 0) + self.get("moved")
        os.makedirs(os.path.dirname(self.stats_file) or ".", exist_ok=True)
        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(self._global, f, ensure_ascii=False, indent=2)

    def total_files_organized(self) -> int:
        """Total cumulat din toate rularile anterioare + rularea curenta."""
        return self._global.get("total_files_organized", 0) + self.get("moved")

    def recent_additions(self, limit: int = 10) -> list:
        return self._recent_additions[-limit:]

    # --- Spatiu ocupat pe categorie (scaneaza Media/) ---

    @staticmethod
    def _folder_size_bytes(path: str) -> int:
        total = 0
        if not os.path.isdir(path):
            return 0
        for dirpath, _, filenames in os.walk(path):
            for name in filenames:
                try:
                    total += os.path.getsize(os.path.join(dirpath, name))
                except OSError:
                    pass
        return total

    @staticmethod
    def _human_size(num_bytes: int) -> str:
        size = float(num_bytes)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    def disk_usage_by_category(self, config) -> dict:
       
        paths = config.paths
        media_root = paths.get("media_root", "")
        subfolders = config.subfolders

        result = {}
        for label, subfolder_name in subfolders.items():
            full_path = os.path.join(media_root, subfolder_name)
            result[label] = self._human_size(self._folder_size_bytes(full_path))

        for label in ("documents", "executables", "pictures", "duplicates", "unsorted"):
            path = paths.get(label)
            if path:
                result[label] = self._human_size(self._folder_size_bytes(path))

        return result

    # --- Raport text ---

    def summary_text(self) -> str:
        c = self._counters
        return (
            f"Rezumat rulare ({self.elapsed_seconds()}s):\n"
            f"  - Fișiere mutate:          {c['moved']}\n"
            f"  - Duplicate găsite:        {c['duplicates']}\n"
            f"  - Nesortate (Unsorted):    {c['unsorted']}\n"
            f"  - Ignorate (incomplete):   {c['skipped_incomplete']}\n"
            f"  - Erori:                  {c['errors']}"
        )

    def global_summary_text(self, config) -> str:
        usage = self.disk_usage_by_category(config)
        usage_lines = "\n".join(f"    - {cat}: {size}" for cat, size in usage.items())
        recent = self.recent_additions(5)
        recent_lines = "\n".join(
            f"    - {r['timestamp']}: {r['filename']}" for r in recent
        ) or 

        return (
            f"Statistici globale (cumulat, toate rularile):\n"
            f"  - Total fișiere organizate: {self.total_files_organized()}\n"
            f"  - Spațiu ocupat pe categorie:\n{usage_lines}\n"
            f"  - Cele mai recente adăugări:\n{recent_lines}"
        )
