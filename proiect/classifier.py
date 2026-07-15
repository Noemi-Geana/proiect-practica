
import os

try:
    import magic  # python-magic
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


# Maparea categoriilor MIME (folosite de python-magic) catre categoriile noastre
_MIME_MAP = {
    "video": FileCategory.VIDEO,
    "audio": FileCategory.AUDIO,
    "image": FileCategory.PICTURE,
    "application/pdf": FileCategory.DOCUMENT,
    "application/zip": FileCategory.ARCHIVE,
    "application/x-rar": FileCategory.ARCHIVE,
    "application/x-7z-compressed": FileCategory.ARCHIVE,
    "application/x-executable": FileCategory.EXECUTABLE,
    "application/x-sharedlib": FileCategory.EXECUTABLE,
    "application/x-elf": FileCategory.EXECUTABLE,
}


class FileClassifier:
    def __init__(self, config, logger=None):
        self.extensions = config.extensions
        self.logger = logger

    def _log(self, msg, level="info"):
        if self.logger:
            getattr(self.logger, level)(msg)

    def is_incomplete(self, filepath: str) -> bool:
        ext = os.path.splitext(filepath)[1].lower()
        return ext in self.extensions.get("incomplete", [])

    def classify_by_extension(self, filepath: str) -> str:
        ext = os.path.splitext(filepath)[1].lower()
        for category, ext_list in self.extensions.items():
            if category == "incomplete":
                continue
            if ext in ext_list:
                # numele categoriei din config -> constanta FileCategory
                return {
                    "video": FileCategory.VIDEO,
                    "audio": FileCategory.AUDIO,
                    "documents": FileCategory.DOCUMENT,
                    "executables": FileCategory.EXECUTABLE,
                    "archives": FileCategory.ARCHIVE,
                    "subtitles": FileCategory.SUBTITLE,
                    "pictures": FileCategory.PICTURE,
                }.get(category, FileCategory.UNKNOWN)
        return FileCategory.UNKNOWN

    def classify_by_content(self, filepath: str) -> str:
       
        if not MAGIC_AVAILABLE:
            return FileCategory.UNKNOWN
        try:
            mime = magic.from_file(filepath, mime=True)  # ex: "video/mp4"
        except Exception as e:
            self._log(f"Eroare la citirea magic bytes pentru {filepath}: {e}", "warning")
            return FileCategory.UNKNOWN

        if mime in _MIME_MAP:
            return _MIME_MAP[mime]
        main_type = mime.split("/")[0]
        return _MIME_MAP.get(main_type, FileCategory.UNKNOWN)

    def classify(self, filepath: str) -> str:
        
        if self.is_incomplete(filepath):
            return FileCategory.INCOMPLETE

        category = self.classify_by_extension(filepath)
        if category != FileCategory.UNKNOWN:
            return category

        # extensia nu a ajutat -> incercam dupa continut (magic bytes)
        category = self.classify_by_content(filepath)
        if category != FileCategory.UNKNOWN:
            self._log(
                f"Fisierul '{filepath}' a fost clasificat dupa continut (magic bytes) "
                f"ca '{category}', extensia nefiind concludenta.",
                "info",
            )
        return category