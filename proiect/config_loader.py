import os
import yaml


class ConfigError(Exception):
    """Eroare la citirea sau validarea configurației"""
    pass


class Config:
    """Citește config.yaml și oferă acces la setări"""

    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self._data = self._load(config_path)
        self._expand_paths()

    # ================================================================
    # ÎNCĂRCARE - Citire din YAML
    # ================================================================

    def _load(self, path: str) -> dict:
        """Citește și validează config.yaml"""
        if not os.path.exists(path):
            raise ConfigError(
                f"Fișierul '{path}' nu există.\n"
                f"Copiază 'config.example.yaml' ca 'config.yaml' și completează-l."
            )
        
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        if not data:
            raise ConfigError(f"Fișierul '{path}' este gol sau invalid.")
        
        return data

    def _expand_paths(self):
        """Transformă '~' în cale reală și face paths absolute"""
        paths = self._data.get("paths", {})
        for key, value in paths.items():
            paths[key] = os.path.abspath(os.path.expanduser(value))
        self._data["paths"] = paths

    # ================================================================
    # ACCES - Proprietăți pentru fiecare secțiune
    # ================================================================

    @property
    def paths(self) -> dict:
        """Downloads, Media, Documents, etc"""
        return self._data["paths"]

    @property
    def subfolders(self) -> dict:
        """Movies, Series, Music - subfoldere în Media/"""
        return self._data.get("subfolders", {})

    @property
    def extensions(self) -> dict:
        """Tipuri de fișiere: video, audio, documents, etc"""
        return self._data.get("extensions", {})

    @property
    def api(self) -> dict:
        """API keys și URLs: OMDB, TMDb"""
        return self._data.get("api", {})

    @property
    def logging_cfg(self) -> dict:
        """Configurare logging: log_file, level, etc"""
        return self._data.get("logging", {})

    @property
    def history_cfg(self) -> dict:
        """Configurare history: history_file"""
        return self._data.get("history", {})

    @property
    def behavior(self) -> dict:
        """Comportament: dry_run, auto_delete, notifications"""
        return self._data.get("behavior", {})

    @property
    def naming(self) -> dict:
        """Template-uri pentru denumire: {title}, {year}, etc"""
        return self._data.get("naming", {})

    @property
    def media_locations(self) -> dict:
        """Locații media suplimentare: extra_roots"""
        return self._data.get("media_locations", {})

    # ================================================================
    # ACCES GENERIC - Pentru orice cale în config
    # ================================================================

    def get(self, *keys, default=None):
        """
        Acces generic: config.get('api', 'omdb_key')
        Merge prin orice adâncime: config.get('a', 'b', 'c', default=None)
        """
        node = self._data
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node

    # ================================================================
    # SETUP - Creare directoare
    # ================================================================

    def ensure_directories(self):
        """Crează toate folderele din config dacă nu există"""
        
        # Crează folderele principale (Downloads, Media, Documents, etc)
        for key, path in self.paths.items():
            os.makedirs(path, exist_ok=True)
        
        # Crează subfoldere în Media (Movies, Series, Music)
        media_root = self.paths.get("media_root")
        if media_root:
            for subfolder in self.subfolders.values():
                os.makedirs(os.path.join(media_root, subfolder), exist_ok=True)