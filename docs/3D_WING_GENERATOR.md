# Separate 3D wing geometry model

The existing 2D version is preserved under `models/2d`. Its initial 50 files are recorded with SHA-256 checksums in `snapshot_manifest.json`. The original working 2D app and predictor still exist; no retraining or source changes were required to generate the wing.

## Run in VS Code

Choose **Terminal > Run Task > BTP 3D: Open wing generator** to open the separate **3D wing generator**. Change the example dimensions and click **Generate 3D model**. Drag the model with the mouse to rotate it; use the toolbar to reset the view. Click **Open STL / OBJ results** to access exports. **Ctrl+Shift+B** now opens the **2&3 combined generator**, documented in `COMBINED_2D_3D.md`.

For the original 2D app, choose **Terminal > Run Task > BTP 2D: Open airfoil image generator**.

Or run from the terminal in `C:\BTP`:

```powershell
.\.venv\Scripts\python.exe src\wing_app.py
```

For a file-based run, edit `config/wing_conditions.json` and run:

```powershell
.\.venv\Scripts\python.exe src\generate_wing.py
```

## Inputs

The defaults are examples, not professor-approved requirements: span **1.8 m**, root chord **0.30 m**, tip chord **0.15 m**, leading-edge sweep **10°**, dihedral **5°**, root twist **0°**, and tip twist **-2°**.

Span means horizontal tip-to-tip distance. The model creates both wing halves with one shared centre section. Positive twist is nose-up around the quarter chord; negative tip twist gives washout. Positive dihedral raises both tips. Root/tip chord variation and coefficient variation are linear with absolute span position.

By default, the same airfoil from the preserved 2D version is used at root and tip. The form lets you choose another generated **design.json** (or **latest.json**) and optionally a different tip design. Do not select unrelated JSON files such as model cards. The referenced airfoil coefficients are copied into each 3D result, so subsequent changes to a latest pointer do not erase the result's provenance.

Prototype bounds: span 0.2–20 m; root and tip chords 0.03–3 m; tip chord no greater than root; sweep -30 to +45°; dihedral ±15°; root/tip twist ±15° with no more than 20° difference. These are supported geometry settings, not aircraft feasibility limits. Mesh resolutions are editable in JSON: odd `span_stations` (5–101) and `chord_points` (21–301).

## Outputs

Each successful generation creates a new folder under `results/3d/`:

| File | Use |
|---|---|
| `wing_mm.stl` | Closed triangulated wing envelope; import numerical units as **millimetres** |
| `wing_m.obj` | Same geometry with numerical coordinates in **metres** |
| `wing_mesh.npz` | Indexed vertices in metres and triangular faces |
| `wing_preview.png` | Static view of the exported geometry |
| `spanwise_geometry.csv` | Chord, twist, datum positions and section thickness along span |
| `wing_design.json` | Inputs, source airfoils, dimensions, units, mesh checks and limitations |

STL and OBJ do not reliably encode physical units; choose the documented units when importing into CAD or a viewer. STL is a mesh, not an editable STEP/B-rep model. The envelope has no ribs, spars, wall thickness, material or mass definition.

The reference trapezoidal area is `span * (root chord + tip chord) / 2`; aspect ratio is `span² / reference area`. These refer to the untwisted reference planform, not the curved skin's surface area. At the example dimensions, reference area is **0.405 m²**, aspect ratio **8**, and taper ratio **0.5**.

## What kind of model this is

This is a **parametric 3D geometry generator**, using sections from the existing 2D work. It is not a trained 3D performance network. No matched full-wing aerodynamic/structural training dataset exists in this project yet. Section predictions remain recorded as historical provenance only; they are not applied as whole-wing lift or drag. Geometry changes and local chord also change relevant flight conditions, which this generator does not solve.

It satisfies the supplied geometric dimensions. It does not establish aerodynamic targets, structural strength, material/mass requirements, payload support or flight feasibility. Existing 2D label conflicts and weak drag performance remain unresolved.

## Verification

The example mesh has 6,560 unique vertices and 13,116 triangles. Checks cover closed topology (each edge shared by two triangles), opposite edge orientation, finite coordinates, no degenerate faces, positive enclosed geometric volume, mirrored wing halves, analytical rectangular/tapered volume cases, reference dimensions, exported STL/OBJ scales and rejection of invalid dimensions. The saved 2D snapshot checksums were also verified unchanged.

These are software/geometry checks, not aerodynamic, structural or manufacturing validation. Run:

```powershell
.\.venv\Scripts\python.exe src\verify_wing.py
```
