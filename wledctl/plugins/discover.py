"""Find WLED devices on the LAN via mDNS. Needs `avahi-browse` (package: avahi-utils)."""
import shutil
import subprocess

from ..client import WLEDError


def register(app):
    @app.command("discover", help="Scan the network for WLED devices (mDNS)")
    def discover(args, app):
        if not shutil.which("avahi-browse"):
            raise WLEDError("avahi-browse not found. Install it: sudo apt install avahi-utils")
        out = subprocess.run(["avahi-browse", "-rtp", "_wled._tcp"],
                             capture_output=True, text=True, timeout=15).stdout
        seen = set()
        for line in out.splitlines():
            f = line.split(";")
            # resolved lines: =;iface;proto;name;type;domain;host;address;port;txt
            if f[0] == "=" and f[2] == "IPv4" and f[7] not in seen:
                seen.add(f[7])
                print(f"{f[3]:<25} {f[7]}")
        if not seen:
            print("No WLED devices found.")
