import hashlib
import os


class DuplicateDetector:
    # Detectează fișierele duplicate pe baza codului unic (SHA256)

    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger
        self._known_codes = {}  # cod -> filepath

    def _log(self, msg, level="info"):
        if self.logger:
            getattr(self.logger, level)(msg)

    @staticmethod
    def compute_hash(filepath: str, chunk_size: int = 65536) -> str:
        # Calculează codul unic (SHA256) al fișierului (citi în bucăți pentru fișiere mari)
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def build_index(self, root_dir: str):
        # Scanează Media/ și indexează codurile tuturor fișierelor
        if not os.path.isdir(root_dir):
            return
        
        for dirpath, _, filenames in os.walk(root_dir):
            for name in filenames:
                full_path = os.path.join(dirpath, name)
                try:
                    cod = self.compute_hash(full_path)
                    self._known_codes[cod] = full_path
                except (OSError, PermissionError) as e:
                    self._log(f"Nu s-a putut citi {full_path}: {e}", "warning")

    def find_duplicate(self, filepath: str):
        # Verifică dacă fișierul deja există în Media/ comparând codul
        try:
            cod = self.compute_hash(filepath)
        except (OSError, PermissionError) as e:
            self._log(f"Nu s-a putut calcula codul pentru {filepath}: {e}", "warning")
            return None
        
        # Dacă codul e în index, e duplicat
        existing = self._known_codes.get(cod)
        if existing and os.path.abspath(existing) != os.path.abspath(filepath):
            return existing
        
        # Nu e duplicat - adaugă în index pentru viitor
        self._known_codes[cod] = filepath
        return None