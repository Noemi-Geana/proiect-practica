import json
import os
import time
from datetime import datetime


class Stats:
    """Urmărește statisticile: per rulare curentă + global cumulat"""

    def __init__(self, config=None):
        # Contoare pentru rularea curentă
        self._counters = {
            "moved": 0,
            "duplicates": 0,
            "unsorted": 0,
            "errors": 0,
            "skipped_incomplete": 0,
        }
        self._start_time = time.time()
        self._recent_additions = []
        
        # Statistici globale (din TOATE rularile)
        self.config = config
        self.stats_file = None
        self._global = {"total_files_organized": 0, "history_additions": []}
        
        if config:
            self.stats_file = config.get("stats", "stats_file", default="config/stats.json")
            self._global = self._load_global()

    # ================================================================
    # PER RULARE - Contoare în memorie
    # ================================================================

    def increment(self, key: str, amount: int = 1):
        """Incrementează un counter"""
        self._counters[key] = self._counters.get(key, 0) + amount

    def get(self, key: str) -> int:
        """Returnează valoarea unui counter"""
        return self._counters.get(key, 0)

    def elapsed_seconds(self) -> float:
        """Cât timp a durat organizarea"""
        return round(time.time() - self._start_time, 2)

    def record_addition(self, filename: str, destination: str):
        """Salvează o mutare reușită"""
        entry = {
            "filename": filename,
            "destination": destination,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        self._recent_additions.append(entry)
        self._global["history_additions"].append(entry)
        
        # Păstrează doar ultimele 200 de intrări
        self._global["history_additions"] = self._global["history_additions"][-200:]

    # ================================================================
    # GLOBAL - Fișier persistent (config/stats.json)
    # ================================================================

    def _load_global(self) -> dict:
        """Citește stats.json din rulări anterioare"""
        if self.stats_file and os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {"total_files_organized": 0, "history_additions": []}

    def save_global(self):
        """Salvează statisticile în stats.json"""
        if not self.stats_file:
            return
        
        # Total = fișiere anterioare + mutate acum
        self._global["total_files_organized"] += self.get("moved")
        
        # Crează folder dacă nu există
        os.makedirs(os.path.dirname(self.stats_file) or ".", exist_ok=True)
        
        # Scrie JSON
        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(self._global, f, ensure_ascii=False, indent=2)

    def total_files_organized(self) -> int:
        """Total cumulat din TOATE rularile"""
        return self._global.get("total_files_organized", 0) + self.get("moved")

    def recent_additions(self, limit: int = 10) -> list:
        """Ultimele X fișiere adăugate acum"""
        return self._recent_additions[-limit:]

    # ================================================================
    # SPAȚIU - Calculator pentru utilizare disc
    # ================================================================

    @staticmethod
    def _folder_size_bytes(path: str) -> int:
        """Calculează spațiul unui folder (în bytes)"""
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
    def _human_size(bytes_size: int) -> str:
        """Convertește bytes în KB, MB, GB, etc"""
        size = float(bytes_size)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    def disk_usage_by_category(self, config) -> dict:
        """Spațiu ocupat pe fiecare categorie"""
        paths = config.paths
        media_root = paths.get("media_root", "")
        subfolders = config.subfolders
        
        result = {}
        
        # Categorii principale (Movies, Series, Music)
        for label, subfolder_name in subfolders.items():
            full_path = os.path.join(media_root, subfolder_name)
            result[label] = self._human_size(self._folder_size_bytes(full_path))
        
        # Categorii speciale (Documents, Executables, etc)
        for label in ("documents", "executables", "pictures", "duplicates", "unsorted"):
            path = paths.get(label)
            if path:
                result[label] = self._human_size(self._folder_size_bytes(path))
        
        return result

    # ================================================================
    # RAPOARTE - Text pentru afișare
    # ================================================================

    def summary_text(self) -> str:
        """Raportul rulării curente"""
        c = self._counters
        t = self.elapsed_seconds()
        return (
            f"Rezumat rulare ({t}s):\n"
            f"  - Fișiere mutate:      {c['moved']}\n"
            f"  - Duplicate:           {c['duplicates']}\n"
            f"  - Nesortate:           {c['unsorted']}\n"
            f"  - Incomplete ignorate: {c['skipped_incomplete']}\n"
            f"  - Erori:               {c['errors']}"
        )

    def global_summary_text(self, config) -> str:
        """Raportul global cumulat"""
        total = self.total_files_organized()
        
        # Spațiu pe categorie
        usage = self.disk_usage_by_category(config)
        usage_text = "\n".join(f"    - {cat}: {size}" for cat, size in usage.items())
        
        # Fișierele adăugate acum
        recent = self.recent_additions(5)
        if recent:
            recent_text = "\n".join(f"    - {r['timestamp']}: {r['filename']}" for r in recent)
        else:
            recent_text = "    (nicio adaugare in aceasta rulare)"
        
        return (
            f"Statistici globale (cumulat din toate rularile):\n"
            f"  - Total fișiere:     {total}\n"
            f"  - Spațiu ocupat:\n{usage_text}\n"
            f"  - Adăugări recente:\n{recent_text}"
        )