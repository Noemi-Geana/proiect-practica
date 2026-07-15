import os
import shutil
import subprocess
import zipfile


class ArchiveHandler:
    def __init__(self, config, logger=None):
        self.logger = logger
        self.enabled = config.behavior.get("extract_archives", True)

    def _log(self, msg, level="info"):
        if self.logger:
            getattr(self.logger, level)(msg)

    @staticmethod
    def is_archive(filepath: str) -> bool:
        ext = os.path.splitext(filepath)[1].lower()
        return ext in (".zip", ".rar", ".7z")

    def extract(self, filepath: str, dry_run: bool = False) -> str | None:
        
        if not self.enabled or not self.is_archive(filepath):
            return None

        base_dir = os.path.dirname(filepath)
        name_no_ext = os.path.splitext(os.path.basename(filepath))[0]
        dest_dir = os.path.join(base_dir, name_no_ext)

        if dry_run:
            self._log(f"[DRY-RUN] Ar extrage '{filepath}' in '{dest_dir}'")
            return dest_dir

        os.makedirs(dest_dir, exist_ok=True)
        ext = os.path.splitext(filepath)[1].lower()

        try:
            if ext == ".zip":
                with zipfile.ZipFile(filepath, "r") as zf:
                    zf.extractall(dest_dir)
            elif ext == ".rar":
                if shutil.which("unrar"):
                    subprocess.run(["unrar", "x", "-y", filepath, dest_dir + os.sep],
                                    check=True, capture_output=True)
                else:
                    self._log("Unealta 'unrar' nu e instalata. Instaleaza cu: sudo apt install unrar", "warning")
                    return None
            elif ext == ".7z":
                if shutil.which("7z"):
                    subprocess.run(["7z", "x", f"-o{dest_dir}", "-y", filepath],
                                    check=True, capture_output=True)
                else:
                    self._log("Unealta '7z' nu e instalata. Instaleaza cu: sudo apt install p7zip-full", "warning")
                    return None
            else:
                return None

            self._log(f"Arhiva '{filepath}' extrasa cu succes in '{dest_dir}'")
            return dest_dir

        except (zipfile.BadZipFile, subprocess.CalledProcessError, OSError) as e:
            self._log(f"Eroare la extragerea arhivei '{filepath}': {e}", "error")
            return None