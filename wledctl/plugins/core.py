"""Core commands: power, colour, brightness, presets, effects, palettes, status, raw JSON."""
import json

from ..colors import parse_color


def _transition_arg(p):
    p.add_argument("-t", "--transition", type=float, help="fade time in seconds")


def register(app):
    # ---- power -----------------------------------------------------------
    for name, value in (("on", True), ("off", False), ("toggle", None)):
        def make(value):
            def handler(args, app):
                return app.run_on(args, lambda c: c.power(value, args.transition))
            return handler
        app.command(name, help=f"Turn LEDs {name}" if value is not None else "Toggle power",
                    setup=_transition_arg)(make(value))

    # ---- colour ----------------------------------------------------------
    def color_setup(p):
        p.add_argument("color", help="name, hex (ff8800) or r,g,b")
        p.add_argument("-s", "--segment", type=int, help="segment id (default: all selected segments)")
        _transition_arg(p)

    @app.command("color", help="Set the primary colour", setup=color_setup)
    def color(args, app):
        rgb = parse_color(args.color)
        return app.run_on(args, lambda c: c.set_color(rgb, args.segment, args.transition))

    # ---- brightness ------------------------------------------------------
    def bri_setup(p):
        p.add_argument("value", type=int, help="0-100 (percent), or 0-255 with --raw")
        p.add_argument("--raw", action="store_true", help="value is 0-255 instead of percent")
        _transition_arg(p)

    @app.command("brightness", help="Set brightness", setup=bri_setup)
    def brightness(args, app):
        bri = args.value if args.raw else round(args.value * 255 / 100)
        return app.run_on(args, lambda c: c.set_brightness(bri, args.transition))

    # ---- presets ---------------------------------------------------------
    @app.command("preset", help="Apply a preset by id or name",
                 setup=lambda p: p.add_argument("preset"))
    def preset(args, app):
        return app.run_on(args, lambda c: c.set_preset(args.preset))

    def list_cmd(name, help, getter):
        @app.command(name, help=help)
        def _(args, app):
            def show(c):
                data = getattr(c, getter)()
                items = data.items() if isinstance(data, dict) else enumerate(data)
                for i, n in items:
                    print(f"{i:>3}  {n}")
            return app.run_on(args, show)

    list_cmd("presets", "List presets", "get_presets")
    list_cmd("effects", "List effects", "get_effects")
    list_cmd("palettes", "List palettes", "get_palettes")

    # ---- effect ----------------------------------------------------------
    def fx_setup(p):
        p.add_argument("effect", nargs="?", help="effect id or (partial) name")
        p.add_argument("--speed", type=int, help="0-255")
        p.add_argument("--intensity", type=int, help="0-255")
        p.add_argument("--palette", help="palette id or name")

    @app.command("effect", help="Set effect / speed / intensity / palette", setup=fx_setup)
    def effect(args, app):
        return app.run_on(args, lambda c: c.set_effect(args.effect, args.speed, args.intensity, args.palette))

    # ---- nightlight ------------------------------------------------------
    def nl_setup(p):
        p.add_argument("minutes", type=int, help="fade duration")
        p.add_argument("--target", type=int, default=0, help="final brightness 0-255 (default 0)")

    @app.command("nightlight", help="Gradually fade brightness (sleep timer)", setup=nl_setup)
    def nightlight(args, app):
        return app.run_on(args, lambda c: c.nightlight(args.minutes, args.target))

    # ---- inspection ------------------------------------------------------
    @app.command("status", help="Show current state")
    def status(args, app):
        def show(c):
            s, info = c.get_state(), c.get_info()
            seg = (s.get("seg") or [{}])[0]
            fx = seg.get("fx")
            fx_name = c.get_effects()[fx] if isinstance(fx, int) else "?"
            print(f"{info.get('name', c.host)} ({c.host}) v{info.get('ver')}: "
                  f"{'ON' if s.get('on') else 'OFF'}, bri {s.get('bri')}/255, "
                  f"preset {s.get('ps')}, effect {fx_name}, colours {seg.get('col')}")
        return app.run_on(args, show)

    @app.command("info", help="Dump device info as JSON")
    def info(args, app):
        return app.run_on(args, lambda c: print(json.dumps(c.get_info(), indent=2)))

    @app.command("raw", help="POST raw JSON to /json/state (full WLED API access)",
                 setup=lambda p: p.add_argument("json", help='e.g. \'{"on":true,"bri":50}\''))
    def raw(args, app):
        payload = json.loads(args.json)
        return app.run_on(args, lambda c: print(c.set_state(payload)))
