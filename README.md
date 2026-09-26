# wledctl

Modular terminal controller for WLED. Standard library only (Python 3.11+).

## Install
    ./install.sh
    nano ~/.config/wledctl/config.toml     # set your WLED IP

## Usage
    wledctl on | off | toggle [-t SECONDS]
    wledctl color red | ff8800 | 255,136,0 [-s SEGMENT]
    wledctl brightness 40                  # percent (--raw for 0-255)
    wledctl presets ; wledctl preset "Movie"
    wledctl effects ; wledctl effect blink --speed 200 --palette ocean
    wledctl nightlight 20                  # fade out over 20 min
    wledctl scene movie                    # scenes from config.toml
    wledctl status | info | discover
    wledctl raw '{"on":true,"bri":80}'     # anything the WLED JSON API supports
    wledctl -d desk -d shelf color blue    # pick devices; -d all for every one

## Boot behaviour
`install.sh` enables a systemd *user* service. At login it waits for your WLED
to come online, then applies `[startup]` from the config. On logout/shutdown it
applies `[shutdown]`. Test manually: `wledctl startup`.
Logs: `journalctl --user -u wledctl`.

## Architecture
    wledctl/client.py    WLED JSON API wrapper (only place that does networking)
    wledctl/app.py       device resolution, plugin loader, CLI dispatch
    wledctl/plugins/     each file = a feature; auto-loaded via register(app)
    ~/.config/wledctl/plugins/*.py   your own plugins, same API

To add an integration (MQTT, Home Assistant, a daemon, ...): write a plugin,
use `app.run_on(args, fn)` for device access and `app.on_startup(fn)` for boot
hooks. See plugins/example_plugin.py.disabled.
