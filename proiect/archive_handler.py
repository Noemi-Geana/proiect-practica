import os
import shutil
import subprocess
import zipfile


class ArchiveHandler:
    """Extrage arhive (.zip, .rar, .7z)"""

    def __init__(self, config, logger=None):
        self.logger = logger
        self.enabled = config.behavior.get("extract_archives", True)

    def _log(self, msg, level="info"):
        """Loghează un mesaj dacă logger e disponibil"""
        if self.logger:
            getattr(self.logger, level)(msg)

    @staticmethod
    def is_archive(filepath: str) -> bool:
        """Verifică dacă fișierul e arhivă"""
        ext = os.path.splitext(filepath)[1].lower()
        return ext in (".zip", ".rar", ".7z")

    def extract(self, filepath: str, dry_run: bool = False) -> str | None:
        """Extrage arhiva și returnează folderul unde s-a extras"""
        
        # E dezactivat sau nu e arhivă
        if not self.enabled or not self.is_archive(filepath):
            return None
        
        # Folderul de destinație
        base_dir = os.path.dirname(filepath)
        name_no_ext = os.path.splitext(os.path.basename(filepath))[0]
        dest_dir = os.path.join(base_dir, name_no_ext)
        
        # Dry-run: doar loghează
        if dry_run:
            self._log(f"[DRY-RUN] Ar extrage '{filepath}' în '{dest_dir}'")
            return dest_dir
        
        # Crează folder
        os.makedirs(dest_dir, exist_ok=True)
        ext = os.path.splitext(filepath)[1].lower()
        
        try:
            # .zip - nativ cu Python
            if ext == ".zip":
                with zipfile.ZipFile(filepath, "r") as zf:
                    zf.extractall(dest_dir)
            
            # .rar - necesită 'unrar'
            elif ext == ".rar":
                if not shutil.which("unrar"):
                    self._log("'unrar' nu e instalat. Instaleaza: sudo apt install unrar", "warning")
                    return None
                subprocess.run(["unrar", "x", "-y", filepath, dest_dir + os.sep],
                               check=True, capture_output=True)
            
            # .7z - necesită '7z'
            elif ext == ".7z":
                if not shutil.which("7z"):
                    self._log("'7z' nu e instalat. Instaleaza: sudo apt install p7zip-full", "warning")
                    return None
                subprocess.run(["7z", "x", f"-o{dest_dir}", "-y", filepath],
                               check=True, capture_output=True)
            
            self._log(f"Extras: '{filepath}' în '{dest_dir}'")
            return dest_dir
        
        except (zipfile.BadZipFile, subprocess.CalledProcessError, OSError) as e:
            self._log(f"Eroare la extragere: {e}", "error")
            return None