# tests/conftest.py
# Делает src и demo_processor импортируемыми для всех тестов.

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]  # .../repo/tests -> .../repo

# 1) src/ — как было
src_dir = repo_root / "src"
if src_dir.is_dir() and str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# 2) src/demo_processor — чтобы видеть swap.py как модуль "swap"
demo_proc_dir = src_dir / "demo_processor"
if demo_proc_dir.is_dir() and str(demo_proc_dir) not in sys.path:
    sys.path.insert(0, str(demo_proc_dir))
