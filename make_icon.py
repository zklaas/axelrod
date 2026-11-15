#!/usr/bin/env python3
"""Build the Axelrod icon: a wheel axle (two wheels on a shaft, seen
end-on) with a rod laid across behind it - "axle" + "rod".  The wheels are
the program's cooperate green and defect red.

Dev tool - needs Pillow.  Run, then ./install-desktop.sh to refresh the dash.
"""
import math
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "icons")
SS = 4                      # supersampling
N = 512 * SS

BG = (232, 236, 242)
EDGE = (60, 72, 92)
STEEL = (120, 132, 150)
STEEL_HI = (184, 194, 208)
ROD = (176, 122, 52)
ROD_HI = (222, 170, 92)
GREEN = (58, 154, 91)
RED = (209, 73, 91)


def s(v):
    return int(v * SS)


def wheel(d, cx, cy, rx, ry, colour):
    # Tyre: an upright ellipse (a wheel seen nearly edge-on from the front).
    d.ellipse([s(cx - rx), s(cy - ry), s(cx + rx), s(cy + ry)], fill=EDGE)
    d.ellipse([s(cx - rx + 9), s(cy - ry + 9), s(cx + rx - 9), s(cy + ry - 9)], fill=colour)
    # Spokes, foreshortened.
    for k in range(6):
        a = math.pi * k / 6
        x = math.cos(a) * (rx - 14)
        y = math.sin(a) * (ry - 14)
        d.line([s(cx - x), s(cy - y), s(cx + x), s(cy + y)], fill=EDGE, width=s(6))
    # Hub.
    d.ellipse([s(cx - 16), s(cy - 26), s(cx + 16), s(cy + 26)], fill=STEEL_HI, outline=EDGE, width=s(5))


def main():
    os.makedirs(OUT, exist_ok=True)
    img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([s(16), s(16), s(496), s(496)], radius=s(92), fill=BG, outline=EDGE, width=s(8))

    # The rod: a long round bar laid diagonally behind the axle.
    x0, y0, x1, y1 = 92, 420, 420, 92
    d.line([s(x0), s(y0), s(x1), s(y1)], fill=EDGE, width=s(40))
    d.line([s(x0), s(y0), s(x1), s(y1)], fill=ROD, width=s(28))
    d.line([s(x0 + 4), s(y0 - 8), s(x1 + 4), s(y1 - 8)], fill=ROD_HI, width=s(8))
    for (x, y) in ((x0, y0), (x1, y1)):
        d.ellipse([s(x - 20), s(y - 20), s(x + 20), s(y + 20)], fill=ROD, outline=EDGE, width=s(6))

    # The axle shaft between the two wheels.
    cy = 262
    d.rounded_rectangle([s(130), s(cy - 17), s(382), s(cy + 17)], radius=s(17), fill=STEEL, outline=EDGE, width=s(6))
    d.line([s(140), s(cy - 6), s(372), s(cy - 6)], fill=STEEL_HI, width=s(6))

    wheel(d, 122, cy, 62, 150, GREEN)
    wheel(d, 390, cy, 62, 150, RED)

    big = img.resize((512, 512), Image.LANCZOS)
    big.save(os.path.join(OUT, "axelrod.png"))
    for size in (256, 128, 64, 48):
        big.resize((size, size), Image.LANCZOS).save(os.path.join(OUT, f"axelrod-{size}.png"))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
