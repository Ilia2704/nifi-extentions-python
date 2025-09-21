# tests/conftest.py
# Делает src импортируемым для всех тестов (юнитов).
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]  # .../repo/tests -> .../repo
src_dir = repo_root / "src"
if str(src_dir) not in sys.path and src_dir.is_dir():
    sys.path.insert(0, str(src_dir))
