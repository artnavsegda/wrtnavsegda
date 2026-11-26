#!/usr/bin/env python3
"""Запуск farm из любого каталога: python3 farm/main.py …"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from farm.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
