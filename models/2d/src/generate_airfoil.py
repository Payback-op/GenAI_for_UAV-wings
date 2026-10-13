"""Conditional geometry search, using the exploratory aerodynamic predictor.

This proposes new geometry and renders it; it is not a trained image generator
or evidence of physical compliance. Search output may report no predicted match.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from common import ROOT, CST, FEATURES, save_json
from geometry import surfaces, geometry_checks

def validate(c):
    fields = ["angle_of_attack_deg", "target_cl", "cl_tolerance", "maximum_cd", "minimum_thickness_ratio", "maximum_thickness_ratio", "reynolds_number", "candidate_count", "random_seed"]
    for key in fields:
        if key not in c or isinstance(c[key], bool) or not isinstance(c[key], (int, float)) or not np.isfinite(c[key]):
            raise ValueError(f"{key} must be a finite number.")
    if c["reynolds_number"] != 100000:
        raise ValueError("Only Reynolds number 100000 is supported by the current predictor.")
    if not -4 <= c["angle_of_attack_deg"] <= 8:
        raise ValueError("Angle of attack must be between -4 and 8 degrees.")
    if c["cl_tolerance"] <= 0 or c["maximum_cd"] <= 0:
        raise ValueError("Lift tolerance and drag limit must be positive.")
    if not 0.01 <= c["minimum_thickness_ratio"] < c["maximum_thickness_ratio"] <= 0.4:
        raise ValueError("Thickness ratios must satisfy 0.01 <= minimum < maximum <= 0.4.")
    if int(c["candidate_count"]) != c["candidate_count"] or not 100 <= c["candidate_count"] <= 50000:
        raise ValueError("Candidate count must be an integer between 100 and 50000.")
    if int(c["random_seed"]) != c["random_seed"] or not 0 <= c["random_seed"] < 2**32:
        raise ValueError("Random seed must be an integer between 0 and 2^32-1.")

def score(models, w, aoa):
    x = pd.DataFrame(w, columns=CST)
    x["AoA"] = aoa
    return models["Cl"].predict(x[FEATURES]), models["Cd"].predict(x[FEATURES])

def generate(c):
    validate(c)
    verification = ROOT / "results/geometry_reference_check.json"
    if not verification.exists() or not json.loads(verification.read_text())["passed"]:
        raise ValueError("Source coordinate reconstruction must pass verification first. Run src/verify_geometry.py.")
    artifact = ROOT / "models/airfoil_baseline.joblib"
    bundle = joblib.load(artifact)
    bounds = np.array([bundle["metadata"]["training_bounds"][key] for key in CST])
    data = pd.read_csv(ROOT / "data/processed/airfoils.csv")
    source = data[data.split == "train"].drop_duplicates(CST).reset_index(drop=True)
    weights = source[CST].to_numpy()
    valid, _, _ = geometry_checks(weights, c["minimum_thickness_ratio"], c["maximum_thickness_ratio"])
    eligible = source[valid].reset_index(drop=True)
    if len(eligible) < 2:
        raise ValueError("Too few training shapes meet the geometry limits. Adjust the thickness range.")
    seed_w = eligible[CST].to_numpy()
    cl, cd = score(bundle["models"], seed_w, c["angle_of_attack_deg"])
    objective = np.abs(cl-c["target_cl"])/c["cl_tolerance"] + 10*np.maximum(cd/c["maximum_cd"]-1, 0)
    best = np.argsort(objective)[:min(128, len(eligible))]
    rng = np.random.default_rng(int(c["random_seed"]))
    n = int(c["candidate_count"])
    parents = rng.choice(best, n)
    # Local search, not arbitrary extrapolation over the full coefficient box.
    mutations = rng.normal(0, 0.003, (n, 8))
    w = seed_w[parents] + mutations
    _, neighbours = cKDTree(seed_w).query(seed_w, k=2)
    mix = np.arange(n) % 2 == 0
    other = seed_w[neighbours[parents[mix], 1]]
    blend = rng.uniform(0.05, 0.3, (mix.sum(), 1))
    w[mix] = (1-blend)*seed_w[parents[mix]] + blend*other + 0.5*mutations[mix]
    valid, thickness, camber = geometry_checks(w, c["minimum_thickness_ratio"], c["maximum_thickness_ratio"])
    valid &= ((w >= bounds[:, 0]) & (w <= bounds[:, 1])).all(axis=1)
    distance, nearest = cKDTree(weights).query(w)
    # Novel but local to the training representation; not a confidence estimate.
    valid &= (distance > 1e-4) & (distance <= 0.02)
    count_valid = int(valid.sum())
    if count_valid == 0:
        raise ValueError("No valid novel local candidates found; adjust geometry limits or search seed.")
    w, thickness, camber, distance, nearest = w[valid], thickness[valid], camber[valid], distance[valid], nearest[valid]
    cl, cd = score(bundle["models"], w, c["angle_of_attack_deg"])
    finite = np.isfinite(cl) & np.isfinite(cd) & (cd > 0)
    w, thickness, camber, distance, nearest, cl, cd = [a[finite] for a in [w, thickness, camber, distance, nearest, cl, cd]]
    if not len(w):
        raise ValueError("No finite, positive-drag predictions returned.")
    error = np.abs(cl-c["target_cl"])
    match = (error <= c["cl_tolerance"]) & (cd <= c["maximum_cd"])
    objective = error/c["cl_tolerance"] + 10*np.maximum(cd/c["maximum_cd"]-1, 0)
    matched = np.where(match)[0]
    order = matched[np.lexsort((error[matched], cd[matched]))] if len(matched) else np.argsort(objective)
    idx = int(order[0])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    folder = ROOT / "results/generated" / stamp
    folder.mkdir(parents=True)
    table = pd.DataFrame(w[order[:20]], columns=CST)
    table["predicted_cl"] = cl[order[:20]]
    table["predicted_cd"] = cd[order[:20]]
    table["thickness_ratio"] = thickness[order[:20]]
    table["nearest_training_distance"] = distance[order[:20]]
    table["meets_predictor_targets"] = match[order[:20]]
    table.to_csv(folder / "ranked_candidates.csv", index=False)
    x, lower, upper = surfaces(w[idx])
    coordinates = np.column_stack([np.r_[x[::-1], x[1:]], np.r_[upper[::-1], lower[1:]]])
    np.savetxt(folder / "airfoil.dat", coordinates, header="BTP generated candidate; normalized chord; exploratory", comments="", fmt="%.10f")
    pd.DataFrame({"x_over_chord": x, "lower_y_over_chord": lower, "upper_y_over_chord": upper}).to_csv(folder / "coordinates.csv", index=False)
    status = "predicted_match" if match[idx] else "no_predicted_match"
    summary = {"status": status, "conditions": c, "coefficient_convention": "First four lower, last four upper; cubic Bernstein; C=x^0.5*(1-x); dz=0; closed endpoints",
        "coefficients": {key: float(v) for key, v in zip(CST, w[idx])},
        "predictions": {"Cl": float(cl[idx]), "Cd": float(cd[idx])},
        "checks": {"cl_within_tolerance": bool(error[idx] <= c["cl_tolerance"]), "cd_within_limit": bool(cd[idx] <= c["maximum_cd"]),
            "thickness_within_limits": True, "nonintersecting_sampled_surfaces": True, "training_feature_bounds": True},
        "maximum_thickness_ratio": float(thickness[idx]), "maximum_absolute_camber_ratio": float(camber[idx]),
        "nearest_training_coefficient_distance": float(distance[idx]), "nearest_training_filename": str(source.iloc[nearest[idx]].Filename),
        "candidate_count": n, "valid_novel_local_candidates": count_valid, "predicted_matching_candidates": len(matched),
        "model_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "source_revision": bundle["metadata"]["source_revision"], "output_folder": str(folder),
        "method": "Bounded local CST mutations and interpolation; predictor-guided candidate search, not a learned conditional image generator",
        "physical_requirements_verified": False,
        "limitations": ["Provisional simulation-label predictions; weak drag model and conflicting source labels", "Source leading-edge anchors are not encoded in CSV; generated normalized endpoints use y=0", "No CFD or experimental check of this generated shape", "Training proximity is a screening heuristic, not uncertainty or aerodynamic validation", "Thickness is normalized chord ratio, not structural strength", "2D airfoil only; no wing/aircraft load, material, mass or flight guarantee"]}
    save_json(folder / "design.json", summary)
    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor("#f8fafc")
    ax.fill_between(x, lower, upper, color="#bfdbfe", alpha=0.8)
    ax.plot(x, upper, color="#1d4ed8", linewidth=2)
    ax.plot(x, lower, color="#1d4ed8", linewidth=2)
    ax.plot(x, (upper+lower)/2, "--", color="#64748b", linewidth=1, label="Camber line")
    ax.set_aspect("equal", adjustable="box")
    ax.set(xlim=(-0.03, 1.03), xlabel="x / chord", ylabel="y / chord")
    ax.grid(alpha=0.2)
    ax.legend(loc="upper right", fontsize=9)
    title = "Generated airfoil - meets predictor targets" if match[idx] else "No predicted match - closest candidate shown"
    fig.suptitle(title, fontsize=16, color="#1d4ed8" if match[idx] else "#b91c1c", y=0.96)
    fig.text(0.5, 0.86, f"AoA {c['angle_of_attack_deg']:g} deg | Re 100,000 | Target Cl {c['target_cl']:g} +/- {c['cl_tolerance']:g} | Cd limit {c['maximum_cd']:g}", ha="center", fontsize=10)
    fig.text(0.5, 0.16, f"Predicted Cl {cl[idx]:.4f} | Predicted Cd {cd[idx]:.5f} | Max thickness {100*thickness[idx]:.1f}% chord", ha="center", fontsize=11)
    fig.text(0.5, 0.065, "Exploratory geometry proposal. Predictor targets only; physical performance is unverified.", ha="center", color="#9a3412", fontsize=10)
    fig.subplots_adjust(left=0.08, right=0.97, bottom=0.27, top=0.78)
    fig.savefig(folder / "airfoil.png", dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)
    save_json(ROOT / "results/generated/latest.json", summary)
    return summary

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--conditions", type=Path, default=ROOT / "config/design_conditions.json")
    args = parser.parse_args()
    try:
        summary = generate(json.loads(args.conditions.read_text()))
    except (ValueError, KeyError) as exc:
        parser.error(str(exc))
    print(json.dumps({"status": summary["status"], "predictions": summary["predictions"], "matching_candidates": summary["predicted_matching_candidates"], "image": str(Path(summary["output_folder"]) / "airfoil.png")}, indent=2))

if __name__ == "__main__":
    main()
