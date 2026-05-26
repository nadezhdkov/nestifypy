import sys
from pathlib import Path
from pynest.yaml import Yaml

# Monkeypatch Yaml to fix the bug
def index_file(self, filepath: Path, data: dict) -> None:
    self._walk(str(filepath.resolve()), data, prefix="")
Yaml._registry.index_file = index_file.__get__(Yaml._registry)

def _global_get(cls, path: str, default=None):
    filename = cls._registry.find(path)
    if filename is None:
        return default
    config = cls._cache.get(filename)
    if config is None:
        return default
    return config.get(path, default)

Yaml.scan(".")

print("Registry:", Yaml.registry())
print("Yaml.get('database'):", Yaml.get("database"))
print("Yaml.get('database.host'):", Yaml.get("database.host"))
