"""
mover.py
--------
Modulul central: decide unde trebuie mutat fiecare fisier si executa
mutarea (sau doar o simuleaza, in mod dry-run).

Reguli de destinatie:
  Downloads/Movies  -> Media/Movies/<an>/<titlu>/<titlu>.<ext>
  Downloads/Series  -> Media/<serial>/<sezon>/<episod>/<fisier>
  Downloads/Music   -> Media/Music/<Artist>/<melodie>
  Document (oriunde in Downloads) -> Documents/
  Executabil        -> Executables/
  Poza              -> Pictures/
  Parsare esuata    -> Unsorted/

Gestioneaza si coliziunile de nume (daca destinatia exista deja, adauga
un sufix numeric in loc sa suprascrie).
"""

import os
import shutil

from proiect.classifier import FileCategory
from proiect.name_parser import parse_movie, parse_series, parse_music


class Mover:
    def __init__(self, config, logger=None, history=None, stats=None):
        self.config = config
        self.logger = logger
        self.history = history
        self.stats = stats
        self.dry_run = config.behavior.get("dry_run", False)

    def _log(self, msg, level="info"):
        if self.logger:
            getattr(self.logger, level)(msg)

    @staticmethod
    def _unique_destination(dest_path: str) -> str:
        """Daca dest_path exista deja, adauga _1, _2, etc. inainte de extensie."""
        if not os.path.exists(dest_path):
            return dest_path
        base, ext = os.path.splitext(dest_path)
        counter = 1
        new_path = f"{base}_{counter}{ext}"
        while os.path.exists(new_path):
            counter += 1
            new_path = f"{base}_{counter}{ext}"
        return new_path

    def _do_move(self, src: str, dest: str) -> str:
        """Executa (sau simuleaza) mutarea efectiva, gestionand coliziuni."""
        dest = self._unique_destination(dest)

        if self.dry_run:
            self._log(f"[DRY-RUN] Ar muta '{src}' -> '{dest}'")
            return dest

        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(src, dest)
        self._log(f"Mutat: '{src}' -> '{dest}'")

        if self.history:
            self.history.record_move(src, dest)
        if self.stats:
            self.stats.increment("moved")
        return dest

    # --- Reguli specifice fiecarui tip de continut din Downloads ---

    def move_movie(self, filepath: str) -> str:
        filename = os.path.basename(filepath)
        ext = os.path.splitext(filename)[1]
        info = parse_movie(filename)
        title, year = info["title"], info["year"]

        if not title or title == "Unknown":
            return self.move_to_unsorted(filepath, reason="Titlu film neidentificat")

        media_root = self.config.paths["media_root"]
        movies_sub = self.config.subfolders.get("movies", "Movies")
        year_folder = str(year) if year else "AnNecunoscut"
        dest_dir = os.path.join(media_root, movies_sub, year_folder, title)
        dest_path = os.path.join(dest_dir, f"{title}{ext}")

        return self._do_move(filepath, dest_path)

    def move_series(self, filepath: str) -> str:
        filename = os.path.basename(filepath)
        info = parse_series(filename)
        title, season, episode = info["title"], info["season"], info["episode"]

        if season is None or episode is None:
            return self.move_to_unsorted(
                filepath, reason=f"Sezon/episod neidentificat pentru '{title}'"
            )

        media_root = self.config.paths["media_root"]
        series_sub = self.config.subfolders.get("series", "Series")
        dest_dir = os.path.join(
            media_root, series_sub, title, f"Sezonul {season:02d}", f"Episodul {episode:02d}"
        )
        dest_path = os.path.join(dest_dir, filename)

        return self._do_move(filepath, dest_path)

    def move_music(self, filepath: str) -> str:
        filename = os.path.basename(filepath)
        ext = os.path.splitext(filename)[1]
        info = parse_music(filename)
        artist, track = info["artist"] or "Artist Necunoscut", info["track"]

        media_root = self.config.paths["media_root"]
        music_sub = self.config.subfolders.get("music", "Music")
        dest_dir = os.path.join(media_root, music_sub, artist)
        dest_path = os.path.join(dest_dir, f"{track}{ext}")

        return self._do_move(filepath, dest_path)

    def move_document(self, filepath: str) -> str:
        filename = os.path.basename(filepath)
        dest_dir = self.config.paths["documents"]
        dest_path = os.path.join(dest_dir, filename)
        return self._do_move(filepath, dest_path)

    def move_executable(self, filepath: str) -> str:
        filename = os.path.basename(filepath)
        dest_dir = self.config.paths["executables"]
        dest_path = os.path.join(dest_dir, filename)
        return self._do_move(filepath, dest_path)

    def move_picture(self, filepath: str) -> str:
        filename = os.path.basename(filepath)
        dest_dir = self.config.paths["pictures"]
        dest_path = os.path.join(dest_dir, filename)
        return self._do_move(filepath, dest_path)

    def move_to_duplicates(self, filepath: str) -> str:
        filename = os.path.basename(filepath)
        dest_dir = self.config.paths["duplicates"]
        dest_path = os.path.join(dest_dir, filename)
        result = self._do_move(filepath, dest_path)
        if self.stats:
            self.stats.increment("duplicates")
        return result

    def move_to_unsorted(self, filepath: str, reason: str = "") -> str:
        filename = os.path.basename(filepath)
        dest_dir = self.config.paths["unsorted"]
        dest_path = os.path.join(dest_dir, filename)
        if reason:
            self._log(f"Nesortat ('{filename}'): {reason}", "warning")
        result = self._do_move(filepath, dest_path)
        if self.stats:
            self.stats.increment("unsorted")
        return result

    # --- Dispatcher general, pe baza locatiei sursa + categorie ---

    def route(self, filepath: str, category: str, source_folder: str) -> str | None:
        """source_folder e unul dintre: 'movies', 'series', 'music', 'root' """
        if source_folder == "movies" and category == FileCategory.VIDEO:
            return self.move_movie(filepath)
        if source_folder == "series" and category == FileCategory.VIDEO:
            return self.move_series(filepath)
        if source_folder == "music" and category == FileCategory.AUDIO:
            return self.move_music(filepath)

        # Fisier direct in Downloads (root) sau categorie care nu tine de folderul sursa
        if category == FileCategory.DOCUMENT:
            return self.move_document(filepath)
        if category == FileCategory.EXECUTABLE:
            return self.move_executable(filepath)
        if category == FileCategory.PICTURE:
            return self.move_picture(filepath)

        return self.move_to_unsorted(filepath, reason=f"Categorie '{category}' fara regula clara")