# BTP: first airfoil prediction model

Read `PROJECT_CONTEXT.md` for the full project scope. This milestone predicts **2D airfoil lift and drag coefficients** from source-native CST parameters and angle of attack at Reynolds number **100,000**.

**Default: 2D only.** Press **Ctrl+Shift+B** in VS Code to open the saved airfoil generator in `models/2d`. Enter targets and click **Generate shape**. This uses the saved 2D model and writes outputs under `models/2d/results/generated`.

**2&3 combined generator:** Choose **Terminal > Run Task > BTP 2&3: Open combined generator**, enter airfoil targets and wing dimensions, then click **Generate 2D + 3D**. One run displays the airfoil cross-section, wing top view and rotatable 3D wing together, all using the exact same airfoil. See `docs/COMBINED_2D_3D.md`. Results are saved together under `results/2&3`.

**Separate 3D wing generator:** Choose **Terminal > Run Task > BTP 3D: Open wing generator**. Rotate the preview and export STL/OBJ. See `docs/3D_WING_GENERATOR.md`. The existing 2D version has been preserved under `models/2d`.

**2D airfoil generator:** Choose **Terminal > Run Task > BTP 2D: Open airfoil image generator**, enter targets and click **Generate shape**. See `docs/AIRFOIL_GENERATOR.md`. Default inputs in both tools are examples, not confirmed project requirements.

## Open and run in VS Code

1. Open `C:\BTP`.
2. Install the **Python** extension published by Microsoft (`ms-python.python`).
3. Press `Ctrl+Shift+P`, choose **Python: Select Interpreter**, and select `C:\BTP\.venv\Scripts\python.exe`.
4. Open **Terminal > New Terminal**. Run the commands below from `C:\BTP`.

Python 3.13 is installed locally under `.python-runtime`; `.venv` contains this project's packages. You do not need to activate the environment when using its full interpreter path. Keep both folders when moving this project; recreating the environment is preferable to copying it to another PC.

```powershell
.\.venv\Scripts\python.exe src\download_data.py
.\.venv\Scripts\python.exe src\prepare_data.py
.\.venv\Scripts\python.exe src\train.py
```

The download step verifies an existing dataset rather than downloading again. The training command reruns the experiment and replaces its model/results. Preserve previous results before making new experimental comparisons.

## What each stage does

- **Download:** saves the source CSV, authors' README/license, immutable GitHub revision, retrieval time, and SHA-256 checksum.
- **Prepare:** audits all inputs and labels, records rejected rows, removes exact duplicate rows, groups aliases and near-identical coefficient vectors, and saves fixed train/validation/test membership.
- **Train:** compares a mean-only reference, two Random Forest settings, and two XGBoost settings separately for lift and drag. Selects by validation RMSE. Tests the selected model and the fixed mean reference. Saves model, predictions, metadata, and plots.
- **Predict:** loads the saved model and predicts new CSV rows containing the nine input columns.

## Inputs and outputs

Inputs: `CST Coeff 1` through `CST Coeff 8`, followed by `AoA` in degrees. Targets: dimensionless `Cl` and `Cd`. `Filename` is provenance/grouping information, never a model input. Follow the authors' coefficient convention; compatibility with other CST implementations has not been established.

All operating points of the same filename remain in the same split. Identical coefficient vectors and vectors within Euclidean distance `1e-4` are connected into the same group. This is a documented proxy for near-identical shapes; it does not establish coordinate equivalence or eliminate all related airfoil families. Target proportions are about 70%/15%/15% **of groups**, so row proportions can differ.

Drag is trained in log space after checking that usable labels are positive; reported predictions/errors are transformed back to coefficient units. Four CPU threads and bounded model sizes keep this baseline suitable for the laptop.

## Review your results

| File | Meaning |
|---|---|
| `results/data_audit.json` | Observed dataset quality, coverage, exclusions, grouping and split counts |
| `results/label_conflicts.csv` | Identical shape/AoA combinations with conflicting source labels and their ranges |
| `results/validation_metrics.csv` | Candidate comparison used for model selection |
| `results/test_metrics.csv` | Final unseen-group test errors |
| `results/test_predictions.csv` | Every test reference, prediction, and residual |
| `results/plots/Cl_test.png`, `Cd_test.png` | Predictions and residuals |
| `results/plots/heldout_polars.png` | Source/model curves for four alphabetically selected test airfoils |
| `models/model_card.json` | Input schema, selected settings, versions, provenance, domain and limitations |
| `models/airfoil_baseline.joblib` | Saved predictors; load only this trusted locally created artifact |

**MAE** is average absolute error. **RMSE** gives larger errors more weight. Both use coefficient units; lower is better. **R²** compares against a constant mean prediction; higher is better, and it can be negative. These are not flight-performance percentages.

## Try saved-model inference

```powershell
.\.venv\Scripts\python.exe src\predict.py data\processed\example_inputs.csv --output results\example_predictions.csv
```

The example inputs are copied from test-set rows, so this demonstrates inference, not an additional independent evaluation. Inputs outside training feature ranges are flagged; passing that check does not establish in-distribution or physically valid geometry.

## Limits and next work

This is a forward predictor, not yet a generative-design system. The labels are source simulations; no new experimental validation has been performed. It has no learned Reynolds dependence, pitching moment, material properties, structural strength, wing mass, complete 3D wing performance, or flight control.

The source contains identical input vectors with conflicting aerodynamic labels. Source rows are retained without arbitrary corrections; all identical inputs stay in one split. Treat the trained model as an **exploratory baseline pending investigation of those conflicts**, not an evaluator ready to choose optimized designs. Distinct CST vectors also do not prove distinct original coordinate shapes.

An exploratory coefficient-search and 2D drawing extension is implemented separately from the forward predictor. A parametric 3D wing geometry generator lofts 2D sections and exports closed meshes. The **2&3** app links these two stages in one run with synchronized previews; it reuses the saved predictor and does not train another neural model. Source interior reconstruction was checked; source endpoint offsets absent from the CSV remain a documented limitation. Investigating label conflicts remains necessary before engineering candidate selection; full-wing performance and detailed physics remain future work.

Source: https://github.com/kanakaero/Dataset-of-Aerodynamic-and-Geometric-Coefficients-of-Airfoils

Paper: https://doi.org/10.3390/data9050064
