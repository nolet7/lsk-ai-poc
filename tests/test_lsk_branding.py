"""Regression: LSK branding replaces legacy corporate references across text sources.

Generated SQLite/Chroma files and transient local checkouts are excluded.
"""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
LEGACY=("a"+"sr").casefold()
EXCLUDED={".git","external",".venv",".venv-lsk","venv","__pycache__",".run-lsk","chroma_db","outputs","results"}
TEXT={".py",".md",".json",".jsonl",".yml",".yaml",".txt",".html",".sh",".toml",".env",".example",".service",".gitignore"}
NAMES={"Dockerfile","README.md",".gitignore"}
OLD_BRANDS=("Dom"+"ino", "C"+"&"+"H")

class LSKBrandingTests(unittest.TestCase):
    def test_no_legacy_brand_in_source_or_paths(self):
        failures=[]
        for path in ROOT.rglob("*"):
            if any(p in EXCLUDED for p in path.relative_to(ROOT).parts) or not path.is_file():
                continue
            if path.suffix not in TEXT and path.name not in NAMES:
                continue
            rel=path.relative_to(ROOT).as_posix()
            source=path.read_text(encoding="utf-8",errors="replace")
            # Previous enterprise name, old internal module names or old product brands.
            old_word=re.compile(r"(?<![a-z])"+LEGACY+r"(?![a-z])",re.I)
            if old_word.search(rel) or old_word.search(source):
                failures.append(rel+": legacy corporate identifier")
            if any(brand in source for brand in OLD_BRANDS):
                failures.append(rel+": legacy real-world product name")
        self.assertEqual(failures,[], "Unexpected legacy branding references")
