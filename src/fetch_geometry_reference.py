"""Preserve authors' CST implementation and file listing at the data revision."""
import json
from urllib.parse import quote
from common import ROOT, save_json
from download_data import fetch, REPO

def main():
    revision = json.loads((ROOT / "data/raw/source.json").read_text())["revision"]
    folder = ROOT / "data/reference"
    folder.mkdir(parents=True, exist_ok=True)
    base = f"https://raw.githubusercontent.com/{REPO}/{revision}"
    for name in ["CST.m", "CST_airfoil_fit.m", "CST_auto.m", "airfoilfit.m", "README.md"]:
        (folder / name).write_bytes(fetch(base + "/CST/" + name))
    tree = json.loads(fetch(f"https://api.github.com/repos/{REPO}/git/trees/{revision}?recursive=1"))
    save_json(folder / "tree.json", tree)
    print("Downloaded source CST reference.")
    files = [entry["path"] for entry in tree["tree"] if entry["path"].startswith("Processed Airfoil Data/")]
    print("Processed geometry files:", files[:15])

if __name__ == "__main__":
    main()
