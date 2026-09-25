"""Install missing recommended Visual Studio Code extensions."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

EXTENSIONS_FILE = Path(".vscode/extensions.json")


def _recommended_extensions() -> list[str]:
    if not EXTENSIONS_FILE.is_file():
        return []
    data = json.loads(EXTENSIONS_FILE.read_text(encoding="utf-8"))
    recommendations = data.get("recommendations", [])
    return [item for item in recommendations if isinstance(item, str)]


def update_extensions(*, assume_yes: bool = False) -> int:
    """Install recommended extensions that are not already installed."""
    code = shutil.which("code")
    if code is None:
        print("Visual Studio Code CLI unavailable; skipping.")
        return 0
    result = subprocess.run(
        [code, "--list-extensions"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        print(f"Could not list VS Code extensions: {detail}", file=sys.stderr)
        return 1
    installed = {line.strip().casefold() for line in result.stdout.splitlines()}
    missing = [
        extension
        for extension in _recommended_extensions()
        if extension.casefold() not in installed
    ]
    if not missing:
        print("VS Code extensions unchanged.")
        return 0
    print("Missing VS Code extensions:")
    for extension in missing:
        print(f"  {extension}")
    if not assume_yes:
        answer = input("Install missing extensions? [y/N] ").strip().casefold()
        if answer not in {"y", "yes"}:
            print("VS Code extension installation skipped.")
            return 0
    for extension in missing:
        install = subprocess.run(
            [code, "--install-extension", extension],
            check=False,
            text=True,
        )
        if install.returncode != 0:
            print(f"Failed to install {extension}.", file=sys.stderr)
            return 1
    print(f"Installed {len(missing)} VS Code extension(s).")
    return 0


def main() -> int:
    """Run the VS Code extension updater."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Install missing extensions without prompting.",
    )
    args = parser.parse_args()
    return update_extensions(assume_yes=bool(args.yes))


if __name__ == "__main__":
    raise SystemExit(main())
