"""
logger.py
---------
Configureaza logging-ul aplicatiei: scriere in fisier cu rotatie automata
(ca sa nu creasca la infinit) + afisare in consola.
"""

import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logger(config) -> logging.Logger:
    log_cfg = config.logging_cfg
    log_file = log_cfg.get("log_file", "logs/organizer.log")
    level_name = log_cfg.get("level", "INFO").upper()
    max_size_mb = log_cfg.get("max_size_mb", 5)
    backup_count = log_cfg.get("backup_count", 3)

    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)

    logger = logging.getLogger("organizer")
    logger.setLevel(getattr(logging, level_name, logging.INFO))
    logger.handlers.clear()  # evita duplicarea handler-elor la rerun (ex. in teste)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = RotatingFileHandler(
        log_file, maxBytes=max_size_mb * 1024 * 1024, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    return logger