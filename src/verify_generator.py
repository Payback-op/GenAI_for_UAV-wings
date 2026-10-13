"""Verify exported design, target matching and explicit no-match behavior."""
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from common import ROOT, CST, FEATURES, save_json
from generate_airfoil import generate, validate

def main():
    latest = ROOT / "results/generated/latest.json"
    original = latest.read_text()
    s = json.loads(original)
    folder = Path(s["output_folder"])
    p = pd.read_csv(folder / "coordinates.csv")
    assert (p.upper_y_over_chord.iloc[1:-1] > p.lower_y_over_chord.iloc[1:-1]).all()
    assert np.allclose(p.iloc[[0, -1]][["lower_y_over_chord", "upper_y_over_chord"]], 0)
    thickness = (p.upper_y_over_chord-p.lower_y_over_chord).max()
    np.testing.assert_allclose(thickness, s["maximum_thickness_ratio"], atol=1e-9)
    c = s["conditions"]
    assert c["minimum_thickness_ratio"] <= thickness <= c["maximum_thickness_ratio"]
    w = [s["coefficients"][key] for key in CST]
    inputs = pd.DataFrame([w + [c["angle_of_attack_deg"]]], columns=FEATURES)
    models = joblib.load(ROOT / "models/airfoil_baseline.joblib")["models"]
    cl, cd = float(models["Cl"].predict(inputs)[0]), float(models["Cd"].predict(inputs)[0])
    np.testing.assert_allclose([cl, cd], [s["predictions"]["Cl"], s["predictions"]["Cd"]])
    matches = abs(cl-c["target_cl"]) <= c["cl_tolerance"] and cd <= c["maximum_cd"]
    assert (s["status"] == "predicted_match") == matches
    assert s["nearest_training_coefficient_distance"] > 1e-4
    coords = np.loadtxt(folder / "airfoil.dat", skiprows=1)
    assert coords.shape == (601, 2) and np.allclose(coords[0], coords[-1])
    assert np.isfinite(coords).all()
    for key, bad in [("reynolds_number", 200000), ("angle_of_attack_deg", 20), ("target_cl", float("nan"))]:
        try:
            validate(dict(c, **{key: bad}))
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid {key} was accepted")
    # Deliberately impossible target must never receive a successful status.
    try:
        impossible = generate(dict(c, target_cl=99.0, candidate_count=500))
        assert impossible["status"] == "no_predicted_match"
        assert impossible["predicted_matching_candidates"] == 0
    finally:
        latest.write_text(original)
    save_json(ROOT / "results/generator_verification.json", {"passed": True,
        "checks": ["Exported surfaces nonintersecting and closed", "Thickness equals exported coordinates", "Saved model independently reproduces candidate predictions", "Match status agrees with targets", "Candidate differs from training coefficients", "Unsupported conditions rejected", "Impossible target returns no-match"],
        "matched_design_folder": str(folder), "no_match_design_folder": impossible["output_folder"]})
    print("Generator verification passed, including an impossible-target no-match case.")

if __name__ == "__main__":
    main()
