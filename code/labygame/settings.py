"""Read/write the player's settings (res/data/settings.json)."""
import json
import os

from .tiles import RES

SETTINGS_FILE = os.path.join(RES, "data", "settings.json")


def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f)
    except OSError:
        pass
