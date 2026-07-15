"""
metadata_api.py
---------------
Interogheaza OMDb API pentru metadate despre filme/seriale (an, gen,
regizor, actori, rating) si descarca poster-ul asociat.

Foloseste un cache local (JSON) ca sa nu interogheze API-ul de mai
multe ori pentru acelasi titlu. Gestioneaza erori de retea/API fara
sa opreasca aplicatia (rate limit, lipsa conexiune, titlu negasit).
"""

import json
import os
import time

import requests


class MetadataAPI:
    def __init__(self, config, logger=None):
        api_cfg = config.api
        self.api_key = api_cfg.get("omdb_key", "")
        self.base_url = api_cfg.get("omdb_url", "http://www.omdbapi.com/")
        self.timeout = api_cfg.get("timeout_seconds", 5)
        self.max_retries = api_cfg.get("max_retries", 2)
        self.cache_file = api_cfg.get("cache_file", "config/metadata_cache.json")
        self.logger = logger

        self._cache = self._load_cache()
        self._last_request_time = 0
        self._min_interval = 0.3  # limitare simpla a ratei de request-uri

    def _log(self, msg, level="info"):
        if self.logger:
            getattr(self.logger, level)(msg)

    def _load_cache(self) -> dict:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                self._log(f"Cache-ul '{self.cache_file}' e corupt, se reporneste gol.", "warning")
        return {}

    def _save_cache(self):
        os.makedirs(os.path.dirname(self.cache_file) or ".", exist_ok=True)
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2)

    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    def fetch(self, title: str, year: int | None = None) -> dict | None:
        """Cauta metadate pentru un titlu. Foloseste cache-ul daca exista deja.
        Returneaza None daca titlul nu a fost gasit sau API-ul e indisponibil."""
        if not self.api_key or self.api_key == "PUNE_AICI_CHEIA_TA":
            self._log("Cheia OMDb API nu este configurata. Se sare peste metadate.", "warning")
            return None

        cache_key = f"{title.lower()}_{year or ''}"
        if cache_key in self._cache:
            self._log(f"Metadate gasite in cache pentru '{title}'")
            return self._cache[cache_key]

        params = {"apikey": self.api_key, "t": title}
        if year:
            params["y"] = year

        for attempt in range(1, self.max_retries + 1):
            try:
                self._rate_limit()
                response = requests.get(self.base_url, params=params, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()

                if data.get("Response") == "False":
                    self._log(f"Titlul '{title}' nu a fost gasit in OMDb: {data.get('Error')}", "warning")
                    return None

                self._cache[cache_key] = data
                self._save_cache()
                self._log(f"Metadate obtinute de la OMDb pentru '{title}'")
                return data

            except requests.exceptions.Timeout:
                self._log(f"Timeout la interogarea OMDb pentru '{title}' (incercarea {attempt})", "warning")
            except requests.exceptions.ConnectionError:
                self._log(f"Fara conexiune la internet, nu se pot obtine metadate pentru '{title}'", "error")
                return None
            except requests.exceptions.RequestException as e:
                self._log(f"Eroare API OMDb pentru '{title}': {e}", "error")
                return None

        return None

    def download_poster(self, metadata: dict, dest_dir: str) -> str | None:
        """Descarca poster-ul (daca exista in metadate) si il salveaza ca poster.jpg
        in directorul destinatie. Returneaza calea fisierului sau None."""
        poster_url = metadata.get("Poster") if metadata else None
        if not poster_url or poster_url == "N/A":
            return None

        try:
            response = requests.get(poster_url, timeout=self.timeout)
            response.raise_for_status()
            os.makedirs(dest_dir, exist_ok=True)
            poster_path = os.path.join(dest_dir, "poster.jpg")
            with open(poster_path, "wb") as f:
                f.write(response.content)
            self._log(f"Poster descarcat: {poster_path}")
            return poster_path
        except requests.exceptions.RequestException as e:
            self._log(f"Nu s-a putut descarca poster-ul: {e}", "warning")
            return None

    @staticmethod
    def save_nfo(metadata: dict, dest_dir: str, filename: str = "info.json"):
        """Salveaza metadatele complete ca fisier JSON langa fisierul media."""
        if not metadata:
            return None
        os.makedirs(dest_dir, exist_ok=True)
        nfo_path = os.path.join(dest_dir, filename)
        with open(nfo_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        return nfo_path