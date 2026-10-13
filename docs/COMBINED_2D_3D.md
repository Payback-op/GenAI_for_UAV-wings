# 2&3 — synchronized 2D and 3D wing generator

This app generates one airfoil, builds a full wing from that exact section, and displays both in the same window. It reuses the existing saved aerodynamic predictor and parametric wing loft. No additional training or software installation is needed.

## Open in VS Code

1. Open the `C:\BTP` folder.
2. Press **Ctrl+Shift+B**, or choose **Terminal > Run Task > BTP 2&3: Open combined generator**.
3. Enter your **airfoil requirements** and **wing dimensions** on the left.
4. Click **Generate 2D + 3D**. The app searches for an airfoil and uses its exact coefficients to build the wing.
5. Compare the **2D airfoil cross-section** and **2D wing top view** on the left with the **3D wing** on the right. Drag the 3D preview to rotate it.
6. Click **Open saved images / 3D files** to view all exports from that run.

Changing a field marks the displayed views as belonging to the previous run. Click Generate again to apply the new values to both views together. Inputs are locked during generation. The separate 2D and 3D apps remain available under their existing VS Code tasks; the preserved `models/2d` snapshot is unchanged.

Terminal alternative:

```powershell
.\.venv\Scripts\python.exe src\combined_app.py
```

For file-based generation, edit `config/combined_conditions.json`, then run:

```powershell
.\.venv\Scripts\python.exe src\generate_combined.py
```

## What the inputs mean

Airfoil requirements control the section search: angle of attack, target lift coefficient, allowed lift difference, maximum drag and thickness limits. The angle of attack specifies the predictor's operating condition; it does not rotate the displayed 3D wing. Reynolds number is fixed at 100,000. Thickness is a percentage in the form and a fraction in JSON.

Wing dimensions control how that section becomes a complete wing: span, root and tip chords, leading-edge sweep, dihedral and root/tip twist. Twist rotates sections around their quarter chord. The same normalized airfoil is used throughout the span; chord scaling and twist make root and tip look different in metres while preserving the underlying section shape. There is no separate root/tip file selection in 2&3.

The top view projects the actual 3D mesh's leading/trailing edges. It includes twist in those edge positions, so it corresponds to the same generated wing. The airfoil cross-section is shown before twist, with normalized chord and equal axis scales.

Starting values are editable examples: AoA 4°, target Cl 0.6 ± 0.05, maximum Cd 0.03, thickness 8–18%, span 1.8 m, root chord 0.30 m, tip chord 0.15 m, sweep 10°, dihedral 5°, root twist 0° and tip twist −2°. Existing standalone configurations are not changed by the combined app.

## Saved together

Every successful run gets its own folder under `results/2&3/<UTC timestamp>/`:

| File / folder | Contents |
|---|---|
| `combined_preview.png` | Side-by-side 2D cross-section, top view and 3D preview |
| `combined_design.json` | Shared conditions, nested section/wing results, exact-shape identity and provenance |
| `2d/airfoil.png` | Airfoil cross-section image |
| `2d/airfoil.dat`, `2d/coordinates.csv` | Normalized airfoil coordinates |
| `2d/design.json`, `2d/ranked_candidates.csv` | Section parameters, predictions, status and search results |
| `3d/wing_mm.stl` | Closed wing mesh; import using **millimetres** |
| `3d/wing_m.obj` | Same mesh with coordinate values in **metres** |
| `3d/wing_mesh.npz`, `3d/spanwise_geometry.csv` | Indexed metre mesh and section geometry |
| `3d/wing_preview.png`, `3d/wing_design.json` | Separate 3D image, dimensions, mesh checks and the exact source airfoil |

`results/2&3/latest.json` records the latest combined result. Standalone `results/generated/latest.json` and `results/3d/latest.json` are not replaced. STL/OBJ are mesh formats, not editable STEP models with spars, ribs or materials.

## Status and verification

**Targets matched** means the existing section predictor returns Cl/Cd within the requested limits. These estimates do not apply to the entire 3D wing. If the search finds no predicted match, all views still show the same closest candidate with an explicit no-match status.

The saved predictor has conflicting source labels and weak drag accuracy. Geometry generation and matching views do not establish physical aerodynamic performance or structural capacity. Detailed physics work remains deferred.

Verification checks exact source identity, inverse scaling/twist of every exported span station against the 2D section, independent prediction/status reproduction, 2D top-view edges, STL/OBJ scale, invalid-input handling and a no-match case. Run:

```powershell
.\.venv\Scripts\python.exe src\verify_combined.py
.\.venv\Scripts\python.exe src\combined_app.py --smoke-test
```
