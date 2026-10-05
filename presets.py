import json
from pathlib import Path

PRESETS_DIR = Path.home() / '.config' / 'sound-helper' / 'presets'


class PresetManager:
    def __init__(self):
        PRESETS_DIR.mkdir(parents=True, exist_ok=True)

    def list_presets(self):
        return sorted([f.stem for f in PRESETS_DIR.glob('*.json')])

    def save(self, name, data):
        path = PRESETS_DIR / f'{name}.json'
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def load(self, name):
        path = PRESETS_DIR / f'{name}.json'
        with open(path) as f:
            return json.load(f)

    def delete(self, name):
        path = PRESETS_DIR / f'{name}.json'
        if path.exists():
            path.unlink()
