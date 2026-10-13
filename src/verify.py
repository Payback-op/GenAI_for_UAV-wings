"""Check leakage boundaries and saved-model predictions against test outputs."""
import json
import subprocess
import sys
import joblib
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from common import ROOT, CST, FEATURES, TARGETS

def main():
    df = pd.read_csv(ROOT / "data/processed/airfoils.csv")
    assert df.groupby("Filename").split.nunique().max() == 1
    assert df.groupby(CST).split.nunique().max() == 1
    shapes = df[CST + ["split"]].drop_duplicates(CST).reset_index(drop=True)
    audit = json.loads((ROOT / "results/data_audit.json").read_text())
    for i, j in cKDTree(shapes[CST].to_numpy()).query_pairs(audit["coefficient_distance_tolerance"]):
        assert shapes.iloc[i].split == shapes.iloc[j].split
    bundle = joblib.load(ROOT / "models/airfoil_baseline.joblib")
    test = pd.read_csv(ROOT / "results/test_predictions.csv")
    for target in TARGETS:
        pred = bundle["models"][target].predict(test[FEATURES])
        np.testing.assert_allclose(pred, test[target + "_predicted"], rtol=1e-6, atol=1e-8)
        assert np.isfinite(pred).all()
    sample = df[df.split == "test"].head(5)[FEATURES]
    sample.to_csv(ROOT / "data/processed/example_inputs.csv", index=False)
    run = subprocess.run([sys.executable, str(ROOT / "src/predict.py"), str(ROOT / "data/processed/example_inputs.csv"), "--output", str(ROOT / "results/example_predictions.csv")], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    example = pd.read_csv(ROOT / "results/example_predictions.csv")
    for target in TARGETS:
        np.testing.assert_allclose(example[target + "_predicted"], bundle["models"][target].predict(sample), rtol=1e-6)
    rejected = subprocess.run([sys.executable, str(ROOT / "src/predict.py"), str(ROOT / "data/processed/example_inputs.csv"), "--reynolds", "200000"], capture_output=True, text=True)
    assert rejected.returncode != 0 and "100000 only" in rejected.stderr
    result = {"passed": True, "checks": ["Filename disjointness", "Exact/near-coefficient disjointness", "Saved artifact reproduces test predictions", "CLI inference matches saved artifact", "Unsupported Reynolds number rejected"]}
    (ROOT / "results/verification.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
