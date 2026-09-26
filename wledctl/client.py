"""Thin client for the WLED JSON API (https://kno.wled.ge/interfaces/json-api/).

Only the standard library is used, so there is nothing to `pip install`.
Everything else in the project talks to WLED through this class, so if you
ever want to add MQTT / UDP / websocket transport, this is the place.
"""
import json
import time
import urllib.error
import urllib.request


class WLEDError(Exception):
    """Raised for any communication or lookup problem."""


class WLEDClient:
    def __init__(self, host: str, timeout: float = 3.0):
        self.host = host
        self.timeout = timeout
        self.base = f"http://{host}"

    # ---- low level -------------------------------------------------------
    def _request(self, path: str, payload: dict | None = None):
        data, headers = None, {}
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            self.base + path, data=data, headers=headers,
            method="POST" if payload is not None else "GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode() or "{}"
                return json.loads(body)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
            raise WLEDError(f"{self.host}: {e}") from e

    # ---- reads -----------------------------------------------------------
    def get_state(self) -> dict:
        return self._request("/json/state")

    def get_info(self) -> dict:
        return self._request("/json/info")

    def get_effects(self) -> list[str]:
        return self._request("/json/effects")  # index in list == effect id

    def get_palettes(self) -> list[str]:
        return self._request("/json/palettes")  # index in list == palette id

    def get_presets(self) -> dict[int, str]:
        """Return {preset_id: name}. Empty slots are skipped."""
        raw = self._request("/presets.json")
        return {int(k): v.get("n", f"Preset {k}") for k, v in raw.items() if v}

    # ---- writes ----------------------------------------------------------
    def set_state(self, state: dict, transition: float | None = None) -> dict:
        """POST a raw state object. `transition` is in seconds (WLED wants 100ms units)."""
        if transition is not None:
            state = {**state, "transition": int(transition * 10)}
        return self._request("/json/state", state)

    def power(self, on: bool | None = None, transition: float | None = None):
        """on=True/False sets power, on=None toggles."""
        return self.set_state({"on": "t" if on is None else on}, transition)

    def set_brightness(self, bri: int, transition: float | None = None):
        return self.set_state({"on": True, "bri": max(0, min(255, bri))}, transition)

    def set_color(self, rgb: list[int], segment: int | None = None, transition=None):
        # "seg" as an object applies to all selected segments; as a list it targets ids.
        seg = {"col": [rgb]} if segment is None else [{"id": segment, "col": [rgb]}]
        return self.set_state({"on": True, "seg": seg}, transition)

    def set_preset(self, preset: int | str):
        return self.set_state({"on": True, "ps": self.resolve_preset(preset)})

    def set_effect(self, effect=None, speed=None, intensity=None, palette=None):
        seg: dict = {}
        if effect is not None:
            seg["fx"] = self.resolve_effect(effect)
        if speed is not None:
            seg["sx"] = speed
        if intensity is not None:
            seg["ix"] = intensity
        if palette is not None:
            seg["pal"] = self.resolve_palette(palette)
        return self.set_state({"on": True, "seg": seg})

    def nightlight(self, minutes: int, target_bri: int = 0):
        """Fade to `target_bri` over `minutes` (WLED nightlight mode 1 = fade)."""
        return self.set_state({"nl": {"on": True, "dur": minutes, "mode": 1, "tbri": target_bri}})

    # ---- name -> id helpers ---------------------------------------------
    @staticmethod
    def _find(name: str, names: list[str], kind: str) -> int:
        low = name.lower()
        for i, n in enumerate(names):
            if n.lower() == low:
                return i
        matches = [i for i, n in enumerate(names) if low in n.lower()]
        if len(matches) == 1:
            return matches[0]
        raise WLEDError(f"{kind} {name!r} not found or ambiguous ({len(matches)} matches)")

    def resolve_effect(self, effect) -> int:
        s = str(effect)
        return int(s) if s.isdigit() else self._find(s, self.get_effects(), "Effect")

    def resolve_palette(self, palette) -> int:
        s = str(palette)
        return int(s) if s.isdigit() else self._find(s, self.get_palettes(), "Palette")

    def resolve_preset(self, preset) -> int:
        s = str(preset)
        if s.isdigit():
            return int(s)
        presets = self.get_presets()
        for pid, n in presets.items():
            if n.lower() == s.lower():
                return pid
        raise WLEDError(f"Preset {preset!r} not found")

    # ---- connectivity ----------------------------------------------------
    def wait_until_reachable(self, max_seconds: float = 60, interval: float = 2) -> bool:
        """Poll until the device answers. Useful at boot, when Wi-Fi may lag behind."""
        deadline = time.monotonic() + max_seconds
        while True:
            try:
                self.get_info()
                return True
            except WLEDError:
                if time.monotonic() >= deadline:
                    return False
                time.sleep(interval)
