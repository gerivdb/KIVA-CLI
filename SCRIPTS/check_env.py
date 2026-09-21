#!/usr/bin/env python3
"""Check environment variables for KIVA-CLI."""
from __future__ import annotations

import os


def main() -> None:
    output_dir = os.environ.get("OUTPUT_DIR", "")
    intents_path = os.environ.get("INTENTS_PATH", "")
    print(f"OUTPUT_DIR: {output_dir}")
    print(f"INTENTS_PATH: {intents_path}")


if __name__ == "__main__":
    main()
