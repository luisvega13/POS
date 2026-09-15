import json
import logging
from pathlib import Path
from threading import RLock

DEFAULT_CONFIG = {"printer_name": "", "encoding": "cp850", "character_table": None}

class ConfigService:
    def __init__(self, path: Path):
        self.path, self._lock = path, RLock()
        if not path.exists():
            self.save(DEFAULT_CONFIG.copy())
    def load(self):
        with self._lock:
            try:
                return {**DEFAULT_CONFIG, **json.loads(self.path.read_text(encoding="utf-8"))}
            except (OSError, json.JSONDecodeError, TypeError):
                logging.exception("No se pudo leer config.json")
                return DEFAULT_CONFIG.copy()
    def save(self, data):
        with self._lock:
            self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    def set_printer(self, name):
        data = self.load()
        data["printer_name"] = name
        self.save(data)
        return data
    def set_character_table(self, table):
        data = self.load()
        data["character_table"] = table
        self.save(data)
        return data
