# First airfoil model: exploratory baseline

Run completed locally on 8 October 2026 (India time).

## Data

- Authors' Agarwal airfoil CSV downloaded from immutable revision `90dae87066913316bc28547b966951294fb885c8`.
- 33,705 rows, 2,946 filename labels, 1,928 exact coefficient vectors.
- No missing, nonfinite, or unparseable values in the required columns; all drag labels positive.
- Angle range: -4 to +8 degrees; fixed Reynolds number: 100,000.
- Conservative filename/near-coefficient grouping produced 1,716 groups.
- Training: 23,633 rows / 1,200 groups; validation: 5,079 rows / 258 groups; test: 4,993 rows / 258 groups.

## Important source-data finding

7,061 identical shape/AoA input combinations have conflicting lift or drag labels. The maximum difference for an identical input is 1.2211 in Cl and 0.07669 in Cd. These rows were retained with their original labels and kept together in the splits. Missing-value checks do not establish physical reliability.

The causes remain unverified: inspect source mapping, original coordinates, coefficient fitting, and simulation conditions/convergence before attributing the conflicts to a particular cause. No labels were averaged, corrected or discarded based on model residuals.

## Experiment

Two Random Forest settings and two XGBoost settings were compared independently per target against a mean-only reference. Models trained on training groups only; validation RMSE selected the winner. The test set was evaluated after selection, without further tuning. For drag, non-dummy models learned log(Cd); scores below use original coefficient units.

XGBoost with depth 4 was selected for both targets. All eight learned fits took approximately 26 seconds in total, excluding setup, plotting and verification. This was measured locally; it is not a promise about larger datasets or simulation workloads. Peak memory was not measured.

| Target/model | Test MAE | Test RMSE | Test R² |
|---|---:|---:|---:|
| Lift, selected XGBoost | 0.053000 | 0.084609 | 0.953516 |
| Lift, mean reference | 0.326696 | 0.392440 | -0.000036 |
| Drag, selected XGBoost | 0.008494 | 0.013419 | 0.204666 |
| Drag, mean reference | 0.010810 | 0.015050 | -0.000362 |

Lift fits the held-out source labels well overall. Drag improvement is limited. The plots show substantial source/model discrepancies for several held-out drag curves. Do not read R² as a percentage accuracy or use the drag model for optimization yet. Negative Cl predictions are permissible; no negative Cd predictions occurred on the test set.

## Verification

Checks passed for filename disjointness, exact/near-coefficient disjointness across splits, saved-model reproduction of test predictions, CLI inference agreement, and rejection of an unsupported Reynolds number. See `verification.json`. These checks validate the software boundaries, not the source aerodynamics or experimental validity.

## Next step

Investigate the conflicting input/label combinations and verify the source's CST-to-coordinate convention. Plan a separate, documented data-quality experiment before adding further models or candidate ranking. If replacing this dataset or changing splits, version the experiment and its reports rather than claiming direct comparison with this first test score.

The current artifact is a 2D forward aerodynamic predictor. Geometry generation, full-wing aerodynamics, structural strength, material/mass predictions, and flight validation have not been completed.
