
import hashlib
import os


class DuplicateDetector:
    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger
        self._known_hashes = {}  # hash -> filepath

    def _log(self, msg, level="info"):
        if self.logger:
            getattr(self.logger, level)(msg)

    @staticmethod
    def compute_hash(filepath: str, chunk_size: int = 65536) -> str:
        
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def build_index(self, root_dir: str):
        
        if not os.path.isdir(root_dir):
            return
        for dirpath, _, filenames in os.walk(root_dir):
            for name in filenames:
                full_path = os.path.join(dirpath, name)
                try:
                    file_hash = self.compute_hash(full_path)
                    self._known_hashes[file_hash] = full_path
                except (OSError, PermissionError) as e:
                    self._log(f"Nu s-a putut citi {full_path}: {e}", "warning")

    def find_duplicate(self, filepath: str):
        
        try:
            file_hash = self.compute_hash(filepath)
        except (OSError, PermissionError) as e:
            self._log(f"Nu s-a putut calcula hash pentru {filepath}: {e}", "warning")
            return None

        existing = self._known_hashes.get(file_hash)
        if existing and os.path.abspath(existing) != os.path.abspath(filepath):
            return existing

        # nu era duplicat -> il adaugam in index pentru comparatii viitoare
        self._known_hashes[file_hash] = filepath
        return None