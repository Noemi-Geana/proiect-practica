import argparse
import os
import sys

from proiect.archive_handler import ArchiveHandler
from proiect.classifier import FileCategory, FileClassifier
from proiect.config_loader import Config, ConfigError
from proiect.duplicates import DuplicateDetector
from proiect.history import History
from proiect.logger import setup_logger
from proiect.metadata_api import MetadataAPI
from proiect.mover import Mover
from proiect.name_parser import parse_movie, parse_series
from proiect.notifier import Notifier
from proiect.stats import Stats


# ================================================================
# CONTEXT - Orchestrator principal
# ================================================================

class OrganizerContext:
    """Coordoneaza toate componentele aplicatiei"""

    def __init__(self, config_path: str, dry_run: bool = False, interactive: bool = False):
        # Citeste config
        self.config = Config(config_path)
        if dry_run:
            self.config._data["behavior"]["dry_run"] = True
        
        # Creeaza folderele necesare
        self.config.ensure_directories()
        
        # Initializeaza toate componentele
        self.logger = setup_logger(self.config)
        self.stats = Stats(self.config)
        self.history = History(self.config, self.logger)
        self.classifier = FileClassifier(self.config, self.logger)
        self.duplicates = DuplicateDetector(self.config, self.logger)
        self.archive_handler = ArchiveHandler(self.config, self.logger)
        self.metadata_api = MetadataAPI(self.config, self.logger)
        self.notifier = Notifier(self.config, self.logger)
        self.mover = Mover(self.config, self.logger, self.history, self.stats)
        self.interactive = interactive
        
        # Indexeaza fisierele din Media pentru detectarea duplicatelor
        self.duplicates.build_index(self.config.paths["media_root"])

    def confirm(self, message: str) -> bool:
        """Cere confirmare utilizatorului daca e in mod interactiv"""
        if not self.interactive:
            return True
        answer = input(f"{message} [y/N]: ").strip().lower()
        return answer == "y"


# ================================================================
# METADATE - Descarca info despre filme/serii
# ================================================================

def fetch_and_save_metadata(ctx: OrganizerContext, filename: str, dest_path: str, is_series: bool):
    """Descarca metadate (titlu, poster, rating) dupa mutare"""
    
    # Nu interogam API in dry-run
    if ctx.config.behavior.get("dry_run", False):
        return
    
    # Extrage titlu din nume
    info = parse_series(filename) if is_series else parse_movie(filename)
    title = info["title"]
    year = info.get("year") if not is_series else None
    
    # Interogheaza OMDB/TMDb
    metadata = ctx.metadata_api.fetch(title, year)
    
    if metadata:
        dest_dir = os.path.dirname(dest_path)
        ctx.metadata_api.download_poster(metadata, dest_dir)
        ctx.metadata_api.save_nfo(metadata, dest_dir)


# ================================================================
# PROCESARE - Procesează un singur fișier
# ================================================================

def process_file(ctx: OrganizerContext, filepath: str, source_folder: str):
    """Procesează un fișier: clasifică, verifică duplicate, mută"""
    
    filename = os.path.basename(filepath)
    
    # Fișierul trebuie să existe
    if not os.path.isfile(filepath):
        return
    
    # Clasifică fișierul
    category = ctx.classifier.classify(filepath)
    
    # Fișiere incomplete: ignoră
    if category == FileCategory.INCOMPLETE:
        ctx.logger.info(f"Fișier incomplet, ignorat: {filename}")
        ctx.stats.increment("skipped_incomplete")
        return
    
    # Subtitrări: amână până când mutăm video-ul
    if category == FileCategory.SUBTITLE:
        video_extensions = ctx.config.extensions.get("video", [])
        if ctx.mover.has_companion_video(filepath, video_extensions):
            ctx.logger.info(f"Subtitrare '{filename}' amânată — va fi asociată cu videoclipul ei")
            return
    
    # Arhive: extrage și procesează fișierele din interior
    if category == FileCategory.ARCHIVE:
        extracted_dir = ctx.archive_handler.extract(
            filepath, dry_run=ctx.config.behavior.get("dry_run", False)
        )
        if extracted_dir and os.path.isdir(extracted_dir):
            for root, _, files in os.walk(extracted_dir):
                for name in files:
                    process_file(ctx, os.path.join(root, name), source_folder)
        return
    
    # Verificare duplicate
    if category in (FileCategory.VIDEO, FileCategory.AUDIO, FileCategory.PICTURE):
        existing = ctx.duplicates.find_duplicate(filepath)
        if existing:
            ctx.logger.warning(f"Duplicat detectat: '{filename}' == '{os.path.basename(existing)}'")
            
            # Opțiunea 1: șterge automat (dacă e configurat)
            if ctx.config.behavior.get("auto_delete_duplicates", False):
                if ctx.confirm(f"Ștergi duplicatul '{filename}'?"):
                    if not ctx.config.behavior.get("dry_run", False):
                        os.remove(filepath)
                    ctx.logger.info(f"Duplicat șters: {filename}")
                    ctx.stats.increment("duplicates")
                return
            
            # Opțiunea 2: mută în Duplicates
            if ctx.confirm(f"Muți duplicatul '{filename}' în Duplicates/?"):
                ctx.mover.move_to_duplicates(filepath)
            return
    
    # Cere confirmare dacă e interactiv
    if not ctx.confirm(f"Muți '{filename}' (categorie: {category})?"):
        ctx.logger.info(f"Mutare anulată de utilizator pentru: {filename}")
        return
    
    # Cauta subtitrare pentru video
    subtitle_path = None
    if category == FileCategory.VIDEO:
        subtitle_extensions = ctx.config.extensions.get("subtitles", [])
        subtitle_path = ctx.mover.find_matching_subtitle(filepath, subtitle_extensions)
    
    # Mută fișierul
    dest_path = ctx.mover.route(filepath, category, source_folder)
    
    # Mută subtitrarea alaturi de video
    if subtitle_path and dest_path:
        ctx.mover.move_subtitle_alongside(subtitle_path, dest_path)
    
    # Descarca metadate pentru filme/serii
    if dest_path and category == FileCategory.VIDEO and source_folder in ("movies", "series"):
        fetch_and_save_metadata(ctx, filename, dest_path, is_series=(source_folder == "series"))


# ================================================================
# DESCOPERIRE - Gasește fișierele în Downloads
# ================================================================

def process_downloads(ctx: OrganizerContext):
    """Procesează toate fișierele din Downloads (fără progress bar)"""
    
    downloads_root = ctx.config.paths["downloads"]
    subfolder_map = {
        "Movies": "movies",
        "Series": "series",
        "Music": "music",
    }
    
    if not os.path.isdir(downloads_root):
        ctx.logger.error(f"Folderul Downloads '{downloads_root}' nu există.")
        return
    
    # Procesează subfolderele speciale (Movies, Series, Music)
    for folder_name, source_tag in subfolder_map.items():
        folder_path = os.path.join(downloads_root, folder_name)
        if not os.path.isdir(folder_path):
            continue
        
        for name in os.listdir(folder_path):
            full_path = os.path.join(folder_path, name)
            try:
                process_file(ctx, full_path, source_tag)
            except Exception as e:
                ctx.logger.error(f"Eroare la procesarea '{full_path}': {e}")
                ctx.stats.increment("errors")
    
    # Procesează fișierele direct în Downloads (documente, executabile, etc)
    for name in os.listdir(downloads_root):
        full_path = os.path.join(downloads_root, name)
        if os.path.isdir(full_path):
            continue  # Folderele speciale deja procesate mai sus
        
        try:
            process_file(ctx, full_path, "root")
        except Exception as e:
            ctx.logger.error(f"Eroare la procesarea '{full_path}': {e}")
            ctx.stats.increment("errors")
    
    # Șterge folderele goale
    cleanup_empty_folders(ctx, downloads_root)


def cleanup_empty_folders(ctx: OrganizerContext, root: str):
    """Șterge folderele goale din Downloads"""
    
    if ctx.config.behavior.get("dry_run", False):
        return
    
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        if dirpath == root:
            continue
        if not dirnames and not filenames:
            try:
                os.rmdir(dirpath)
                ctx.logger.info(f"Folder gol șters: {dirpath}")
            except OSError:
                pass


# ================================================================
# RULARE - Modurile de execuție
# ================================================================

def run_once(ctx: OrganizerContext):
    """Organizează fișierele o singură dată"""
    
    ctx.logger.info("=== Pornire organizare Downloads ===")
    
    try:
        # Încercă cu progress bar (tqdm)
        from tqdm import tqdm
        files_to_process = []
        downloads_root = ctx.config.paths["downloads"]
        
        # Colectează toate fișierele înainte de procesare
        for root, dirs, files in os.walk(downloads_root):
            for name in files:
                files_to_process.append(os.path.join(root, name))
        
        # Procesează cu progress bar
        for filepath in tqdm(files_to_process, desc="Organizare fișiere", unit="fișier"):
            try:
                rel = os.path.relpath(filepath, downloads_root)
                parts = rel.split(os.sep)
                mapping = {"Movies": "movies", "Series": "series", "Music": "music"}
                source_folder = mapping.get(parts[0], "root") if len(parts) > 1 else "root"
                process_file(ctx, filepath, source_folder)
            except Exception as e:
                ctx.logger.error(f"Eroare la procesarea '{filepath}': {e}")
                ctx.stats.increment("errors")
    except ImportError:
        # Fallback dacă tqdm nu-i disponibil
        process_downloads(ctx)
    
    # Afișează rapoarte
    summary = ctx.stats.summary_text()
    ctx.logger.info(summary)
    print("\n" + summary)
    
    global_summary = ctx.stats.global_summary_text(ctx.config)
    ctx.logger.info(global_summary)
    print("\n" + global_summary)
    
    # Salvează statistici
    ctx.stats.save_global()
    
    # Notificare desktop
    ctx.notifier.notify_summary(
        moved=ctx.stats.get("moved"),
        errors=ctx.stats.get("errors"),
        duplicates=ctx.stats.get("duplicates"),
    )


def run_watch(ctx: OrganizerContext):
    """Monitorizează Downloads și organizează automat"""
    
    from proiect.watcher import start_watching
    
    downloads_root = ctx.config.paths["downloads"]
    
    def callback(filepath: str):
        """Callback când apare un fișier nou"""
        rel = os.path.relpath(filepath, downloads_root)
        parts = rel.split(os.sep)
        mapping = {"Movies": "movies", "Series": "series", "Music": "music"}
        source_folder = mapping.get(parts[0], "root") if len(parts) > 1 else "root"
        process_file(ctx, filepath, source_folder)
    
    start_watching([downloads_root], callback, logger=ctx.logger)


def run_undo(ctx: OrganizerContext):
    """Anulează ultima rulare și restaurează fișierele"""
    
    success, failed = ctx.history.undo_last_run()
    print(f"Undo finalizat: {success} fișiere restaurate, {failed} eșuate.")
    ctx.logger.info(f"Undo executat: {success} reușite, {failed} eșuate.")


# ================================================================
# CLI - Argument parser și entry point
# ================================================================

def build_arg_parser() -> argparse.ArgumentParser:
    """Crează parser-ul pentru argumente de linie de comandă"""
    
    parser = argparse.ArgumentParser(
        description="Organizeaza automat fisierele din Downloads (filme, seriale, muzica, documente)."
    )
    parser.add_argument("--config", default="config/config.yaml", help="Cale catre fisierul de configurare")
    parser.add_argument("--dry-run", action="store_true", help="Simuleaza, fara sa mute fisiere real")
    parser.add_argument("--watch", action="store_true", help="Monitorizeaza continuu folderul Downloads")
    parser.add_argument("--undo", action="store_true", help="Anuleaza ultima rulare (restaureaza fisierele)")
    parser.add_argument("--interactive", action="store_true", help="Cere confirmare inainte de fiecare mutare")
    
    return parser

def main():
    """Entry point - parseaza argumentele și declanșează acțiunea"""
    
    parser = build_arg_parser()
    args = parser.parse_args()
    
    # Citește config și crează context
    try:
        ctx = OrganizerContext(args.config, dry_run=args.dry_run, interactive=args.interactive)
    except ConfigError as e:
        print(f"Eroare de configurare: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Execută acțiunea specifiată
    if args.undo:
        run_undo(ctx)
    elif args.watch:
        run_watch(ctx)
    else:
        run_once(ctx)


if __name__ == "__main__":
    main()