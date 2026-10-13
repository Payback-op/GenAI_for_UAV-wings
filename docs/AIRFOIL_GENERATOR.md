# Conditional 2D airfoil image prototype

This extension proposes new CST airfoil geometry, uses the saved baseline to check target lift/drag, and renders the actual cross-section to PNG. It is a **predictor-guided design search**, not a newly trained conditional image network. Performance matching is provisional; no CFD, experimental or flight validation is performed.

## Use from VS Code

Choose **Terminal > Run Task > BTP 2D: Open airfoil image generator** to open the local 2D window. The default **Ctrl+Shift+B** task now opens the **2&3 combined generator**, with linked 2D and 3D views.

Enter angle of attack, desired lift coefficient, allowed lift difference, a maximum drag coefficient and thickness limits. Click **Generate shape**. The image, predicted values and match status appear in the window. Click **Open saved results** for the PNG, coordinates and condition/parameter record.

For file-based use, edit `config/design_conditions.json`, then run:

```powershell
.\.venv\Scripts\python.exe src\generate_airfoil.py --conditions config\design_conditions.json
```

Thickness ratios in JSON are fractions (0.08 = 8% chord); the desktop form displays percentages. Positive thickness is a geometry constraint, not proof of structural strength. Reynolds number is fixed at 100,000. Angle of attack is limited to -4 through +8 degrees. Weight, flight speed, material and complete-wing requirements are not accepted by this section-level prototype.

## Example, not the user's confirmed specification

The first demonstration used 4 degrees, target Cl 0.60 with tolerance 0.05, Cd limit 0.03, and thickness 8–18% chord. It generated a candidate with predicted Cl 0.603012, Cd 0.019919 and maximum thickness about 9.1% chord. These satisfy the predictor's example targets; they do not establish that a physical airfoil produces those coefficients.

## What the search does

1. Uses training-set coefficient vectors only as starting points.
2. Selects nearby promising source vectors according to the requested target.
3. Generates new vectors through local random perturbations and interpolation.
4. Reconstructs lower/upper surfaces using source-native CST.
5. Rejects intersecting sampled surfaces, thickness/camber violations, out-of-range coefficients and shapes too far from training vectors.
6. Rejects exact/near-identical source vectors, so the output is a new proposal rather than simply a plotted dataset row.
7. Scores the valid candidates and selects a predicted match, preferring lower predicted drag among matches. If none match, explicitly shows the closest candidate with a no-match status.

Search scope: 8,000 candidates by default, mutation standard deviation 0.003, nearest-training coefficient distance between 0.0001 and 0.02. These are heuristic screening settings, not calibrated uncertainty or guarantees of aerodynamic interpolation. The bounded search does not prove that no solution exists when it finds none.

Each run is saved in its own `results/generated/<UTC timestamp>/` folder. `latest.json` points to the latest real run. All ranked candidates are proposals, not certified designs.

## Geometry convention and its verification

The authors' MATLAB source gives first four coefficients for the lower surface and last four for the upper surface, cubic Bernstein polynomials, class function `sqrt(x)*(1-x)`, and zero trailing-edge thickness. Reference files are preserved at the same immutable revision as the dataset.

Reconstruction was cross-checked against 30 deterministically selected source coefficient/coordinate pairs. Interior agreement was within `1e-5` normalized chord, and the reference coefficients matched dataset vectors. The source also sets leading-edge endpoint ordinates from `A(ind,2)`, which are not encoded in the eight CSV coefficients. The new shapes deliberately use closed normalized endpoints at y=0. Endpoint offsets are reported separately and are not claimed as matching source coordinates. See `results/geometry_reference_check.json`.

`airfoil.dat` uses an upper-trailing-edge → leading-edge → lower-trailing-edge contour with normalized chord. `coordinates.csv` provides both surfaces at common chord stations. `design.json` records coefficients, all conditions, predictions, checks, nearest training distance, source/model identifiers and limitations.

## Limits and checks

The baseline still has conflicting source labels and weak drag prediction. Search can exploit predictor errors even near training shapes. A passing target status means **only that the current model predicts a match**. Source conventions, experimental validation, and model/data reliability need further work before the generator can support engineering selection.

Verification covers exported geometry, model-prediction reproduction, target-status consistency, novelty, unsupported-input rejection and an impossible-target no-match case. The desktop form also passed initialization checks. See `results/generator_verification.json`.

Run checks with:

```powershell
.\.venv\Scripts\python.exe src\verify_geometry.py
.\.venv\Scripts\python.exe src\verify_generator.py
```
