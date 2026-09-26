"""Application core: device resolution, plugin loading and CLI dispatch.

HOW TO EXTEND
-------------
A plugin is just a Python file with a `register(app)` function.
Drop it in `wledctl/plugins/` (built-in) or `~/.config/wledctl/plugins/` (yours).
Inside `register`, declare commands with `@app.command(...)`:

    def register(app):
        def setup(p):                     # optional: add argparse arguments
            p.add_argument("value", type=int)

        @app.command("hello", help="Say hello", setup=setup)
        def hello(args, app):             # `app` gives access to config + devices
            return app.run_on(args, lambda client: print(client.get_info()["name"]))

Plugins can also call `app.on_startup(fn)` / `app.on_shutdown(fn)` to attach
extra work to the boot/shutdown hooks (see plugins/startup.py).
"""
import argparse
import importlib
import importlib.util
import pkgutil
import sys
from dataclasses import dataclass
from typing import Callable

from . import config as config_mod
from . import plugins as builtin_plugins
from .client import WLEDClient, WLEDError


@dataclass
class Command:
    name: str
    help: str
    setup: Callable | None
    handler: Callable


class App:
    def __init__(self, config: dict):
        self.config = config
        self.commands: dict[str, Command] = {}
        self.startup_hooks: list[Callable] = []   # fn(app, client)
        self.shutdown_hooks: list[Callable] = []  # fn(app, client)
        self.timeout = 3.0

    # ---- plugin API ------------------------------------------------------
    def command(self, name: str, help: str = "", setup: Callable | None = None):
        def deco(fn):
            self.commands[name] = Command(name, help, setup, fn)
            return fn
        return deco

    def on_startup(self, fn):
        self.startup_hooks.append(fn)
        return fn

    def on_shutdown(self, fn):
        self.shutdown_hooks.append(fn)
        return fn

    # ---- devices ---------------------------------------------------------
    def clients(self, target: list[str] | None) -> list[WLEDClient]:
        """Resolve --device values into clients.

        target can hold config names, raw hosts/IPs, or "all".
        With no target we use `default_device`, or the only configured device.
        """
        devices: dict = self.config.get("devices", {})
        target = target or ([self.config["default_device"]] if "default_device" in self.config else [])
        if not target and len(devices) == 1:
            target = list(devices)
        if not target:
            raise WLEDError("No device selected. Use -d HOST, or set [devices] and default_device in the config.")
        hosts: list[str] = []
        for t in target:
            if t == "all":
                hosts += list(devices.values())
            else:
                hosts.append(devices.get(t, t))  # unknown name -> treat as hostname/IP
        return [WLEDClient(h, self.timeout) for h in dict.fromkeys(hosts)]

    def run_on(self, args, fn: Callable[[WLEDClient], None]) -> int:
        """Run fn(client) on every selected device; report errors per device."""
        rc = 0
        for c in self.clients(args.device):
            try:
                fn(c)
            except WLEDError as e:
                print(f"error: {e}", file=sys.stderr)
                rc = 1
        return rc

    # ---- plumbing --------------------------------------------------------
    def load_plugins(self):
        for m in pkgutil.iter_modules(builtin_plugins.__path__):
            mod = importlib.import_module(f"{builtin_plugins.__name__}.{m.name}")
            if hasattr(mod, "register"):
                mod.register(self)
        if config_mod.USER_PLUGIN_DIR.is_dir():
            for path in sorted(config_mod.USER_PLUGIN_DIR.glob("*.py")):
                spec = importlib.util.spec_from_file_location(f"wledctl_user_{path.stem}", path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "register"):
                    mod.register(self)

    def build_parser(self) -> argparse.ArgumentParser:
        p = argparse.ArgumentParser(prog="wledctl", description="Control WLED devices from the terminal.")
        p.add_argument("-d", "--device", action="append", help="device name, host/IP, or 'all' (repeatable)")
        p.add_argument("--timeout", type=float, default=3.0, help="HTTP timeout in seconds")
        sub = p.add_subparsers(dest="cmd", required=True, metavar="COMMAND")
        for c in sorted(self.commands.values(), key=lambda c: c.name):
            sp = sub.add_parser(c.name, help=c.help, description=c.help)
            if c.setup:
                c.setup(sp)
        return p

    def run(self, argv: list[str]) -> int:
        args = self.build_parser().parse_args(argv)
        self.timeout = args.timeout
        try:
            return self.commands[args.cmd].handler(args, self) or 0
        except WLEDError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2


def main(argv: list[str] | None = None) -> int:
    app = App(config_mod.load())
    app.load_plugins()
    return app.run(sys.argv[1:] if argv is None else argv)
