"""Config loading. File: ~/.config/wledctl/config.toml (see config.example.toml)."""
import os
import tomllib
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "wledctl"
CONFIG_PATH = CONFIG_DIR / "config.toml"
USER_PLUGIN_DIR = CONFIG_DIR / "plugins"


def load() -> dict:
    """Return the parsed config, or an empty dict if the file does not exist."""
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)
