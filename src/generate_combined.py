"""2&3: one airfoil search feeding synchronized 2D/3D geometry views."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from common import ROOT, CST, save_json
from generate_airfoil import generate, validate
from generate_wing import generate_wing, draw_wing
from wing_geometry import validate_wing
from geometry import surfaces

def validate_combined(c):
    if not isinstance(c, dict) or not isinstance(c.get("airfoil"), dict) or not isinstance(c.get("wing"), dict):
        raise ValueError("Combined conditions need airfoil and wing sections.")
    validate(c["airfoil"])
    validate_wing(c["wing"])
    if "root_airfoil_design" in c["wing"] or "tip_airfoil_design" in c["wing"]:
        raise ValueError("2&3 always uses its own newly generated airfoil. Remove external root/tip design fields.")

def draw_section(ax, airfoil):
    ax.clear()
    weights = [airfoil["coefficients"][key] for key in CST]
    x, lower, upper = surfaces(weights)
    ax.fill_between(x, lower, upper, color="#bfdbfe")
    ax.plot(x, upper, color="#1d4ed8", linewidth=1.7)
    ax.plot(x, lower, color="#1d4ed8", linewidth=1.7)
    ax.plot(x, (lower+upper)/2, "--", color="#64748b", linewidth=0.8)
    ax.set_aspect("equal", adjustable="box")
    ax.set(xlim=(-0.02, 1.02), xlabel="x / chord", ylabel="z / chord", title="2D airfoil cross-section (before twist)")
    ax.tick_params(labelsize=8)
    ax.grid(alpha=0.18)

def draw_planform(ax, v):
    """Project the actual mesh LE/TE into the x-y plane, including twist."""
    ax.clear()
    ring = v.reshape(len(np.unique(v[:, 1])), -1, 3)
    leading = ring[:, ring.shape[1]//2]
    trailing = ring[:, 0]
    polygon = np.vstack([leading, trailing[::-1], leading[:1]])
    ax.fill(polygon[:, 1], polygon[:, 0], color="#bfdbfe", edgecolor="#1d4ed8", linewidth=1.5)
    centre = len(ring)//2
    ax.plot([leading[centre, 1], trailing[centre, 1]], [leading[centre, 0], trailing[centre, 0]], "--", color="#64748b", linewidth=0.8)
    ax.set_aspect("equal", adjustable="box")
    ax.set(xlabel="Spanwise y (m)", ylabel="Chordwise x (m)", title="2D wing top view (mesh edge projection)")
    ax.invert_yaxis()
    ax.tick_params(labelsize=8)
    ax.grid(alpha=0.18)

def generate_combined(c, *, progress=None):
    validate_combined(c)
    notify = progress or (lambda message: None)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    folder = ROOT / "results/2&3" / stamp
    folder.mkdir(parents=True)
    notify("Generating the airfoil from your section targets...")
    airfoil = generate(dict(c["airfoil"]), output_folder=folder / "2d", publish_latest=False)
    exact_design = folder / "2d/design.json"
    wing_conditions = dict(c["wing"], root_airfoil_design=str(exact_design), tip_airfoil_design="same_as_root")
    notify("Building the 3D wing from that exact airfoil...")
    wing = generate_wing(wing_conditions, output_folder=folder / "3d", publish_latest=False)
    if wing["root_section"]["coefficients"] != airfoil["coefficients"] or wing["tip_section"]["coefficients"] != airfoil["coefficients"]:
        raise ValueError("2D/3D shape identity check failed.")
    with np.load(folder / "3d/wing_mesh.npz") as mesh:
        v, f = mesh["vertices_m"], mesh["faces"]
    notify("Saving synchronized 2D and 3D previews...")
    fig = plt.figure(figsize=(14, 7), facecolor="#f8fafc")
    grid = fig.add_gridspec(2, 2, width_ratios=[1, 1.45], hspace=0.4)
    draw_section(fig.add_subplot(grid[0, 0]), airfoil)
    draw_planform(fig.add_subplot(grid[1, 0]), v)
    draw_wing(fig.add_subplot(grid[:, 1], projection="3d"), v, f)
    matched = airfoil["status"] == "predicted_match"
    fig.suptitle("2&3 | One design, synchronized 2D and 3D views", fontsize=17, y=0.98)
    p = airfoil["predictions"]
    fig.text(0.5, 0.105, f"Section Cl {p['Cl']:.4f} | Section Cd {p['Cd']:.5f} | Span {c['wing']['span_m']:g} m | Root chord {c['wing']['root_chord_m']:g} m | Tip chord {c['wing']['tip_chord_m']:g} m", ha="center", fontsize=10)
    fig.text(0.5, 0.055, ("Section predictor targets matched. " if matched else "No predicted target match; closest geometry shown. ") + "Whole-wing performance is unverified.", ha="center", fontsize=10, color="#9a3412")
    fig.subplots_adjust(left=0.06, right=0.98, top=0.87, bottom=0.24)
    fig.savefig(folder / "combined_preview.png", dpi=160)
    plt.close(fig)
    summary = {"name": "2&3", "version": "combined-v1", "conditions": c,
        "status": airfoil["status"], "output_folder": str(folder), "airfoil": airfoil, "wing": wing,
        "synchronization": {"exact_same_coefficients": True, "root_and_tip_use_generated_airfoil": True,
            "airfoil_design_sha256": hashlib.sha256(exact_design.read_bytes()).hexdigest(),
            "two_dimensional_wing_view": "Leading/trailing edges projected from the exported 3D mesh"},
        "physical_requirements_verified": False,
        "method": "Existing aerodynamic predictor-guided 2D search followed by parametric 3D loft; no new neural model training",
        "limitations": ["Cl/Cd targets refer to the airfoil at the input AoA and fixed Re=100000", "Span, sweep, twist and dihedral create geometry but do not establish whole-wing Cl/Cd", "Same normalized section used across span, scaled and twisted", "Weak drag prediction and source label conflicts remain", "No structural, payload or flight validation"]}
    save_json(folder / "combined_design.json", summary)
    save_json(ROOT / "results/2&3/latest.json", summary)
    return summary

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--conditions", type=Path, default=ROOT / "config/combined_conditions.json")
    args = parser.parse_args()
    try:
        s = generate_combined(json.loads(args.conditions.read_text()), progress=lambda message: print(message, flush=True))
    except (ValueError, KeyError) as error:
        parser.error(str(error))
    print(json.dumps({"name": s["name"], "status": s["status"], "same_airfoil_in_both_views": s["synchronization"]["exact_same_coefficients"], "output_folder": s["output_folder"]}, indent=2))

if __name__ == "__main__":
    main()
