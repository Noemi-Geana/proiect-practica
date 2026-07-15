"""
stats.py
--------
Tine evidenta simpla a numarului de fisiere mutate/ignorate/eronate
in timpul unei rulari, si genereaza un raport de sumar la final.
"""

import time


class Stats:
    def __init__(self):
        self._counters = {
            "moved": 0,
            "duplicates": 0,
            "unsorted": 0,
            "errors": 0,
            "skipped_incomplete": 0,
        }
        self._start_time = time.time()

    def increment(self, key: str, amount: int = 1):
        self._counters[key] = self._counters.get(key, 0) + amount

    def get(self, key: str) -> int:
        return self._counters.get(key, 0)

    def elapsed_seconds(self) -> float:
        return round(time.time() - self._start_time, 2)

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