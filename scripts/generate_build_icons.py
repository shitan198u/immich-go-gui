#!/usr/bin/env python3
"""Generate Windows .ico and macOS .icns build icons from the app PNG (dev tool; requires Pillow)."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover - dev-only script
    raise SystemExit(
        "Pillow is required for icon generation. Install with: uv pip install pillow"
    ) from exc

DEFAULT_ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
DEFAULT_ICNS_SIZES = (16, 32, 64, 128, 256, 512)


def generate_ico(
    png_path: Path, ico_path: Path, sizes: tuple[int, ...] = DEFAULT_ICO_SIZES
) -> None:
    with Image.open(png_path) as img:
        rgba = img.convert("RGBA")
        rgba.save(
            ico_path,
            format="ICO",
            sizes=[(size, size) for size in sizes],
        )


def generate_icns(
    png_path: Path, icns_path: Path, sizes: tuple[int, ...] = DEFAULT_ICNS_SIZES
) -> None:
    with Image.open(png_path) as img:
        rgba = img.convert("RGBA")
        rgba.save(
            icns_path,
            format="ICNS",
            sizes=[(size, size) for size in sizes],
        )


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--png",
        type=Path,
        default=root / "immich-go-gui.png",
        help="Source PNG image",
    )
    parser.add_argument(
        "--ico",
        type=Path,
        default=root / "immich-go-gui.ico",
        help="Output ICO path",
    )
    parser.add_argument(
        "--icns",
        type=Path,
        default=root / "immich-go-gui.icns",
        help="Output ICNS path",
    )
    args = parser.parse_args()
    if not args.png.is_file():
        raise SystemExit(f"PNG not found: {args.png}")
    generate_ico(args.png, args.ico)
    generate_icns(args.png, args.icns)
    print(f"Wrote {args.ico} ({', '.join(str(s) for s in DEFAULT_ICO_SIZES)}px)")
    print(f"Wrote {args.icns} ({', '.join(str(s) for s in DEFAULT_ICNS_SIZES)}px)")


if __name__ == "__main__":
    main()
