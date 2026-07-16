import os
import shutil

from proiect.classifier import FileCategory
from proiect.name_parser import parse_movie, parse_series, parse_music


class PathSecurityError(Exception):
   
    pass


class Mover:
    def __init__(self, config, logger=None, history=None, stats=None):
        self.config = config
        self.logger = logger
        self.history = history
        self.stats = stats
        self.dry_run = config.behavior.get("dry_run", False)

        # radacinile permise pentru orice mutare: doar folderele definite explicit in config.
        # orice destinatie calculata TREBUIE sa se afle in interiorul uneia dintre ele.
        self._allowed_roots = [os.path.abspath(p) for p in config.paths.values()]

    def _log(self, msg, level="info"):
        if self.logger:
            getattr(self.logger, level)(msg)

    @staticmethod
    def _unique_destination(dest_path: str) -> str:
    
        if not os.path.exists(dest_path):
            return dest_path
        base, ext = os.path.splitext(dest_path)
        counter = 1
        new_path = f"{base}_{counter}{ext}"
        while os.path.exists(new_path):
            counter += 1
            new_path = f"{base}_{counter}{ext}"
        return new_path

    def _is_within_allowed_roots(self, path: str) -> bool:
        
        resolved = os.path.abspath(path)
        for root in self._allowed_roots:
            try:
                if os.path.commonpath([resolved, root]) == root:
                    return True
            except ValueError:
                # poate aparea pe Windows la unitati de disc diferite; pe Linux e rar
                continue
        return False

    def _do_move(self, src: str, dest: str) -> str:

        if not self._is_within_allowed_roots(dest):
            msg = (
                f"Destinatie respinsa (in afara folderelor permise, posibil path traversal): "
                f"'{dest}'"
            )
            self._log(msg, "error")
            if self.stats:
                self.stats.increment("errors")
            raise PathSecurityError(msg)

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
            self.stats.record_addition(os.path.basename(dest), dest)
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

    def has_companion_video(self, subtitle_path: str, video_extensions: list) -> bool:
       
        sub_dir = os.path.dirname(subtitle_path)
        sub_stem = os.path.splitext(os.path.basename(subtitle_path))[0].lower()

        if not os.path.isdir(sub_dir):
            return False

        for name in os.listdir(sub_dir):
            ext = os.path.splitext(name)[1].lower()
            if ext not in video_extensions:
                continue
            video_stem = os.path.splitext(name)[0].lower()
            if sub_stem == video_stem or sub_stem.startswith(video_stem):
                return True
        return False

    def find_matching_subtitle(self, video_path: str, subtitle_extensions: list) -> str | None:
      
        video_dir = os.path.dirname(video_path)
        video_stem = os.path.splitext(os.path.basename(video_path))[0].lower()

        if not os.path.isdir(video_dir):
            return None

        for name in os.listdir(video_dir):
            ext = os.path.splitext(name)[1].lower()
            if ext not in subtitle_extensions:
                continue
            sub_stem = os.path.splitext(name)[0].lower()
            # potrivire exacta SAU numele subtitrarii incepe cu numele video-ului
            # (acopera cazul "Film.ro.srt" pentru "Film.mkv")
            if sub_stem == video_stem or sub_stem.startswith(video_stem):
                return os.path.join(video_dir, name)
        return None

    def move_subtitle_alongside(self, subtitle_path: str, video_dest_path: str) -> str:
       
        sub_ext = os.path.splitext(subtitle_path)[1]
        video_dest_dir = os.path.dirname(video_dest_path)
        video_dest_stem = os.path.splitext(os.path.basename(video_dest_path))[0]

        dest_path = os.path.join(video_dest_dir, f"{video_dest_stem}{sub_ext}")
        result = self._do_move(subtitle_path, dest_path)
        self._log(f"Subtitrare asociata mutata alaturi de video: '{result}'")
        return result

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