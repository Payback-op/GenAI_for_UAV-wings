"""Generate a parametric 3D wing, separate from the preserved 2D predictor."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import pandas as pd
from common import ROOT, CST, save_json
from wing_geometry import build_mesh, write_stl, write_obj

def load_section(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    s = json.loads(path.read_text())
    coefficients = np.array([s["coefficients"][key] for key in CST], dtype=float)
    if not np.isfinite(coefficients).all():
        raise ValueError("Airfoil design has invalid coefficients.")
    return coefficients, {"design_file": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "coefficients": s["coefficients"], "original_section_conditions": s.get("conditions"),
        "original_section_predictions": s.get("predictions"),
        "meaning": "Original 2D design estimates only; these are not whole-wing or spanwise predictions"}

def draw_wing(ax, v, f):
    ax.clear()
    collection = Poly3DCollection(v[f], facecolors="#60a5fa", linewidth=0, shade=True)
    ax.add_collection3d(collection)
    low, high = v.min(axis=0), v.max(axis=0)
    centre = (low+high)/2
    extent = np.maximum(high-low, 0.03)
    for setter, i in [(ax.set_xlim, 0), (ax.set_ylim, 1), (ax.set_zlim, 2)]:
        setter(centre[i]-extent[i]*0.55, centre[i]+extent[i]*0.55)
    ax.set_box_aspect(extent, zoom=1.35)
    ax.set(xlabel="x aft (m)", ylabel="y span (m)", zlabel="z up (m)")
    ax.view_init(elev=30, azim=-125)
    ax.set_title("Generated full wing - geometry proposal", fontsize=13)
    ax.set_axis_off()
    rings = v.reshape(len(np.unique(v[:, 1])), -1, 3)
    for k in [0, rings.shape[1]//2]:
        edge = rings[:, k, :]
        ax.plot(edge[:, 0], edge[:, 1], edge[:, 2], color="#1e3a8a", linewidth=0.8)
    for j in [0, len(rings)//2, len(rings)-1]:
        edge = np.vstack([rings[j], rings[j, 0]])
        ax.plot(edge[:, 0], edge[:, 1], edge[:, 2], color="#1e3a8a", linewidth=0.6)

def generate_wing(c, *, output_folder=None, publish_latest=True):
    root, root_source = load_section(c["root_airfoil_design"])
    if c.get("tip_airfoil_design", "same_as_root") == "same_as_root":
        tip, tip_source = root.copy(), dict(root_source)
    else:
        tip, tip_source = load_section(c["tip_airfoil_design"])
    v, f, stations, dimensions, checks = build_mesh(c, root, tip)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    folder = Path(output_folder) if output_folder is not None else ROOT / "results/3d" / stamp
    folder.mkdir(parents=True)
    write_stl(folder / "wing_mm.stl", v, f)
    write_obj(folder / "wing_m.obj", v, f)
    np.savez_compressed(folder / "wing_mesh.npz", vertices_m=v, faces=f)
    pd.DataFrame(stations).to_csv(folder / "spanwise_geometry.csv", index=False)
    fig = plt.figure(figsize=(11, 7))
    ax = fig.add_subplot(111, projection="3d")
    draw_wing(ax, v, f)
    fig.text(0.5, 0.10, f"Span {c['span_m']:g} m | Root {c['root_chord_m']:g} m | Tip {c['tip_chord_m']:g} m | Reference area {dimensions['reference_planform_area_m2']:.3f} m²", ha="center", fontsize=11)
    fig.text(0.5, 0.055, "Parametric geometry. Complete-wing aerodynamics, strength and flight performance are unverified.", ha="center", fontsize=9, color="#9a3412")
    fig.subplots_adjust(bottom=0.18, top=0.9)
    fig.savefig(folder / "wing_preview.png", dpi=160)
    plt.close(fig)
    summary = {"version": "3d-geometry-v1", "generator_type": "Parametric symmetric tapered-wing loft; no new 3D ML training",
        "conditions": c, "dimensions": dimensions, "mesh_checks": checks, "root_section": root_source, "tip_section": tip_source,
        "output_folder": str(folder), "export_units": {"wing_mm.stl": "millimetres; STL does not encode units", "wing_m.obj": "metres by convention", "wing_mesh.npz": "metres"},
        "physical_requirements_verified": False, "complete_wing_aerodynamic_predictions": None,
        "limitations": ["No matched 3D aerodynamic or structural training labels", "2D source predictions do not account for span, sweep, twist, dihedral or varying local Reynolds number", "Closed envelope mesh only; no spars, ribs, shell thickness or material definition", "Mesh topology checked, not certified manufacturing or flight feasibility", "Generated source-normalized leading-edge endpoints use y=0", "Existing 2D label conflicts and weak drag prediction remain unresolved"]}
    save_json(folder / "wing_design.json", summary)
    if publish_latest:
        save_json(ROOT / "results/3d/latest.json", summary)
    return summary

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--conditions", type=Path, default=ROOT / "config/wing_conditions.json")
    args = parser.parse_args()
    try:
        result = generate_wing(json.loads(args.conditions.read_text()))
    except (ValueError, KeyError, FileNotFoundError) as error:
        parser.error(str(error))
    print(json.dumps({"output_folder": result["output_folder"], "dimensions": result["dimensions"], "mesh_checks": result["mesh_checks"]}, indent=2))

if __name__ == "__main__":
    main()
