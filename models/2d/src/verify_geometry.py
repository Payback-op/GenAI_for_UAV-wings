"""Cross-check CST reconstruction against source coordinate/weight pairs."""
import io
import json
from zipfile import ZipFile
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from common import ROOT, CST, save_json
from geometry import surfaces, geometry_checks

def main():
    data = pd.read_csv(ROOT / "data/processed/airfoils.csv")
    tree = cKDTree(data[CST].drop_duplicates().to_numpy())
    results = []
    with ZipFile(ROOT / "data/reference/AIRFOILS.zip") as archive:
        names = set(archive.namelist())
        # Deterministic spread through the archive; do not select by fit quality.
        coeff_names = sorted(n for n in names if n.endswith("_Coeffs.txt"))
        selected = [coeff_names[i] for i in np.linspace(0, len(coeff_names)-1, 30, dtype=int)]
        for name in selected:
            dat_name = name.replace("_Coeffs.txt", ".dat")
            if dat_name not in names:
                raise ValueError(f"Missing reference coordinates for {name}")
            weights = np.loadtxt(io.BytesIO(archive.read(name))).reshape(-1)
            points = np.loadtxt(io.BytesIO(archive.read(dat_name)))
            x, lower, upper = surfaces(weights, points[:, 0])
            error = np.minimum(np.abs(points[:, 1]-lower), np.abs(points[:, 1]-upper))
            interior = (points[:, 0] > 0) & (points[:, 0] < 1)
            nearest, _ = tree.query(weights)
            results.append({"reference": dat_name, "points": len(points), "maximum_surface_error": float(error.max()),
                "maximum_interior_error": float(error[interior].max()),
                "source_endpoint_offset": float(np.abs(points[~interior, 1]).max()),
                "rms_surface_error": float(np.sqrt(np.mean(error**2))), "nearest_dataset_coefficient_distance": float(nearest)})
    # Source code anchors x=0 to A(ind,2), absent from the eight coefficients.
    # Check all interior samples strictly, report that endpoint difference explicitly.
    passed = all(r["maximum_interior_error"] < 1e-5 and r["nearest_dataset_coefficient_distance"] < 1e-6 for r in results)
    result = {"passed": passed, "checked_reference_airfoils": len(results), "tolerance": 1e-5,
        "convention": "lower four then upper four; cubic Bernstein; class x^0.5*(1-x); zero trailing-edge thickness",
        "endpoint_policy": "Generated normalized shapes close at y=0. Source anchors x=0 to A(ind,2), not encoded in CSV; endpoint offsets are reported separately, not treated as reconstruction agreement.",
        "scope": "Processed source reconstruction only, not aerodynamic or original-shape fitting validation", "references": results}
    save_json(ROOT / "results/geometry_reference_check.json", result)
    print(json.dumps(result, indent=2))
    if not passed:
        raise ValueError("Source geometry reconstruction check failed; inspect reference report.")
    valid, _, _ = geometry_checks(np.array([[-.1]*4 + [.1]*4]), .01, .4)
    assert valid[0]
    inverted, _, _ = geometry_checks(np.array([[.1]*4 + [-.1]*4]), .01, .4)
    assert not inverted[0]

if __name__ == "__main__":
    main()
