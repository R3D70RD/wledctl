#!/usr/bin/env bash
# Installs wledctl for the current user (no root, no pip). Requires Python >= 3.11.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.local/share/wledctl"
BIN="$HOME/.local/bin"
mkdir -p "$DEST" "$BIN" "$HOME/.config/wledctl/plugins" "$HOME/.config/systemd/user"

rm -rf "$DEST/wledctl" && cp -r "$SRC/wledctl" "$DEST/"
printf '#!/usr/bin/env bash\nPYTHONPATH="%s" exec python3 -m wledctl "$@"\n' "$DEST" > "$BIN/wledctl"
chmod +x "$BIN/wledctl"

[ -f "$HOME/.config/wledctl/config.toml" ] || cp "$SRC/config.example.toml" "$HOME/.config/wledctl/config.toml"
cp "$SRC/systemd/wledctl.service" "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable --now wledctl.service || true

echo "Done. Edit ~/.config/wledctl/config.toml (set your WLED IP), then try: wledctl status"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "Note: add $BIN to your PATH.";; esac
