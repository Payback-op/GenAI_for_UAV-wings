"""Check preserved 2D files, wing geometry, topology and exported units."""
import hashlib
import json
from pathlib import Path
import struct
import numpy as np
from common import ROOT, save_json
from generate_wing import load_section
from geometry import surfaces
from wing_geometry import build_mesh, validate_wing

def verify_saved_2d():
    folder = ROOT / "models/2d"
    manifest = json.loads((folder / "snapshot_manifest.json").read_text())
    for name, checksum in manifest["files"].items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == checksum, f"Saved 2D file changed: {name}"
    return len(manifest["files"])

def main():
    preserved = verify_saved_2d()
    c = json.loads((ROOT / "config/wing_conditions.json").read_text())
    w, _ = load_section(c["root_airfoil_design"])
    plain = dict(c, root_twist_deg=0., tip_twist_deg=0., leading_edge_sweep_deg=0., dihedral_deg=0.)
    v, f, stations, d, checks = build_mesh(plain, w, w)
    x, lower, upper = surfaces(w, __import__("geometry").chord_grid(c["chord_points"]))
    section_area = np.trapezoid(upper-lower, x)
    cr, ct, b = c["root_chord_m"], c["tip_chord_m"], c["span_m"]
    expected_volume = section_area*b*(cr*cr+cr*ct+ct*ct)/3
    np.testing.assert_allclose(checks["signed_volume_m3"], expected_volume, rtol=1e-9)
    np.testing.assert_allclose(d["reference_planform_area_m2"], b*(cr+ct)/2)
    np.testing.assert_allclose(d["reference_aspect_ratio"], b*b/d["reference_planform_area_m2"])
    rectangular = dict(plain, tip_chord_m=cr)
    _, _, _, _, rect_checks = build_mesh(rectangular, w, w)
    np.testing.assert_allclose(rect_checks["signed_volume_m3"], section_area*b*cr*cr, rtol=1e-9)
    for params, tip in [(c, w), (dict(c, leading_edge_sweep_deg=-20., dihedral_deg=-10.), w),
        (c, w*np.array([1, 1, 1, 1, 1.05, 1.05, 1.05, 1.05]))]:
        vertices, faces, _, _, q = build_mesh(params, w, tip)
        assert q["closed_manifold"] and q["consistent_orientation"] and q["degenerate_faces"] == 0
        assert q["finite_vertices"] and q["signed_volume_m3"] > 0
        rings = vertices.reshape(params["span_stations"], -1, 3)
        np.testing.assert_allclose(rings[:, :, [0, 2]], rings[::-1, :, [0, 2]], atol=1e-10)
        np.testing.assert_allclose(rings[:, :, 1], -rings[::-1, :, 1], atol=1e-10)
    for key, value in [("span_m", -1), ("root_chord_m", float("nan")), ("tip_chord_m", cr+1), ("span_stations", 40)]:
        try:
            validate_wing(dict(c, **{key: value}))
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid {key} accepted")
    s = json.loads((ROOT / "results/3d/latest.json").read_text())
    folder = Path(s["output_folder"])
    with np.load(folder / "wing_mesh.npz") as mesh:
        vertices, faces = mesh["vertices_m"], mesh["faces"]
    payload = (folder / "wing_mm.stl").read_bytes()
    count = struct.unpack_from("<I", payload, 80)[0]
    assert count == len(faces) and len(payload) == 84+50*count
    records = np.frombuffer(payload, dtype=np.dtype([("normal", "<f4", (3,)), ("points", "<f4", (3, 3)), ("attr", "<u2")]), offset=84)
    np.testing.assert_allclose(records["points"], vertices[faces]*1000, rtol=1e-6, atol=2e-4)
    assert np.isfinite(records["points"]).all()
    obj_lines = (folder / "wing_m.obj").read_text().splitlines()
    obj_v = np.array([[float(t) for t in line.split()[1:]] for line in obj_lines if line.startswith("v ")])
    obj_f = np.array([[int(t)-1 for t in line.split()[1:]] for line in obj_lines if line.startswith("f ")])
    np.testing.assert_allclose(obj_v, vertices, atol=1e-9)
    np.testing.assert_array_equal(obj_f, faces)
    result = {"passed": True, "saved_2d_files_unchanged": preserved,
        "checks": ["Analytical untwisted tapered/rectangular volume", "Reference area and aspect ratio", "Mirrored sections", "Closed and oriented meshes for sweep/dihedral/different tip sections", "Invalid dimensions rejected", "Binary STL count and millimetre scale", "OBJ metre coordinates and face round trip"],
        "scope": "Geometry/software/export checks only; no aerodynamic or structural validation"}
    save_json(ROOT / "results/3d/verification.json", result)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
