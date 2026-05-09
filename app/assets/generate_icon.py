"""
Generates the application icon (icon.png and icon.ico) using Pillow.
Run once: python app/assets/generate_icon.py
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

SIZE = 512
OUT = os.path.join(os.path.dirname(__file__), "icon.png")
OUT_ICO = os.path.join(os.path.dirname(__file__), "icon.ico")


def _draw_play_triangle(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, color: tuple) -> None:
    """Draw a centred equilateral play triangle."""
    pts = [
        (cx - r * 0.45, cy - r * 0.55),
        (cx - r * 0.45, cy + r * 0.55),
        (cx + r * 0.6,  cy),
    ]
    draw.polygon(pts, fill=color)


def _draw_shuffle_arrows(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, color: tuple) -> None:
    """Draw two crossing shuffle arrows beneath the play icon area."""
    lw = max(4, int(r * 0.06))
    # Arrow 1: lower-left to upper-right
    x0, y0 = cx - r * 0.38, cy + r * 0.35
    x1, y1 = cx + r * 0.38, cy - r * 0.05
    draw.line([(x0, y0), (x1, y1)], fill=color, width=lw)
    # Arrow 2: upper-left to lower-right
    x0b, y0b = cx - r * 0.38, cy - r * 0.05
    x1b, y1b = cx + r * 0.38, cy + r * 0.35
    draw.line([(x0b, y0b), (x1b, y1b)], fill=color, width=lw)
    # Arrowheads (right side)
    ah = lw * 2.5
    for tip, ang in [((x1, y1), -30), ((x1b, y1b), 30)]:
        for da in [-35, 35]:
            rad = math.radians(ang + da)
            ex = tip[0] - ah * math.cos(rad)
            ey = tip[1] - ah * math.sin(rad)
            draw.line([tip, (ex, ey)], fill=color, width=lw)


def generate(path: str = OUT) -> None:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background circle - deep navy gradient approximated by two ellipses
    bg_outer = (15, 18, 40, 255)
    bg_inner = (30, 35, 75, 255)
    draw.ellipse([0, 0, SIZE, SIZE], fill=bg_outer)
    margin = SIZE * 0.12
    draw.ellipse([margin, margin, SIZE - margin, SIZE - margin], fill=bg_inner)

    cx, cy, r = SIZE / 2, SIZE / 2, SIZE * 0.42

    # Accent ring
    ring_color = (99, 102, 241)  # indigo-500
    draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        outline=ring_color,
        width=max(6, int(SIZE * 0.018)),
    )

    # Play triangle (white)
    _draw_play_triangle(draw, cx, cy - r * 0.12, r * 0.55, (255, 255, 255, 240))

    # Shuffle arrows (indigo)
    _draw_shuffle_arrows(draw, cx, cy + r * 0.42, r * 0.55, (150, 153, 255, 220))

    img.save(path, "PNG")
    print(f"Icon saved -> {path}")

    # Also generate .ico (Windows) next to the .png
    ico_path = os.path.splitext(path)[0] + ".ico"
    sizes = [256, 128, 64, 48, 32, 16]
    ico_images = [img.resize((s, s), Image.LANCZOS) for s in sizes]
    ico_images[0].save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=ico_images[1:],
    )
    print(f"Icon saved -> {ico_path}")


if __name__ == "__main__":
    generate()
