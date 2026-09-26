"""Named scenes defined in config.toml under [scenes.<name>].

A scene is a raw WLED state object, so anything the WLED JSON API accepts works.
Usage: wledctl scene movie
"""
from ..client import WLEDError


def register(app):
    @app.command("scene", help="Apply a scene from the config file",
                 setup=lambda p: p.add_argument("name", nargs="?", help="scene name (omit to list)"))
    def scene(args, app):
        scenes = app.config.get("scenes", {})
        if not args.name:
            print("\n".join(scenes) or "(no scenes defined)")
            return 0
        if args.name not in scenes:
            raise WLEDError(f"Unknown scene {args.name!r}. Available: {', '.join(scenes) or 'none'}")
        return app.run_on(args, lambda c: c.set_state({"on": True, **scenes[args.name]}))
