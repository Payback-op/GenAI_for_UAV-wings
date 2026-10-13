"""Integration checks for shared 2D/3D identity, exports and no-match handling."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import struct
import joblib
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from common import ROOT, CST, FEATURES, save_json
from generate_combined import generate_combined, validate_combined, draw_planform
from verify_wing import verify_saved_2d


def source_surfaces(weights, x):
    # Evaluate the source polynomial directly, independently of the loft code.
    basis = np.column_stack([(1-x)**3, 3*x*(1-x)**2, 3*x*x*(1-x), x**3])
    factor = np.sqrt(x)*(1-x)
    return factor*(basis @ weights[:4]), factor*(basis @ weights[4:])


def verify_run(summary):
    folder = Path(summary["output_folder"])
    section = json.loads((folder / "2d/design.json").read_text())
    wing = json.loads((folder / "3d/wing_design.json").read_text())
    conditions = summary["conditions"]
    assert summary["airfoil"] == section and summary["wing"] == wing
    assert section["conditions"] == conditions["airfoil"]
    digest = hashlib.sha256((folder / "2d/design.json").read_bytes()).hexdigest()
    for end in ["root_section", "tip_section"]:
        assert wing[end]["coefficients"] == section["coefficients"]
        assert wing[end]["sha256"] == digest
        assert Path(wing[end]["design_file"]) == folder / "2d/design.json"
    weights = np.array([section["coefficients"][key] for key in CST])
    coordinates = pd.read_csv(folder / "2d/coordinates.csv")
    lower, upper = source_surfaces(weights, coordinates.x_over_chord.to_numpy())
    np.testing.assert_allclose(coordinates.lower_y_over_chord, lower, atol=1e-12)
    np.testing.assert_allclose(coordinates.upper_y_over_chord, upper, atol=1e-12)
    with np.load(folder / "3d/wing_mesh.npz") as mesh:
        vertices, faces = mesh["vertices_m"], mesh["faces"]
    c = conditions["wing"]
    rings = vertices.reshape(c["span_stations"], -1, 3)
    n = c["chord_points"]
    x = (1-np.cos(np.linspace(0, np.pi, n)))/2
    lower, upper = source_surfaces(weights, x)
    expected_x = np.r_[x[::-1], x[1:-1]]
    expected_z = np.r_[upper[::-1], lower[1:-1]]
    stations = pd.read_csv(folder / "3d/spanwise_geometry.csv")
    for ring, station in zip(rings, stations.to_dict("records")):
        # Undo each section's translation, quarter-chord rotation and scaling.
        chord = station["chord_m"]
        theta = np.deg2rad(station["twist_deg"])
        dx = ring[:, 0]-station["leading_edge_datum_x_m"]-chord*0.25
        dz = ring[:, 2]-station["dihedral_datum_z_m"]
        normalized_x = (np.cos(theta)*dx-np.sin(theta)*dz)/chord+0.25
        normalized_z = (np.sin(theta)*dx+np.cos(theta)*dz)/chord
        np.testing.assert_allclose(normalized_x, expected_x, atol=1e-11)
        np.testing.assert_allclose(normalized_z, expected_z, atol=1e-11)
    np.testing.assert_allclose(np.ptp(vertices[:, 1]), c["span_m"], atol=1e-12)
    np.testing.assert_allclose(stations.iloc[len(stations)//2].chord_m, c["root_chord_m"])
    np.testing.assert_allclose(stations.iloc[[0, -1]].chord_m, c["tip_chord_m"])
    fig = Figure()
    ax = fig.add_subplot(111)
    draw_planform(ax, vertices)
    polygon = np.vstack([rings[:, n-1], rings[::-1, 0], rings[:1, n-1]])
    plotted = ax.patches[0].get_xy()
    np.testing.assert_allclose(plotted, polygon[:, [1, 0]], atol=1e-12)
    bundle = joblib.load(ROOT / "models/airfoil_baseline.joblib")
    inputs = pd.DataFrame([{**section["coefficients"], "AoA": conditions["airfoil"]["angle_of_attack_deg"]}])[FEATURES]
    predictions = {key: float(model.predict(inputs)[0]) for key, model in bundle["models"].items()}
    for key in ["Cl", "Cd"]:
        np.testing.assert_allclose(section["predictions"][key], predictions[key], rtol=1e-6)
    a = conditions["airfoil"]
    matched = abs(predictions["Cl"]-a["target_cl"]) <= a["cl_tolerance"] and predictions["Cd"] <= a["maximum_cd"]
    assert summary["status"] == section["status"] == ("predicted_match" if matched else "no_predicted_match")
    assert not summary["physical_requirements_verified"]
    assert wing["mesh_checks"]["closed_manifold"] and wing["mesh_checks"]["consistent_orientation"]
    payload = (folder / "3d/wing_mm.stl").read_bytes()
    count = struct.unpack_from("<I", payload, 80)[0]
    assert count == len(faces) and len(payload) == 84+50*count
    dtype = np.dtype([("normal", "<f4", (3,)), ("points", "<f4", (3, 3)), ("attr", "<u2")])
    records = np.frombuffer(payload, dtype=dtype, offset=84)
    np.testing.assert_allclose(records["points"], vertices[faces]*1000, rtol=1e-6, atol=2e-4)
    lines = (folder / "3d/wing_m.obj").read_text().splitlines()
    obj_vertices = np.array([[float(v) for v in line.split()[1:]] for line in lines if line.startswith("v ")])
    obj_faces = np.array([[int(v)-1 for v in line.split()[1:]] for line in lines if line.startswith("f ")])
    np.testing.assert_allclose(obj_vertices, vertices, atol=1e-9)
    np.testing.assert_array_equal(obj_faces, faces)
    for name in ["combined_preview.png", "2d/airfoil.png", "3d/wing_preview.png"]:
        assert (folder / name).stat().st_size > 1000
    return {"folder": str(folder), "status": summary["status"], "matching_span_stations": len(rings)}


def main():
    preserved = verify_saved_2d()
    originals = {path: (ROOT / path).read_bytes() for path in ["results/generated/latest.json", "results/3d/latest.json", "config/design_conditions.json", "config/wing_conditions.json", "models/airfoil_baseline.joblib"]}
    latest = ROOT / "results/2&3/latest.json"
    original_latest = latest.read_bytes()
    original = json.loads(original_latest)
    runs = [verify_run(original)]
    c = deepcopy(original["conditions"])
    c["airfoil"].update(target_cl=99, candidate_count=500)
    c["wing"].update(span_m=2.4, root_chord_m=0.4, tip_chord_m=0.2, root_twist_deg=6., tip_twist_deg=-8., leading_edge_sweep_deg=-5., dihedral_deg=10., chord_points=31, span_stations=7)
    try:
        no_match = generate_combined(c)
        assert no_match["status"] == "no_predicted_match"
        runs.append(verify_run(no_match))
    finally:
        latest.write_bytes(original_latest)
    for key, value in [("span_m", -1), ("tip_chord_m", 1.), ("span_stations", 40), ("root_airfoil_design", "old-design.json")]:
        invalid = deepcopy(original["conditions"])
        invalid["wing"][key] = value
        try:
            validate_combined(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid or external wing input accepted: {key}")
    for path, content in originals.items():
        assert (ROOT / path).read_bytes() == content, f"Standalone artifact changed: {path}"
    assert verify_saved_2d() == preserved
    result = {"passed": True, "name": "2&3", "runs": runs, "saved_2d_files_unchanged": preserved,
        "checks": ["Exact newly generated section source at both wing ends", "Independent source polynomial evaluation of 2D coordinates", "Every span station recovered to the same normalized 2D shape after inverse twist/scaling", "Input span/root/tip dimensions", "2D top-view edges agree with actual 3D mesh", "Independent saved-model predictions and match/no-match status", "Closed oriented mesh", "STL millimetre and OBJ metre export round trips", "Invalid inputs and stale external design references rejected", "Original standalone configs/latest results/predictor and 2D snapshot unchanged"],
        "scope": "Software and geometry integration checks; no physical performance validation"}
    save_json(ROOT / "results/2&3/verification.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
