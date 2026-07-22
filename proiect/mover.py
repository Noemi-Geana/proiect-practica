import os
import shutil
from proiect.classifier import FileCategory
from proiect.duplicates import DuplicateDetector
from proiect.name_parser import parse_movie, parse_series, parse_music


class PathSecurityError(Exception):
    # Dacă cineva încearcă mutare în afara folderelor permise
    pass


class Mover:
    # Gestionează mutările de fișiere din Downloads → Media

    def __init__(self, config, logger=None, history=None, stats=None):
        self.config = config
        self.logger = logger
        self.history = history
        self.stats = stats
        self.dry_run = config.behavior.get("dry_run", False)
        
        # Folderele în care e permisă mutarea
        self._allowed_roots = [os.path.abspath(p) for p in config.paths.values()]
        extra_roots = config.media_locations.get("extra_roots", [])
        self._allowed_roots.extend(extra_roots)
        self._extra_media_roots = extra_roots
        
        # Template-uri pentru denumire din config
        self._naming = config.naming

    def _log(self, msg, level="info"):
        if self.logger:
            getattr(self.logger, level)(msg)

    def _unique_destination(self, dest: str) -> str:
        # Dacă fișierul deja există, adaugă _1, _2, etc
        if not os.path.exists(dest):
            return dest
        base, ext = os.path.splitext(dest)
        counter = 1
        while os.path.exists(f"{base}_{counter}{ext}"):
            counter += 1
        return f"{base}_{counter}{ext}"

    def _is_within_allowed_roots(self, path: str) -> bool:
        # Blochează path traversal: nici ../../etc/passwd
        resolved = os.path.abspath(path)
        for root in self._allowed_roots:
            try:
                if os.path.commonpath([resolved, root]) == root:
                    return True
            except ValueError:
                continue
        return False

    def _do_move(self, src: str, dest: str) -> str:
        # 1. Validare path, 2. Hash înainte, 3. Mutare, 4. Hash după (integritate)
        
        if not self._is_within_allowed_roots(dest):
            self._log(f"Path traversal detectat: '{dest}'", "error")
            if self.stats:
                self.stats.increment("errors")
            raise PathSecurityError(f"Destinatie respinsa: {dest}")
        
        dest = self._unique_destination(dest)
        
        if self.dry_run:
            self._log(f"[DRY-RUN] Ar muta: '{src}' → '{dest}'")
            return dest
        
        # Hash înainte
        hash_before = None
        try:
            hash_before = DuplicateDetector.compute_hash(src)
        except OSError:
            pass
        
        # Mutare
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(src, dest)
        
        # Hash după + verificare
        if hash_before is not None:
            hash_after = None
            try:
                hash_after = DuplicateDetector.compute_hash(dest)
            except OSError:
                pass
            
            if hash_after and hash_after != hash_before:
                self._log(f"ATENTIE: hash diferit pentru '{dest}'", "error")
                if self.stats:
                    self.stats.increment("errors")
            else:
                self._log(f"Integritate OK: '{dest}'")
        
        self._log(f"Mutat: '{src}' → '{dest}'")
        
        if self.history:
            self.history.record_move(src, dest)
        if self.stats:
            self.stats.increment("moved")
            self.stats.record_addition(os.path.basename(dest), dest)
        
        return dest

    def move_movie(self, filepath: str) -> str:
        # Film: Downloads/Movies/Film.mkv → Media/Movies/2024/Film/Film.mkv
        filename = os.path.basename(filepath)
        ext = os.path.splitext(filename)[1]
        info = parse_movie(filename)
        title, year = info["title"], info["year"]
        
        if not title or title == "Unknown":
            return self.move_to_unsorted(filepath, reason="Titlu neidentificat")
        
        year_folder = str(year) if year else "AnNecunoscut"
        dest_dir = os.path.join(self.config.paths["media_root"], 
                                self.config.subfolders.get("movies", "Movies"),
                                year_folder, title)
        return self._do_move(filepath, os.path.join(dest_dir, f"{title}{ext}"))

    def move_series(self, filepath: str) -> str:
        # Serial: Downloads/Series/Serial.S05E12.mkv → Media/Series/Serial/Sezonul 05/Episodul 12/
        filename = os.path.basename(filepath)
        info = parse_series(filename)
        title, season, episode = info["title"], info["season"], info["episode"]
        
        if season is None or episode is None:
            return self.move_to_unsorted(filepath, reason="Sezon/episod neidentificat")
        
        dest_dir = os.path.join(self.config.paths["media_root"],
                                self.config.subfolders.get("series", "Series"),
                                title, 
                                f"Sezonul {season:02d}", 
                                f"Episodul {episode:02d}")
        return self._do_move(filepath, os.path.join(dest_dir, filename))

    def move_music(self, filepath: str) -> str:
        # Muzică: Downloads/Music/Song.mp3 → Media/Music/Artist/Song.mp3
        filename = os.path.basename(filepath)
        ext = os.path.splitext(filename)[1]
        info = parse_music(filename)
        artist = info["artist"] or "Artist Necunoscut"
        track = info["track"]
        
        dest_dir = os.path.join(self.config.paths["media_root"],
                                self.config.subfolders.get("music", "Music"),
                                artist)
        return self._do_move(filepath, os.path.join(dest_dir, f"{track}{ext}"))

    def move_document(self, filepath: str) -> str:
        # Document: Downloads/doc.pdf → Media/Documents/doc.pdf
        return self._do_move(filepath, os.path.join(self.config.paths["documents"], 
                                                     os.path.basename(filepath)))

    def move_executable(self, filepath: str) -> str:
        # Executable: Downloads/app.exe → Media/Executables/app.exe
        return self._do_move(filepath, os.path.join(self.config.paths["executables"], 
                                                     os.path.basename(filepath)))

    def move_picture(self, filepath: str) -> str:
        # Poză: Downloads/photo.jpg → Media/Pictures/photo.jpg
        return self._do_move(filepath, os.path.join(self.config.paths["pictures"], 
                                                     os.path.basename(filepath)))

    def has_companion_video(self, subtitle_path: str, video_extensions: list) -> bool:
        # Verifică dacă deja există video cu același nume lângă subtitrare
        sub_dir = os.path.dirname(subtitle_path)
        sub_stem = os.path.splitext(os.path.basename(subtitle_path))[0].lower()
        
        if not os.path.isdir(sub_dir):
            return False
        
        for name in os.listdir(sub_dir):
            if os.path.splitext(name)[1].lower() in video_extensions:
                video_stem = os.path.splitext(name)[0].lower()
                if sub_stem == video_stem or sub_stem.startswith(video_stem):
                    return True
        return False

    def find_matching_subtitle(self, video_path: str, subtitle_extensions: list) -> str | None:
        # Caută subtitrare cu același nume de bază ca video-ul
        video_dir = os.path.dirname(video_path)
        video_stem = os.path.splitext(os.path.basename(video_path))[0].lower()
        
        if not os.path.isdir(video_dir):
            return None
        
        for name in os.listdir(video_dir):
            if os.path.splitext(name)[1].lower() in subtitle_extensions:
                sub_stem = os.path.splitext(name)[0].lower()
                if sub_stem == video_stem or sub_stem.startswith(video_stem):
                    return os.path.join(video_dir, name)
        return None

    def move_subtitle_alongside(self, subtitle_path: str, video_dest_path: str) -> str:
        # Mută subtitrarea alaturi de video cu același nume de bază
        sub_ext = os.path.splitext(subtitle_path)[1]
        video_dest_dir = os.path.dirname(video_dest_path)
        video_dest_stem = os.path.splitext(os.path.basename(video_dest_path))[0]
        
        dest_path = os.path.join(video_dest_dir, f"{video_dest_stem}{sub_ext}")
        result = self._do_move(subtitle_path, dest_path)
        self._log(f"Subtitrare asociata: '{result}'")
        return result

    def move_to_duplicates(self, filepath: str) -> str:
        # Mută duplicatul în Media/Duplicates/
        dest_path = os.path.join(self.config.paths["duplicates"], os.path.basename(filepath))
        result = self._do_move(filepath, dest_path)
        if self.stats:
            self.stats.increment("duplicates")
        return result

    def move_to_unsorted(self, filepath: str, reason: str = "") -> str:
        # Mută fișierul nesortat în Media/Unsorted/
        dest_path = os.path.join(self.config.paths["unsorted"], os.path.basename(filepath))
        if reason:
            self._log(f"Nesortat '{os.path.basename(filepath)}': {reason}", "warning")
        result = self._do_move(filepath, dest_path)
        if self.stats:
            self.stats.increment("unsorted")
        return result

    def route(self, filepath: str, category: str, source_folder: str) -> str | None:
        # Rutează fișierul la metoda potrivită pe baza tipului și locației
        
        if source_folder == "movies" and category == FileCategory.VIDEO:
            return self.move_movie(filepath)
        if source_folder == "series" and category == FileCategory.VIDEO:
            return self.move_series(filepath)
        if source_folder == "music" and category == FileCategory.AUDIO:
            return self.move_music(filepath)
        
        if category == FileCategory.DOCUMENT:
            return self.move_document(filepath)
        if category == FileCategory.EXECUTABLE:
            return self.move_executable(filepath)
        if category == FileCategory.PICTURE:
            return self.move_picture(filepath)
        
        return self.move_to_unsorted(filepath, reason=f"Categorie '{category}' fără regulă")