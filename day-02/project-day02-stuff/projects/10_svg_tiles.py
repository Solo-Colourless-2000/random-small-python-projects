"""SVG Tile Art."""
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 10_svg_tiles.py output.svg")
        return 2
    output = Path(sys.argv[1])
    if output.suffix.lower() != ".svg":
        print("Error: output must have a .svg extension.")
        return 2

    colors = ["#4ec4cc", "#b8e34a", "#e2a0b8", "#e8a54b"]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="240" height="240" viewBox="0 0 240 240">']
    parts.append('<rect width="240" height="240" fill="#0e1316"/>')

    for row in range(4):
        for column in range(4):
            x, y = 20 + column * 50, 20 + row * 50
            color = colors[(row + column) % len(colors)]
            parts.append(f'<rect x="{x}" y="{y}" width="40" height="40" rx="8" fill="{color}"/>')
    parts.append("</svg>")

    try:
        with output.open("x", encoding="utf-8") as file:
            file.write("\n".join(parts) + "\n")
    except OSError as error:
        print(f"Error: cannot save: {error}")
        return 1
    print(f"Saved: {output.as_posix()} (4x4 = 16 tiles)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
