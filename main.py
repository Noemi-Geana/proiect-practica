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


class OrganizerContext:
   

    def __init__(self, config_path: str, dry_run: bool = False, interactive: bool = False):
        self.config = Config(config_path)
        if dry_run:
            self.config._data["behavior"]["dry_run"] = True

        self.config.ensure_directories()
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

        # index de hash-uri pentru detectarea duplicatelor fata de ce e deja organizat
        self.duplicates.build_index(self.config.paths["media_root"])

    def confirm(self, message: str) -> bool:
        if not self.interactive:
            return True
        answer = input(f"{message} [y/N]: ").strip().lower()
        return answer == "y"


def fetch_and_save_metadata(ctx: OrganizerContext, filename: str, dest_path: str, is_series: bool):

    if ctx.config.behavior.get("dry_run", False):
        return  # nu interogam API-ul in simulare

    info = parse_series(filename) if is_series else parse_movie(filename)
    title = info["title"]
    year = info.get("year") if not is_series else None

    metadata = ctx.metadata_api.fetch(title, year)
    if metadata:
        dest_dir = os.path.dirname(dest_path)
        ctx.metadata_api.download_poster(metadata, dest_dir)
        ctx.metadata_api.save_nfo(metadata, dest_dir)


def process_file(ctx: OrganizerContext, filepath: str, source_folder: str):
    
    filename = os.path.basename(filepath)

    if not os.path.isfile(filepath):
        return

    category = ctx.classifier.classify(filepath)

    if category == FileCategory.INCOMPLETE:
        ctx.logger.info(f"Fișier incomplet, ignorat: {filename}")
        ctx.stats.increment("skipped_incomplete")
        return

    if category == FileCategory.SUBTITLE:
        video_extensions = ctx.config.extensions.get("video", [])
        if ctx.mover.has_companion_video(filepath, video_extensions):
            ctx.logger.info(f"Subtitrare '{filename}' amânată — va fi asociată cu videoclipul ei")
            return

    # arhive: extragem continutul, apoi procesam recursiv fisierele extrase
    if category == FileCategory.ARCHIVE:
        extracted_dir = ctx.archive_handler.extract(
            filepath, dry_run=ctx.config.behavior.get("dry_run", False)
        )
        if extracted_dir and os.path.isdir(extracted_dir):
            for root, _, files in os.walk(extracted_dir):
                for name in files:
                    process_file(ctx, os.path.join(root, name), source_folder)
        return

    # verificare duplicate (doar pentru fisiere media, nu documente mici)
    if category in (FileCategory.VIDEO, FileCategory.AUDIO, FileCategory.PICTURE):
        existing = ctx.duplicates.find_duplicate(filepath)
        if existing:
            ctx.logger.warning(f"Duplicat detectat: '{filename}' == '{existing}'")
            if ctx.config.behavior.get("auto_delete_duplicates", False):
                if ctx.confirm(f"Ștergi duplicatul '{filename}'?"):
                    if not ctx.config.behavior.get("dry_run", False):
                        os.remove(filepath)
                    ctx.logger.info(f"Duplicat șters: {filename}")
                    ctx.stats.increment("duplicates")
                    return
            else:
                if ctx.confirm(f"Muți duplicatul '{filename}' în Duplicates/?"):
                    ctx.mover.move_to_duplicates(filepath)
                    return

    if not ctx.confirm(f"Muți '{filename}' (categorie: {category})?"):
        ctx.logger.info(f"Mutare anulată de utilizator pentru: {filename}")
        return

    # inainte de mutarea video-ului, cautam o subtitrare asociata in acelasi folder
    subtitle_path = None
    if category == FileCategory.VIDEO:
        subtitle_extensions = ctx.config.extensions.get("subtitles", [])
        subtitle_path = ctx.mover.find_matching_subtitle(filepath, subtitle_extensions)

    dest_path = ctx.mover.route(filepath, category, source_folder)

    # daca am gasit o subtitrare asociata, o mutam alaturi de video, la noua locatie
    if subtitle_path and dest_path:
        ctx.mover.move_subtitle_alongside(subtitle_path, dest_path)

    # dupa mutare, daca e film/serial, incercam sa obtinem metadate
    if dest_path and category == FileCategory.VIDEO and source_folder in ("movies", "series"):
        fetch_and_save_metadata(ctx, filename, dest_path, is_series=(source_folder == "series"))


def process_downloads(ctx: OrganizerContext):

    downloads_root = ctx.config.paths["downloads"]

    subfolder_map = {
        "Movies": "movies",
        "Series": "series",
        "Music": "music",
    }

    if not os.path.isdir(downloads_root):
        ctx.logger.error(f"Folderul Downloads '{downloads_root}' nu există.")
        return

    # 1. subfolderele speciale
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

    # 2. fisiere direct in radacina Downloads (documente, executabile, poze, etc.)
    for name in os.listdir(downloads_root):
        full_path = os.path.join(downloads_root, name)
        if os.path.isdir(full_path):
            continue  # Movies/Series/Music deja procesate mai sus
        try:
            process_file(ctx, full_path, "root")
        except Exception as e:
            ctx.logger.error(f"Eroare la procesarea '{full_path}': {e}")
            ctx.stats.increment("errors")

    cleanup_empty_folders(ctx, downloads_root)


def cleanup_empty_folders(ctx: OrganizerContext, root: str):
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


def run_once(ctx: OrganizerContext):
    ctx.logger.info("=== Pornire organizare Downloads ===")
    process_downloads(ctx)
    summary = ctx.stats.summary_text()
    ctx.logger.info(summary)
    print("\n" + summary)

    global_summary = ctx.stats.global_summary_text(ctx.config)
    ctx.logger.info(global_summary)
    print("\n" + global_summary)
    ctx.stats.save_global()

    ctx.notifier.notify_summary(
        moved=ctx.stats.get("moved"),
        errors=ctx.stats.get("errors"),
        duplicates=ctx.stats.get("duplicates"),
    )


def run_watch(ctx: OrganizerContext):
    from proiect.watcher import start_watching

    downloads_root = ctx.config.paths["downloads"]
    watch_paths = [downloads_root]

    def callback(filepath: str):
        # determinam source_folder in functie de subfolderul in care a aparut fisierul
        rel = os.path.relpath(filepath, downloads_root)
        parts = rel.split(os.sep)
        mapping = {"Movies": "movies", "Series": "series", "Music": "music"}
        source_folder = mapping.get(parts[0], "root") if len(parts) > 1 else "root"
        process_file(ctx, filepath, source_folder)

    start_watching(watch_paths, callback, logger=ctx.logger)


def run_undo(ctx: OrganizerContext):
    success, failed = ctx.history.undo_last_run()
    print(f"Undo finalizat: {success} fișiere restaurate, {failed} eșuate.")
    ctx.logger.info(f"Undo executat: {success} reușite, {failed} eșuate.")


def build_arg_parser() -> argparse.ArgumentParser:
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
    parser = build_arg_parser()
    args = parser.parse_args()

    try:
        ctx = OrganizerContext(args.config, dry_run=args.dry_run, interactive=args.interactive)
    except ConfigError as e:
        print(f"Eroare de configurare: {e}", file=sys.stderr)
        sys.exit(1)

    if args.undo:
        run_undo(ctx)
    elif args.watch:
        run_watch(ctx)
    else:
        run_once(ctx)


if __name__ == "__main__":
    main()