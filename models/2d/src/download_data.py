"""Download an immutable source revision and preserve its provenance."""
import hashlib
import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from common import ROOT, save_json

REPO = "kanakaero/Dataset-of-Aerodynamic-and-Geometric-Coefficients-of-Airfoils"

def fetch(url):
    with urlopen(Request(url, headers={"User-Agent": "BTP-airfoil-research"}), timeout=90) as response:
        return response.read()

def main():
    folder = ROOT / "data/raw"
    folder.mkdir(parents=True, exist_ok=True)
    manifest = folder / "source.json"
    if manifest.exists():
        meta = json.loads(manifest.read_text())
        path = folder / "airfoils.csv"
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == meta["sha256"]:
            print("Verified existing raw dataset; download skipped.")
            return
        raise ValueError("Existing raw dataset differs from manifest; preserve and investigate it.")
    revision = json.loads(fetch(f"https://api.github.com/repos/{REPO}/commits/main"))["sha"]
    base = f"https://raw.githubusercontent.com/{REPO}/{revision}"
    url = base + "/Final%20Results/COMPILED%20AIRFOIL%20DATA.csv"
    content = fetch(url)
    if not content.lstrip().startswith(b"Filename,"):
        raise ValueError("Unexpected CSV header; inspect before using.")
    (folder / "airfoils.csv").write_bytes(content)
    for name in ["LICENSE", "README.md"]:
        (folder / name).write_bytes(fetch(base + "/" + name))
    save_json(manifest, {"repository": f"https://github.com/{REPO}", "revision": revision,
        "url": url, "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content),
        "reynolds_number": 100000, "paper": "https://doi.org/10.3390/data9050064"})
    print(f"Downloaded {len(content):,} bytes at revision {revision}.")

if __name__ == "__main__":
    main()
