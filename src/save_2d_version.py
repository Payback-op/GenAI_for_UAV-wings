"""Preserve the current 2D implementation without moving or changing it."""
import hashlib
import json
import shutil
from datetime import datetime, timezone
from common import ROOT, save_json

def main():
    dest = ROOT / "models/2d"
    if dest.exists():
        raise ValueError("The saved 2D version already exists; it will not be overwritten.")
    dest.mkdir(parents=True)
    paths = ["src/common.py", "src/geometry.py", "src/generate_airfoil.py", "src/design_app.py",
        "src/predict.py", "src/train.py", "src/prepare_data.py", "src/download_data.py",
        "src/verify.py", "src/verify_geometry.py", "src/verify_generator.py",
        "models/airfoil_baseline.joblib", "models/model_card.json", "config/design_conditions.json",
        "data/raw/airfoils.csv", "data/raw/source.json", "data/raw/LICENSE", "data/raw/README.md",
        "data/processed/airfoils.csv", "data/processed/schema.json", "data/processed/example_inputs.csv",
        "data/splits/membership.csv", "results/data_audit.json", "results/test_metrics.csv",
        "results/validation_metrics.csv", "results/geometry_reference_check.json",
        "results/generator_verification.json", "results/verification.json", "results/FIRST_MODEL_REPORT.md",
        "docs/AIRFOIL_GENERATOR.md", "requirements.lock.txt", "PROJECT_CONTEXT.md"]
    for rel in paths:
        source = ROOT / rel
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for rel in ["results/plots", "data/reference"]:
        shutil.copytree(ROOT / rel, dest / rel)
    latest = json.loads((ROOT / "results/generated/latest.json").read_text())
    source_output = ROOT / "results/generated" / __import__("pathlib").Path(latest["output_folder"]).name
    saved_output = dest / "results/generated" / source_output.name
    shutil.copytree(source_output, saved_output)
    latest["output_folder"] = str(saved_output)
    save_json(dest / "results/generated/latest.json", latest)
    (dest / "README.md").write_text(
        "# Saved 2D model and generator\n\nFrozen version captured on 8 October 2026. "
        "Original working files remain in C:\\BTP.\n\n"
        "Run the saved generator from C:\\BTP:\n\n"
        "```powershell\n.\\.venv\\Scripts\\python.exe models\\2d\\src\\design_app.py\n```\n\n"
        "This snapshot has its own code, model, inputs, data and results. Running it writes new outputs inside the snapshot; "
        "the manifest records the initially preserved files. The trained model and source are not changed by generating designs. "
        "The project Python environment is shared.\n\n"
        "Predictor-target matches are provisional. Source-label conflicts and weak drag performance remain unresolved.\n",
        encoding="utf-8")
    files = {str(p.relative_to(dest)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(dest.rglob("*")) if p.is_file()}
    save_json(dest / "snapshot_manifest.json", {"saved_utc": datetime.now(timezone.utc).isoformat(),
        "version": "2d-v1", "files": files, "purpose": "Preserve existing 2D predictor and geometry/image generator before adding 3D"})
    print(f"Saved and hashed {len(files)} files in {dest}")

if __name__ == "__main__":
    main()
