"""conftest.py — pytest configuration for psgscoring within YASAFlaskified."""
import sys
from pathlib import Path

# Ensure myproject/ is on sys.path so psgscoring package resolves
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
