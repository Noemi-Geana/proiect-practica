import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class DownloadsHandler(FileSystemEventHandler):
    def __init__(self, process_callback, logger=None, settle_seconds: float = 2.0):
       
        self.process_callback = process_callback
        self.logger = logger
        self.settle_seconds = settle_seconds

    def _log(self, msg, level="info"):
        if self.logger:
            getattr(self.logger, level)(msg)

    def _handle_path(self, filepath: str):
        if not filepath:
            return
        # asteapta putin ca fisierul sa se "stabilizeze" (sa nu mai fie scris)
        time.sleep(self.settle_seconds)
        try:
            self.process_callback(filepath)
        except Exception as e:
            self._log(f"Eroare la procesarea automata a '{filepath}': {e}", "error")

    def on_created(self, event):
        if not event.is_directory:
            self._handle_path(event.src_path)

    def on_moved(self, event):
        # relevant cand un fisier e redenumit din .crdownload/.part in extensia finala
        if not event.is_directory:
            self._handle_path(event.dest_path)


def start_watching(paths_to_watch: list, process_callback, logger=None):
    
    handler = DownloadsHandler(process_callback, logger=logger)
    observer = Observer()

    for path in paths_to_watch:
        observer.schedule(handler, path, recursive=True)
        if logger:
            logger.info(f"Se monitorizeaza folderul: {path}")

    observer.start()
    if logger:
        logger.info("Watcher pornit. Apasa Ctrl+C pentru a opri.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        if logger:
            logger.info("Watcher oprit de utilizator.")
    observer.join()