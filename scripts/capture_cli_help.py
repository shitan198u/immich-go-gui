#!/usr/bin/env python3
"""Script to capture immich-go CLI help outputs into versioned test fixtures.

Pure Python, Qt-free script.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.binary_manager import get_binary_path, load_binary_metadata, TESTED_IMMICH_GO_VERSION


TARGET_COMMANDS = {
    "root": [],
    "upload": ["upload"],
    "upload_from-folder": ["upload", "from-folder"],
    "upload_from-google-photos": ["upload", "from-google-photos"],
    "upload_from-immich": ["upload", "from-immich"],
    "archive": ["archive"],
    "archive_from-folder": ["archive", "from-folder"],
    "archive_from-immich": ["archive", "from-immich"],
    "stack": ["stack"],
}


def capture_help_for_version(binary_path: Path, version: str, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_commands = {}

    for name, args in TARGET_COMMANDS.items():
        cmd = [str(binary_path)] + args + ["--help"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            text = res.stdout if res.stdout else res.stderr
        except Exception as e:
            text = f"Error capturing help for {' '.join(args)}: {e}"

        out_file = out_dir / f"{name}.txt"
        out_file.write_text(text, encoding="utf-8")
        manifest_commands[name] = args

    manifest = {
        "version": version,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "binary_path": str(binary_path),
        "commands": manifest_commands,
    }

    manifest_file = out_dir / "manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return manifest


def main():
    parser = argparse.ArgumentParser(description="Capture immich-go CLI help outputs.")
    parser.add_argument("--binary-path", type=str, help="Path to immich-go executable.")
    parser.add_argument("--version", type=str, default=TESTED_IMMICH_GO_VERSION, help="Target version tag.")
    args = parser.parse_args()

    if args.binary_path:
        bin_path = Path(args.binary_path).resolve()
    else:
        meta = load_binary_metadata()
        bin_path = Path(get_binary_path(meta)).resolve()

    fixtures_dir = PROJECT_ROOT / "tests" / "fixtures" / "cli_help" / args.version
    print(f"Capturing CLI help using binary: {bin_path} -> {fixtures_dir}")

    manifest = capture_help_for_version(bin_path, args.version, fixtures_dir)
    print(f"Successfully captured {len(manifest['commands'])} help targets.")


if __name__ == "__main__":
    main()
