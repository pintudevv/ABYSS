import os
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
EXT_DIR = BASE_DIR / "extension"
DIST_DIR = BASE_DIR / "dist"

DIST_DIR.mkdir(exist_ok=True)
zip_path = DIST_DIR / "abyss_extension_v1.1.zip"

print(f"[+] Packaging Chrome Web Store release artifact: {zip_path}")

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(EXT_DIR):
        for file in files:
            full_path = Path(root) / file
            rel_path = full_path.relative_to(EXT_DIR)
            z.write(full_path, rel_path)
            print(f"   + Added: {rel_path}")

print(f"\n[OK] SUCCESS: Chrome & Edge Web Store release package created at:\n{zip_path} ({zip_path.stat().st_size} bytes)")
