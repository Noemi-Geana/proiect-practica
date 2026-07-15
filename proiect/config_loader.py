"""
config_loader.py
-----------------
Incarca fisierul de configurare (config.yaml) si expune datele
intr-un obiect usor de folosit in restul aplicatiei.
Toate caile din config sunt expandate automat (~ -> /home/user/...).
"""

import os
import yaml


class ConfigError(Exception):
    """Eroare specifica problemelor de configurare."""
    pass


class Config:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self._data = self._load(config_path)
        self._expand_paths()

    def _load(self, path: str) -> dict:
        if not os.path.exists(path):
            raise ConfigError(
                f"Fisierul de configurare '{path}' nu exista. "
                f"Copiaza 'config.example.yaml' ca 'config.yaml' si completeaza-l."
            )
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            raise ConfigError(f"Fisierul de configurare '{path}' este gol sau invalid.")
        return data

    def _expand_paths(self):
        """Transforma '~' in calea reala catre home si face path-urile absolute."""
        paths = self._data.get("paths", {})
        for key, value in paths.items():
            paths[key] = os.path.abspath(os.path.expanduser(value))
        self._data["paths"] = paths

    # --- Acces convenabil la sectiuni ---
    @property
    def paths(self) -> dict:
        return self._data["paths"]

    @property
    def subfolders(self) -> dict:
        return self._data.get("subfolders", {})

    @property
    def extensions(self) -> dict:
        return self._data.get("extensions", {})

    @property
    def api(self) -> dict:
        return self._data.get("api", {})

    @property
    def logging_cfg(self) -> dict:
        return self._data.get("logging", {})

    @property
    def history_cfg(self) -> dict:
        return self._data.get("history", {})

    @property
    def behavior(self) -> dict:
        return self._data.get("behavior", {})

    def get(self, *keys, default=None):
        """Acces generic: config.get('api', 'omdb_key')"""
        node = self._data
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                return default
            node = node[k]
        return node

    def ensure_directories(self):
        """Creeaza toate directoarele din 'paths' daca nu exista deja."""
        for key, path in self.paths.items():
            os.makedirs(path, exist_ok=True)
        # subfoldere Movies/Series/Music in media_root
        media_root = self.paths.get("media_root")
        if media_root:
            for sub in self.subfolders.values():
                os.makedirs(os.path.join(media_root, sub), exist_ok=True)

