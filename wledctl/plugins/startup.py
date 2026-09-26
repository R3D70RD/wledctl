"""Boot / shutdown behaviour. Run by the systemd user service (see systemd/).

Config ([startup] table) - all keys optional:
    enabled      = true
    device       = "all"        # config name, host, or "all"
    wait_seconds = 60           # wait this long for the device to come online
    transition   = 1.0
    scene        = "warm"       # a [scenes.*] entry, OR use the keys below
    preset       = "Rainbow"    # id or name
    color        = "ff6a00"
    effect       = "Breathe"
    brightness   = 50           # percent
[shutdown]
    turn_off     = true

Other plugins can add behaviour with app.on_startup(fn) / app.on_shutdown(fn).
"""
from ..client import WLEDError
from ..colors import parse_color


def apply_startup(app, c):
    cfg = app.config.get("startup", {})
    t = cfg.get("transition", 1.0)
    if "scene" in cfg:
        c.set_state({"on": True, **app.config.get("scenes", {})[cfg["scene"]]}, t)
    else:
        c.power(True, t)
        if "preset" in cfg:
            c.set_preset(cfg["preset"])
        if "color" in cfg:
            c.set_color(parse_color(cfg["color"]), transition=t)
        if "effect" in cfg:
            c.set_effect(cfg["effect"])
    if "brightness" in cfg:
        c.set_brightness(round(cfg["brightness"] * 255 / 100), t)


def apply_shutdown(app, c):
    if app.config.get("shutdown", {}).get("turn_off", False):
        c.power(False, 1.0)


def _run(app, args, hooks, builtin, wait: bool):
    cfg = app.config.get("startup", {})
    if not cfg.get("enabled", True) and wait:
        return 0
    targets = args.device or [cfg.get("device", "all")]
    rc = 0
    for c in app.clients(targets):
        try:
            if wait and not c.wait_until_reachable(cfg.get("wait_seconds", 60)):
                raise WLEDError(f"{c.host}: not reachable after {cfg.get('wait_seconds', 60)}s")
            builtin(app, c)
            for hook in hooks:
                hook(app, c)
        except (WLEDError, KeyError) as e:
            print(f"error: {e}", file=__import__("sys").stderr)
            rc = 1
    return rc


def register(app):
    @app.command("startup", help="Apply the [startup] settings (used at boot)")
    def startup(args, app):
        return _run(app, args, app.startup_hooks, apply_startup, wait=True)

    @app.command("shutdown", help="Apply the [shutdown] settings")
    def shutdown(args, app):
        return _run(app, args, app.shutdown_hooks, apply_shutdown, wait=False)
