"""Regenerate package integrity manifest after a reviewed release change."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
files = [path for path in root.rglob("*") if path.is_file()
         and not any(part in (".git", "__pycache__", ".downloads") for part in path.relative_to(root).parts)
         and path.name != "SHA256SUMS.json" and path.suffix != ".pyc"]
sums = {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(files)}
(root / "SHA256SUMS.json").write_text(json.dumps(sums, indent=2) + "\n", encoding="utf-8")
print(f"Checksummed {len(files)} files")
