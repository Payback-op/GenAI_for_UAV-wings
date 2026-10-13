# BTP_UAV_Gen — UAV Wing Generative Design Project

**Purpose:** A self-contained project handoff for another AI assistant. Read this file before proposing work, writing code, selecting datasets, or discussing progress.

**Context updated:** 2 October 2026, India time.

**Original project title:** “Generative design approaches for UAV structures.”

**Current focus:** UAV wings, following a discussion with the project professor.

**Student context:** B.Tech Mechanical Engineering, IIT Jodhpur.

**Deadline:** The user needs to complete the project by October 2026. The exact submission date has not been supplied. Earlier schedules assumed **31 October 2026**; this is a planning assumption, not a confirmed deadline.

## 1. Quick briefing

The user initially explored generative design of UAV structures and screened papers about drone frames, chassis, landing gear, and topology optimization. An earlier proposed implementation focused on one detachable quadcopter arm. After meeting the professor, the user changed the active scope to **wings**.

The intended long-term system should propose wing designs by varying geometry, area, weight, and material while meeting aircraft load and flight requirements. The user also mentioned flight movement, control, and navigation toward a target.

The immediate instruction is **model first, using useful existing datasets; do not start detailed physics work yet**. The current proposed path is to build a machine-learning aerodynamic predictor, use it to score generated airfoil shapes, and develop candidate 3D wing geometry. Full-wing aerodynamics, structural capacity, propulsion, and flight control require additional work and data.

No trained model, optimized wing, completed CFD/FEA study, fabricated wing, or demonstrated flight result has been reported. Treat proposed methods and schedules as recommendations rather than completed work.

## 2. What the user has actually decided

| Item | Status |
|---|---|
| Broad project title | Supplied by the user: generative design approaches for UAV structures |
| Current component | Wings, following the professor discussion |
| Desired variables | Wing area, weight, material, and geometry |
| Desired eventual behaviour | Support the required aircraft weight and enable operational flight and controlled movement |
| Immediate priority | Find suitable datasets and prepare the model |
| Detailed physics work | Deferred for now at the user's request |
| Completion month | October 2026 |
| Exact submission date | Unknown |
| Aircraft configuration | Unknown; conventional fixed-wing is only the current working assumption |
| Meaning of “model” | Interpreted as a machine-learning model because the user requested datasets; exact architecture/output still needs agreement |
| 2D airfoil versus complete 3D wing output | Not yet confirmed with the professor |

The detachable-quadcopter-arm plan is historical context and has been superseded. Do not return to it as the active project unless the user explicitly changes direction.

## 3. Engineering distinctions that affect the model

These distinctions define the scope; they are not a request to begin a physics derivation.

- **Airfoil:** The two-dimensional cross-section of a wing.
- **Wing:** The complete three-dimensional structure, with span, chord distribution, taper, twist, sweep, dihedral, and internal construction.
- **Aerodynamic lift:** The force that can support aircraft weight in flight.
- **Structural load capacity:** Whether the wing and its attachments can withstand the applied loads. Adequate predicted lift does not establish structural strength.
- **Thrust:** For a conventional fixed-wing UAV, thrust is normally supplied by a motor/propeller or another propulsion system. The wing primarily provides lift and also creates drag. A flapping-wing aircraft needs a different treatment.
- **Flight control/navigation:** Uses aircraft dynamics, control surfaces, actuators, sensors, and control algorithms. A static aerodynamic predictor is not an autopilot.

Do not equate predicted airfoil coefficients with a proven ability of the full aircraft to fly, carry a specified payload, turn, or reach a target.

## 4. Current progress and evidence

### Completed or reported

1. The user supplied ten literature links and an uploaded review PDF in earlier discussion.
2. An earlier AI screened the papers and identified two duplicate references.
3. A professor-facing presentation was created during the earlier frame/arm planning stage.
4. The user subsequently discussed the project with the professor and reported the wing-focused scope.
5. Dataset options for airfoil prediction, shape generation, and aircraft design were researched.
6. One downloadable starter CSV was inspected on 1 October 2026; its audit is recorded below.

### Not reported as completed

- A requirements specification for the UAV or wing.
- A finalized dataset choice approved by the professor.
- A cleaned, versioned training dataset or train/validation/test split.
- Trained regression models or a generative model.
- A selected baseline airfoil or wing geometry.
- Wing construction/material selection.
- New CFD, FEA, wind-tunnel testing, manufacturing, or flight validation.

The earlier presentation describes the old discussion. It should be revised for the wing/model scope before being used as a current progress presentation.

## 5. Dataset shortlist

The main recommendation is: **start with the ready-to-use Agarwal CSV, expand operating-condition coverage with NASA Airfoil Learning, and use selected UIUC experimental data for independent comparison.** AFBench is an optional shape-generation resource.

The shortlist does not contain a verified dataset combining airfoil geometry, complete wing planform, material/construction, structural capacity, propulsion, and flight control in one matched set of training examples. This is a limitation of the sources checked, not a claim that no such data exists anywhere.

### 5.1 Starter: aerodynamic and geometric coefficients of airfoils

**Paper:** Agarwal et al., “A Comprehensive Dataset of the Aerodynamic and Geometric Coefficients of Airfoils in the Public Domain,” Data, 2024, 9(5), 64.

- Paper: https://doi.org/10.3390/data9050064
- Repository: https://github.com/kanakaero/Dataset-of-Aerodynamic-and-Geometric-Coefficients-of-Airfoils
- CSV: https://raw.githubusercontent.com/kanakaero/Dataset-of-Aerodynamic-and-Geometric-Coefficients-of-Airfoils/main/Final%20Results/COMPILED%20AIRFOIL%20DATA.csv

**Why useful:** Already tabular and includes shape parameters and performance labels, allowing a small first regression model without new simulations.

**Data source:** OpenFOAM-generated aerodynamic results, at a fixed Reynolds number of **100,000**.

**Audit of the CSV inspected on 1 October 2026:**

| Property | Observed value |
|---|---|
| Data rows | 33,705 |
| Distinct `Filename` labels | 2,946 |
| Angle-of-attack range | −4° to +8° |
| Shape inputs | Eight columns: `CST Coeff 1` through `CST Coeff 8` |
| Aerodynamic labels | `Cl`, `Cd` |
| `Cl` range | Approximately −0.75723 to 1.90666 |
| `Cd` range | Approximately 0.0014021 to 0.0899762 |
| Missing/non-finite values checked in `AoA`, `Cl`, `Cd` | None found |

**Exact columns:**

```text
Filename
AoA
CST Coeff 1
CST Coeff 2
CST Coeff 3
CST Coeff 4
CST Coeff 5
CST Coeff 6
CST Coeff 7
CST Coeff 8
Cl
Cd
```

**Limits:**

- Fixed Reynolds number: the model cannot learn Reynolds-number variation from this CSV alone.
- No pitching-moment column, material data, structural labels, or complete-wing geometry.
- The angle range is insufficient for general claims about stall or post-stall behaviour.
- Distinct filenames do not prove distinct geometry. Check duplicate and near-duplicate shapes.
- The audit did not establish that every shape-input column is clean or that every aerodynamic sample is physically reliable.
- Follow the authors' CST convention. Do not reinterpret these eight columns as another library's CST/Kulfan representation without checking the definition and validating reconstruction.
- These counts describe the previously inspected version. Re-audit the downloaded file and retain a checksum when implementation starts.

### 5.2 Main expansion: NASA Airfoil Learning

- Repository and tutorials: https://github.com/nasa/airfoil-learning
- NASA software entry: https://software.nasa.gov/software/LEW-20283-1
- Technical report: https://ntrs.nasa.gov/citations/20220006290
- Raw dataset ZIP advertised by the repository: https://nasa-public-data.s3.amazonaws.com/plot3d_utilities/airfoil-learning-dataset.zip

**Inputs documented:** Airfoil geometry/vertices, graph connectivity where applicable, Reynolds number, angle of attack, and `Ncrit` (a transition/turbulence parameter).

**Labels documented:** Lift coefficient, drag coefficient, pitching-moment coefficient, and pressure coefficient; additional labels may be present.

**Why useful:** Broader operating conditions, moment labels, and code demonstrating machine learning on airfoil geometry.

**Limits:** XFOIL-generated 2D data rather than flight measurements or complete-wing structural results. Inspect actual coverage and preprocessing before selecting a UAV operating envelope. The full archive was not successfully downloaded during the earlier research; do not assume its contents have been fully audited.

Prefer the raw data when building a reproducible preprocessing pipeline. The repository notes that the already-normalized dataset may not include the required normalization scalars.

### 5.3 Geometry and independent experimental reference: UIUC

- Coordinate database: https://m-selig.ae.illinois.edu/ads/coord_database.html
- Low-Speed Airfoil Tests: https://m-selig.ae.illinois.edu/uiuc_lsat.html

**Contents:** Approximately 1,650 coordinate sets in the database; the low-speed testing programme reports wind-tunnel validation of over 200 airfoils. Individual reports cover different Reynolds-number ranges and test conditions.

**Use:** Known baseline shapes, geometry comparisons, and selected experimental polar checks at matching conditions.

**Limits:** Coordinate files alone have no aerodynamic labels. Many experimental results are in books/reports and may require extraction or digitization. Do not treat every coordinate file as having corresponding experimental polars.

### 5.4 Optional generative resource: AFBench / AF-200K

- Repository: https://github.com/InternScience/Intern-WingWing
- Paper: https://arxiv.org/abs/2406.18846
- Dataset folder linked by the authors: https://drive.google.com/drive/folders/1SV9Vyb0EisuG0t69YauGUyq0C5gKwRgt

**Contents:** About 200,000 2D airfoil shapes, geometric and aerodynamic annotations, and generative-model benchmark code. The paper describes consistent 257-point shape representations.

**Use:** Training or studying a conditional shape generator, and comparing generative methods.

**Important domain limitation:** The paper's aerodynamic annotation uses Reynolds number **100,000**, Mach numbers **0.2–0.7**, and prescribed lift coefficients **0–2**. XFOIL returns corresponding angle, drag, and moment labels. These are not arbitrary low-speed-UAV operating conditions.

Geometry can be useful for a generator, but aerodynamic labels require domain matching. The published benchmark includes geometric generation/editing tasks; do not assume every model directly accepts a payload or desired full-wing performance. Keep training splits grouped by related geometry where possible.

### 5.5 Optional whole-aircraft context: AircraftVerse

- Dataset: https://zenodo.org/records/6525446
- Repository: https://github.com/SRI-CSL/AircraftVerse
- Paper: https://arxiv.org/abs/2306.05562

**Contents:** 27,714 battery-powered aircraft designs and simulated performance, with design descriptions that can include wing span/chord and component selections.

**Use:** A later study of configuration versus aircraft-level mass and performance. Filter for relevant wing-bearing configurations and comparable missions before use.

**Limits:** Aircraft-level outcomes do not isolate the contribution of one wing. This is not a standalone wing-material-strength dataset.

### 5.6 Other resources considered

- **AirfRANS:** https://airfrans.readthedocs.io/en/latest/notes/dataset.html — 1,000 2D CFD simulations, Reynolds numbers 2–6 million, angles −5° to +15°. Useful for flow-field surrogate research, but may be outside a small UAV's intended Reynolds range.
- **NeuralFoil:** https://github.com/peterdsharpe/NeuralFoil — an existing trained airfoil predictor, useful as a comparison or later rapid evaluator. Distinguish use of a pretrained tool from training the user's own model. Labels generated with NeuralFoil must be identified as model-generated and are not independent experimental validation.

Verify current access, licensing, and source versions before redistributing data or incorporating it into a deliverable.

## 6. Recommended model architecture

### Stage A — Forward aerodynamic predictor

**First prototype with the starter CSV:**

- Inputs: eight supplied CST coefficients plus angle of attack.
- Targets: `Cl` and `Cd`.
- `Filename`: grouping/provenance field, not the principal shape representation.
- Reynolds number: fixed context, not a learned variable in this first dataset.

**Expanded prototype with NASA data:**

- Inputs: normalized geometry or a verified common shape parameterization, angle of attack, Reynolds number, and available transition/turbulence parameters.
- Targets: section lift, drag, and pitching-moment coefficients.
- Include Mach or other condition features only when the data supports them.

**Initial model comparisons:** Random Forest, XGBoost, and optionally a small multilayer perceptron. Choose based on held-out performance and implementation time rather than model complexity. Separate regressors for each target are a simple starting point.

Consider a positive/log-space treatment of drag only after inspecting label quality. Preserve the inverse transformation in the inference pipeline and evaluate error in the original coefficient units too.

### Stage B — Candidate generation and ranking

The forward predictor scores designs; by itself it is not a generative-design model.

For an achievable October prototype:

1. Begin with known valid airfoils or verified shape-parameter bounds.
2. Generate candidate parameter variations or run a bounded search.
3. Reconstruct and check the geometry.
4. Predict aerodynamic coefficients at several operating points supported by the data.
5. Rank or retain a Pareto set of candidates rather than choosing solely the maximum lift or a single attractive shape.
6. Retain source geometry, input parameters, predicted values, and model/domain information for every candidate.

Geometry checks should cover surface intersection, positive thickness, leading/trailing-edge behaviour, smoothness, and reasonable thickness/camber. Candidate designs far outside training coverage need an explicit domain flag.

A conditional VAE or an AFBench-based generator is an optional extension after the baseline predictor and geometry checks work. Do not make an ambitious diffusion/GAN implementation the critical path without confirming resources and expectations.

### Stage C — Parametric 3D wing generation

Build a geometry generator around selected airfoil sections with editable:

- Span and root/tip chord.
- Taper and chord distribution.
- Twist, sweep, and dihedral.
- Root/tip airfoil selection.

Store area and aspect ratio consistently with the geometry. These quantities are related; do not independently randomize mutually inconsistent wing dimensions.

At this stage, the model can output **candidate wing geometry with section-level aerodynamic estimates**. Complete-wing predictions require relevant 3D labels or an explicitly documented later analysis method.

### Stage D — Material, structure, propulsion, and control

These are future modules, not already solved by the airfoil predictor.

| Module | Necessary information | Possible later outputs |
|---|---|---|
| Wing aerodynamics | Complete planform, airfoil distribution, flight conditions, and relevant 3D labels | Whole-wing lift/drag/moment and spanwise loading |
| Wing structure | Material properties, skin/spar/rib geometry, laminate layup where relevant, load cases | Wing mass, stiffness, stress, deflection, and structural feasibility |
| Propulsion | Motor/propeller, battery, airspeed and operating-point data | Available thrust and power |
| Flight dynamics/control | Aircraft mass/inertia, centre of gravity, aerodynamic derivatives, control surfaces/actuators | Stability, manoeuvre response, and controller performance |

A material name is not a sufficient structural input. Properties and construction must be connected to the actual component. Wing mass is generally an outcome of geometry, construction, and material choice; it should not be varied independently without explaining how that mass is achieved.

## 7. Required data preparation and evaluation

1. Save raw data separately from processed data; record URL, retrieval date, source/version, and checksum.
2. Audit every input and output column, missing/non-finite values, units, duplicates, and condition coverage.
3. Normalize coordinate orientation/chord consistently and confirm the shape-parameter convention.
4. Detect duplicate and near-duplicate geometries, including shapes with different filenames.
5. Split by airfoil or geometry family before fitting preprocessing. Keep all operating points for one geometry in one split.
6. Fit scalers, dimensionality reduction, or learned preprocessing on training data only.
7. Tune using validation data; reserve the test set for the final comparison.
8. Report MAE, RMSE, and R² separately for each target. Avoid a single regression “accuracy percentage” and percentage errors around zero lift/moment.
9. Plot predicted versus reference values, residuals, and polar curves for held-out airfoils.
10. When multiple operating conditions are available, test generalization across conditions as well as across shapes.
11. Compare against selected experimental cases at matching conditions where available. Prediction of simulation labels and agreement with experiments are different findings.
12. Keep solver/model sources distinguishable. Do not pool XFOIL, OpenFOAM, pretrained-model, and experimental labels as interchangeable ground truth without a justified strategy.

Do not fabricate labels for material effects, load capacity, stall, payload feasibility, or flight behaviour when the source data does not contain those outcomes.

## 8. Specifications still needed

These are unknown. Ask only for what the immediate next task requires, and make progress on independent work in parallel.

| Specification | Current status |
|---|---|
| Exact October submission date | Unknown; 31 October is provisional |
| Conventional fixed-wing, hybrid VTOL, or flapping-wing UAV | Unknown |
| Professor's required output: airfoil generator, 3D wing generator, or full performance model | Unknown |
| Total aircraft mass, including wings, battery, electronics, and payload | Unknown |
| Payload mass | Unknown |
| Cruise/minimum/maximum speed and operating altitude | Unknown |
| Wingspan/area/geometry envelope | Unknown |
| Baseline airfoil or reference UAV | Unknown |
| Material and manufacturing method | Unknown |
| Spar/rib/skin construction | Unknown |
| Software access | Unknown; earlier mentions were recommendations, not confirmed access |
| Laptop OS, RAM, CPU, GPU, or cloud access | Unknown |
| Fabrication and experimental expectations | Unknown |

Do not carry over the old arm-plan assumptions about DJI F450 dimensions, PLA/FDM construction, thrust loads, or software licenses to the wing project.

## 9. Provisional October execution plan

This plan is for a **model-and-candidate-design milestone**. It does not promise a fully flight-validated UAV by the same dates. Adjust it when the professor's deliverable and exact deadline are known.

| Dates | Work | Reviewable output |
|---|---|---|
| 2–5 October | Confirm immediate model scope, obtain/audit starter data, prepare grouped splits | Data audit, feature/target definitions, reproducible split files |
| 6–12 October | Train and compare baseline predictors; inspect held-out curves | Metrics, plots, inference pipeline, model/domain limitations |
| 13–19 October | Add bounded candidate generation and geometry checks | Ranked valid candidate airfoils with traceable predictions |
| 20–24 October | Generate selected 3D wing candidates; document construction/material requirements | Geometry exports, design tables, clearly scoped comparison |
| 25–31 October | Final comparisons, documentation, report, presentation, reproducibility checks | Submission package and demonstration |

Minimum credible October outputs:

- A documented dataset and clean preprocessing pipeline.
- Evaluation on unseen airfoils rather than only random rows.
- A saved model with an accompanying input/output schema.
- Candidate-generation and geometry-validation logic.
- Several ranked candidates with transparent assumptions.
- A parametric wing generator if required and feasible.
- A report/presentation that distinguishes completed results from future physics and flight validation.

## 10. Suggested implementation organisation

This is a proposed layout, not a claim that these files already exist.

| Proposed path | Purpose |
|---|---|
| `data/raw/` | Original source data |
| `data/processed/` | Clean features, targets, and provenance |
| `data/splits/` | Fixed grouped train/validation/test membership |
| `src/prepare_data.py` | Audit and preprocessing |
| `src/train.py` | Baseline training and model comparison |
| `src/predict.py` | Reproducible inference |
| `src/generate_candidates.py` | Shape generation/search and geometry checks |
| `src/build_wing.py` | Parametric 3D wing generation |
| `models/` | Model artifacts and preprocessing state |
| `results/` | Metrics, plots, and candidate tables |
| `geometry/` | Selected airfoil/wing exports |
| `docs/` | Report, references, and presentation |

Python with NumPy, pandas, scikit-learn, and XGBoost is a reasonable initial stack. PyTorch and additional geometry tools are optional. Select actual versions after checking the execution environment; no pinned environment has been established.

## 11. Earlier literature review — historical background

The following list records the earlier AI's screening of the user-supplied papers. It is **not a fresh full-text review performed for this README**. Some sources were assessed through abstracts or accessible sections. Recheck important claims before citing them in a report.

Most references are about quadcopter frames or other UAV structures. They help explain generative-design workflows and validation, but they are not direct wing-aerodynamics datasets. A wing-focused literature review still needs to be developed.

| Original link | Paper/source | Earlier assessment and relevance now |
|---|---|---|
| 1 | Andries & Zaharia, “Generative Design, Simulation, and 3D Printing of the Quadcopter Drone Frame,” 2025. https://www.mdpi.com/2076-3417/15/17/9647 | Useful design-to-manufacturing workflow. Frame-specific; do not transfer its loads or results to a wing. |
| 2 | Gutierrez et al., “Topological Optimization, Generative Design and Validation of Drone Structures,” AIAA, 2023. https://arc.aiaa.org/doi/10.2514/6.2023-0964 | Useful comparison of topology optimization, generative design, and validation. Obtain full text before adopting methods. |
| 3 | “Design and Fabrication of an Optimized Drone Chassis,” 2025. https://ijrpr.com/uploads/V6ISSUE7/IJRPR50455.pdf | Earlier review flagged internal inconsistencies in fabrication and material claims. Low-confidence technical foundation. |
| 4 and 10 | Balayan et al., “Optimal Design of Quadcopter Chassis Using Generative Design and Lightweight Materials,” 2024. https://www.mdpi.com/2075-1702/12/3/187 | Useful structural/material comparison. These two original links refer to the same paper. |
| 5 | Seregi & Ficzere, “Weight Reduction of a Drone Using Generative Design,” 2021. https://pdfs.semanticscholar.org/6397/dc1055f6fcc50adcb0b45c2c1d6a71b2f26d.pdf | Supporting preserve/obstacle geometry and design-selection workflow; not wing aerodynamic training data. |
| 6 | Gupta et al., “Generative Design of Main Landing Gear for a Remote-Controlled Aircraft,” 2023. https://www.sciencedirect.com/science/article/pii/S2214785323004753 | Supporting design comparison and selection; component-specific landing-gear methodology. |
| 7 | “Use of a Generative Design Approach for UAV Frame Structure Optimization and Additive Manufacturing,” 2023. https://link.springer.com/chapter/10.1007/978-981-19-6107-6_15 | Optional procedural background; earlier assessment had limited full-text access. |
| 8 and uploaded review PDF | Souvanhnakhoomman & Chua, “A Comprehensive Review of Generative Design Applications in UAVs,” 2025. https://journals.utm.my/aej/article/view/21286 | Broad landscape reference. The ResearchGate link and uploaded review were identified as the same source. |
| 9 | Darsin et al., “Advanced Optimization of Drone Frame Design Through Generative Design and 3D Printing,” 2025. https://link.springer.com/article/10.1007/s12206-024-1210-x | Useful structural design-space exploration background. Verify full-text details before adopting testing/anisotropy methods. |

Original alternate links:

- Link 4: https://www.researchgate.net/publication/378962414_Optimal_Design_of_Quadcopter_Chassis_Using_Generative_Design_and_Lightweight_Materials_to_Advance_Precision_Agriculture
- Link 8: https://www.researchgate.net/publication/389439127_A_COMPREHENSIVE_REVIEW_OF_GENERATIVE_DESIGN_APPLICATIONS_IN_UNMANNED_AERIAL_VEHICLES

The original ten links plus the uploaded review were screened as **nine unique papers** after those duplicates were accounted for. Published mass-reduction percentages or other numerical results from these papers are not project results and should not be presented as such.

## 12. Instructions for the next AI assistant

1. Continue the **wing-focused, model-first** project. Treat the old arm plan as superseded.
2. Respect the request to defer new detailed physics work. Existing simulation labels can support model development now; distinguish that from later physical validation.
3. Begin with the dataset audit and a clear feature/target contract. Do not silently change the project into a flight controller or a full aircraft simulation.
4. Clarify whether the professor expects a 2D airfoil generator or complete 3D wing generator, because this materially changes the minimum deliverable.
5. Make useful progress using the known starter CSV while collecting missing specifications. Avoid repeatedly asking for information already supplied in this README.
6. Use practical, staged explanations and reproducible code. The user is a mechanical-engineering student; explain unfamiliar ML concepts as they become necessary.
7. Distinguish recommendations, assumptions, observed data, trained-model results, and physical evidence.
8. Keep material/weight/load-capacity claims tied to actual construction and relevant labels.
9. Preserve source URLs, dataset versions, conventions, splits, and evaluation conditions.
10. Never invent a completed experiment, a model score, a geometry, software access, or professor approval.

### Suggested first message in a new AI chat

> Read this README as the context for my B.Tech project, “Generative design approaches for UAV structures.” My professor has directed me to focus on wings. I need to complete the project in October 2026, and I want to build the data/model stage before starting detailed physics work. Help me audit the recommended starter CSV, define the inputs and outputs, and build a baseline predictor with a geometry-grouped train/validation/test split. Then help me add candidate generation and, if required, a parametric 3D wing generator. Clearly separate airfoil predictions from complete-wing strength and flight feasibility. Use the confirmed information here and ask only for missing details that affect the next step.

## 13. Handoff limitations

This README consolidates the visible project discussion and the recorded dataset research. It is not a repository of completed implementation files, a certification of dataset fidelity, or evidence of an operational UAV. Update the status, specifications, and results as real work is completed.

## 14. Implementation update — 8 October 2026, India time

This update supersedes earlier statements that no dataset pipeline or trained model exists; those sections remain as historical handoff context.

- VS Code and Microsoft's Python extension are installed. A separate Python 3.13.14 runtime is under `.python-runtime`, with project packages in `.venv`. Actual package versions are recorded in `requirements.lock.txt`.
- The Agarwal CSV and source README/license were downloaded at immutable revision `90dae87066913316bc28547b966951294fb885c8`. Provenance/checksum: `data/raw/source.json`.
- A complete-column audit found 33,705 rows, 2,946 filename labels, 1,928 exact coefficient vectors, no invalid numeric inputs/targets, and positive drag labels.
- Important: 7,061 identical coefficient/AoA combinations contain conflicting labels. Causes have not been established. See `results/label_conflicts.csv`; do not assume this dataset is ready for optimization.
- Filename aliases and coefficient vectors within Euclidean distance `1e-4` were grouped before splitting. This is a conservative coefficient-space proxy, not a verified geometry-family partition. Split membership: `data/splits/membership.csv`.
- First exploratory Random Forest/XGBoost comparison completed; validation selected depth-4 XGBoost for both targets. Test lift MAE/RMSE/R²: 0.053000 / 0.084609 / 0.953516. Test drag: 0.008494 / 0.013419 / 0.204666. Drag performance remains limited.
- Saved model: `models/airfoil_baseline.joblib`; schema, domain, settings, and package/source provenance: `models/model_card.json`. Forward predictions only; candidate generation has not been implemented.
- Software verification passed for split boundaries, artifact reproduction, inference, and unsupported-Reynolds rejection. No experimental or complete-wing validation performed.
- Start with `README.md` and `results/FIRST_MODEL_REPORT.md` to review the implementation. Next: investigate source label conflicts and CST reconstruction before trusting generated-candidate rankings. Detailed physics work remains deferred.

## 15. Conditional 2D geometry/image extension — 8 October 2026

- The user explicitly requested a model that generates an image meeting conditions and selected **2D airfoil cross-section first**. Exact user target values have not been supplied; initial displayed targets are labelled examples.
- `src/generate_airfoil.py` now performs bounded local CST mutations/interpolation from training shapes, geometry checks, and prediction-based matching. It is a surrogate-guided search, not a trained conditional image neural network. It exports PNG, DAT coordinates, ranked parameters and `design.json`.
- `src/design_app.py` provides a local desktop input form. VS Code's default build task (`Ctrl+Shift+B`) opens it. Conditions: angle, target Cl/tolerance, maximum Cd and thickness range; Re fixed at 100000.
- The authors' source convention was verified against 30 processed reference pairs for interior reconstruction and matching coefficient vectors. Source leading-edge anchors absent from the CSV differ from generated normalized endpoints (closed at y=0); see `results/geometry_reference_check.json`. Full source-shape equivalence has not been established.
- Example conditions: AoA 4 degrees, Cl 0.6 +/- 0.05, Cd <= 0.03, thickness 8–18% chord. First example candidate predicts Cl 0.603012, Cd 0.019919, maximum thickness about 9.1% chord. This is a predictor-target match only; physical compliance remains unverified.
- Generator checks passed for geometry exports, independently reproduced predictions, novelty, target-status consistency and explicit no-match on an impossible target. The desktop form passed initialization.
- Existing source label conflicts and weak drag performance remain unresolved. Candidate search must remain labelled exploratory; no new CFD/experimental/flight evidence exists. See `docs/AIRFOIL_GENERATOR.md` for instructions and limits.

## 16. Saved 2D version and separate 3D wing generator — 8 October 2026

- User requested another model producing 3D geometry and asked to save the existing version as 2D. They authorized editable example wing dimensions.
- Existing 2D code, predictor, config, data/reference information and latest design are preserved under `models/2d`, with 50-file initial checksum manifest. Original working files remain intact. All saved checksums passed after 3D generation.
- A separate **parametric geometry generator**, not newly trained 3D ML, is implemented in `src/wing_geometry.py`, `src/generate_wing.py` and `src/wing_app.py`. Definition: `models/3d/model_card.json`. It lofts root/tip 2D CST sections into a symmetric, closed full-wing mesh with taper, sweep, dihedral and quarter-chord twist.
- Editable example parameters: span 1.8 m, root chord 0.30 m, tip chord 0.15 m, leading-edge sweep 10 degrees, dihedral 5 degrees, root twist 0 degrees and tip twist -2 degrees. These are examples, not aircraft requirements or professor approval.
- Example reference planform area 0.405 m², aspect ratio 8, taper ratio 0.5. Geometry is 6,560 vertices / 13,116 triangles. Checks passed for closed topology, orientation, degeneracy, symmetry, analytical volume/dimensions and STL/OBJ round trips.
- 3D results are under `results/3d`. Exports: STL with numerical millimetre coordinates, OBJ with metre coordinates, PNG preview, indexed NPZ mesh, section table and provenance JSON. No internal structure/material/mass model or STEP/B-rep output.
- VS Code Ctrl+Shift+B now opens the 3D app. Existing 2D app is available via task `BTP 2D: Open airfoil image generator`.
- No matched 3D training data, whole-wing aerodynamic predictions, structural capacity or flight validation has been added. Section estimates are provenance only; geometry does not establish load/flight requirements. Detailed physics remains deferred. See `docs/3D_WING_GENERATOR.md`.

## 17. Combined 2&3 generator — 8 October 2026

- User requested another version named **2&3**, with matching 2D and 3D views from one design. The standalone 2D/3D apps and preserved 2D snapshot remain available.
- `src/combined_app.py` provides one form for airfoil targets and wing dimensions, with synchronized airfoil cross-section, wing top view and rotatable 3D wing previews. One Generate button updates all views; changed inputs are marked until a new run completes.
- `src/generate_combined.py` searches for the 2D section using the existing predictor, then feeds that run's exact `2d/design.json` into the wing loft. Root and tip use identical normalized coefficients, scaled and twisted across the span. This integrates existing methods; it is not newly trained 3D ML.
- Separate combined settings: `config/combined_conditions.json`. Model definition: `models/2&3/model_card.json`. Each run saves PNG/coordinates/STL/OBJ and provenance together under `results/2&3`; standalone latest results are not replaced.
- **Ctrl+Shift+B now opens 2&3**. Separate apps remain under tasks `BTP 2D: Open airfoil image generator` and `BTP 3D: Open wing generator`. See `docs/COMBINED_2D_3D.md`.
- Integration checks passed for exact section identity, inverse scaling/twist at all 41 example span stations, projected 2D edges, reproduced predictions, mesh exports, invalid inputs and a separate 7-station no-match case. All 50 saved 2D file checksums remained unchanged; the combined GUI rendered both canvases and correctly marked changed inputs. See `results/2&3/verification.json`.
- Cl/Cd targets describe the section at the input AoA and fixed Re=100000. They do not establish full-wing Cl/Cd. Existing label conflicts, weak drag prediction and physical-validation limits remain; detailed physics is still deferred.
