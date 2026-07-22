import os

try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False


class FileCategory:
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    EXECUTABLE = "executable"
    ARCHIVE = "archive"
    SUBTITLE = "subtitle"
    PICTURE = "picture"
    INCOMPLETE = "incomplete"
    UNKNOWN = "unknown" 


class FileClassifier:
    # Clasifică fișiere: 1. Incomplete?, 2. Extensie?, 3. Conținut (magic)?

    def __init__(self, config, logger=None):
        self.extensions = config.extensions
        self.logger = logger

    def _log(self, msg, level="info"):
        if self.logger:
            getattr(self.logger, level)(msg)

    def classify(self, filepath: str) -> str:
        ext = os.path.splitext(filepath)[1].lower()
        
        # 1. E fișier incomplet?
        if ext in self.extensions.get("incomplete", []):
            return FileCategory.INCOMPLETE
        
        # 2. Clasifică după extensie
        category = self._classify_by_extension(ext)
        if category:
            return category
        
        # 3. Dacă extensia nu ajută, încearcă magic bytes
        if MAGIC_AVAILABLE:
            category = self._classify_by_magic(filepath)
            if category:
                self._log(f"'{filepath}' clasificat după conținut ca '{category}'")
                return category
        
        # Default
        return FileCategory.DOCUMENT

    def _classify_by_extension(self, ext: str) -> str | None:
        # Cauta extensia în config
        ext_map = {
            "video": FileCategory.VIDEO,
            "audio": FileCategory.AUDIO,
            "documents": FileCategory.DOCUMENT,
            "executables": FileCategory.EXECUTABLE,
            "archives": FileCategory.ARCHIVE,
            "subtitles": FileCategory.SUBTITLE,
            "pictures": FileCategory.PICTURE,
        }
        
        for config_key, category in ext_map.items():
            if ext in self.extensions.get(config_key, []):
                return category
        
        return None

    def _classify_by_magic(self, filepath: str) -> str | None:
        # Citește magic bytes și determină tipul
        try:
            mime = magic.from_file(filepath, mime=True)
        except Exception:
            return None
        
        # Mapare MIME → categorie
        mime_map = {
            "video": FileCategory.VIDEO,
            "audio": FileCategory.AUDIO,
            "image": FileCategory.PICTURE,
            "application/pdf": FileCategory.DOCUMENT,
            "application/zip": FileCategory.ARCHIVE,
            "application/x-rar": FileCategory.ARCHIVE,
            "application/x-7z-compressed": FileCategory.ARCHIVE,
            "application/x-executable": FileCategory.EXECUTABLE,
            "application/x-sharedlib": FileCategory.EXECUTABLE,
        }
        
        # Verificare 
        if mime in mime_map:
            return mime_map[mime]
        
        # Verific prefixul (ex: "video/mp4" → "video")
        main_type = mime.split("/")[0]
        return mime_map.get(main_type)