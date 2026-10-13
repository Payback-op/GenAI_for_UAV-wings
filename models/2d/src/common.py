from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
CST = [f"CST Coeff {i}" for i in range(1, 9)]
FEATURES = CST + ["AoA"]
TARGETS = ["Cl", "Cd"]
SEED = 42

def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
