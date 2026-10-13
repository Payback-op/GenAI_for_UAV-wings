"""Download the source's processed coordinates for reconstruction verification."""
import hashlib
import json
from common import ROOT, save_json
from download_data import REPO, fetch

def main():
    revision = json.loads((ROOT / "data/raw/source.json").read_text())["revision"]
    dest = ROOT / "data/reference/AIRFOILS.zip"
    url = f"https://raw.githubusercontent.com/{REPO}/{revision}/Processed%20Airfoil%20Data/AIRFOILS.zip"
    if not dest.exists():
        content = fetch(url)
        if not content.startswith(b"PK"):
            raise ValueError("Unexpected geometry archive.")
        dest.write_bytes(content)
    save_json(dest.with_suffix(".source.json"), {"revision": revision, "url": url, "sha256": hashlib.sha256(dest.read_bytes()).hexdigest()})
    print(f"Geometry reference archive ready: {dest.stat().st_size:,} bytes")

if __name__ == "__main__":
    main()
