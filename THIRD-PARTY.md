# Third-party sources

Axelrod uses these open-source sources, each under its own licence.

| Source | Licence | Note |
|---|---|---|
| Python package PIL | MIT-CMU | Pillow is only imported by the dev tool make_icon.py, not bundled; Pillow's licence is the HPND/MIT-CMU style licence, so the automatic guess is right. |
| Python package PyQt6 | GPL-3.0-only | PyQt6 is imported (gui.py, charts.py), not copied; it is available under GPL-3.0 (or a commercial licence). Distributing with PyQt6 under GPL means the release licence must be GPL-compatible. |
