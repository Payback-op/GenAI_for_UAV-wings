"""Train on training groups, select on validation, evaluate test once."""
import hashlib
import json
import platform
import time
import importlib.metadata
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor
from common import ROOT, FEATURES, TARGETS, SEED, save_json

def metrics(y, pred):
    return {"MAE": float(mean_absolute_error(y, pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y, pred))), "R2": float(r2_score(y, pred))}

def main():
    frame = pd.read_csv(ROOT / "data/processed/airfoils.csv")
    parts = {s: frame[frame.split == s].copy() for s in ["train", "validation", "test"]}
    for a, b in [("train", "validation"), ("train", "test"), ("validation", "test")]:
        assert set(parts[a].geometry_group).isdisjoint(parts[b].geometry_group)
    result = ROOT / "results"
    (ROOT / "models").mkdir(exist_ok=True)
    (result / "plots").mkdir(exist_ok=True)
    validation, test_metrics, models, durations, selections = [], [], {}, {}, {}
    predictions = parts["test"][["source_row", "Filename", "geometry_group"] + FEATURES + TARGETS].copy()
    for target in TARGETS:
        candidates = {
            "mean_baseline": DummyRegressor(strategy="mean"),
            "random_forest_leaf2": RandomForestRegressor(n_estimators=200, min_samples_leaf=2, max_depth=24, n_jobs=4, random_state=SEED),
            "random_forest_leaf4": RandomForestRegressor(n_estimators=200, min_samples_leaf=4, max_depth=18, n_jobs=4, random_state=SEED),
            "xgboost_depth4": XGBRegressor(n_estimators=400, max_depth=4, learning_rate=0.05, subsample=0.9, colsample_bytree=0.9, tree_method="hist", device="cpu", n_jobs=4, random_state=SEED),
            "xgboost_depth6": XGBRegressor(n_estimators=400, max_depth=6, learning_rate=0.05, subsample=0.9, colsample_bytree=0.9, tree_method="hist", device="cpu", n_jobs=4, random_state=SEED),
        }
        fitted = {}
        for name, model in candidates.items():
            if target == "Cd" and name != "mean_baseline":
                model = TransformedTargetRegressor(regressor=model, func=np.log, inverse_func=np.exp)
            start = time.perf_counter()
            model.fit(parts["train"][FEATURES], parts["train"][target])
            elapsed = time.perf_counter() - start
            pred = model.predict(parts["validation"][FEATURES])
            score = metrics(parts["validation"][target], pred)
            validation.append({"target": target, "model": name, **score, "training_seconds": elapsed})
            fitted[name] = model
            durations[target + "/" + name] = elapsed
            print(f"{target} {name}: validation RMSE={score['RMSE']:.6f}, {elapsed:.1f}s", flush=True)
        # Pick independently for lift/drag by validation RMSE, including the dummy.
        chosen = min([v for v in validation if v["target"] == target], key=lambda v: v["RMSE"])["model"]
        models[target] = fitted[chosen]
        selections[target] = chosen
        y = parts["test"][target].to_numpy()
        pred = models[target].predict(parts["test"][FEATURES])
        predictions[target + "_predicted"] = pred
        predictions[target + "_residual"] = pred - y
        test_metrics.append({"target": target, "model": chosen, **metrics(y, pred), "negative_predictions": int((pred < 0).sum())})
        # Dummy test score is a fixed reference, not used for model selection.
        dummy_pred = fitted["mean_baseline"].predict(parts["test"][FEATURES])
        if chosen != "mean_baseline":
            test_metrics.append({"target": target, "model": "mean_baseline", **metrics(y, dummy_pred), "negative_predictions": int((dummy_pred < 0).sum())})
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        axes[0].scatter(y, pred, s=5, alpha=0.25)
        low, high = min(y.min(), pred.min()), max(y.max(), pred.max())
        axes[0].plot([low, high], [low, high], "k--")
        axes[0].set(xlabel=f"Reference {target}", ylabel=f"Predicted {target}", title="Unseen-airfoil test set")
        axes[1].scatter(y, pred-y, s=5, alpha=0.25)
        axes[1].axhline(0, color="black", linestyle="--")
        axes[1].set(xlabel=f"Reference {target}", ylabel="Prediction minus reference", title="Residuals")
        fig.tight_layout()
        fig.savefig(result / f"plots/{target}_test.png", dpi=150)
        plt.close(fig)
    pd.DataFrame(validation).to_csv(result / "validation_metrics.csv", index=False)
    pd.DataFrame(test_metrics).to_csv(result / "test_metrics.csv", index=False)
    predictions.to_csv(result / "test_predictions.csv", index=False)
    # Deterministic alphabetical selection avoids cherry-picking good polar examples.
    names = sorted(parts["test"].Filename.unique())[:4]
    fig, axes = plt.subplots(2, 4, figsize=(14, 7), squeeze=False)
    for col, name in enumerate(names):
        curve = parts["test"][parts["test"].Filename == name].sort_values("AoA")
        for row, target in enumerate(TARGETS):
            ax = axes[row, col]
            ax.plot(curve.AoA, curve[target], "o-", label="Source simulation")
            ax.plot(curve.AoA, models[target].predict(curve[FEATURES]), "s--", label="Model")
            ax.set(title=name, xlabel="Angle of attack (degrees)", ylabel=target)
            ax.grid(alpha=0.3)
    axes[0, 0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(result / "plots/heldout_polars.png", dpi=150)
    plt.close(fig)
    provenance = json.loads((ROOT / "data/raw/source.json").read_text())
    metadata = {"features": FEATURES, "targets": TARGETS, "selected_models": selections,
        "training_bounds": {c: [float(parts["train"][c].min()), float(parts["train"][c].max())] for c in FEATURES},
        "reynolds_number": 100000, "AoA_units": "degrees", "seed": SEED,
        "drag_transform": "log(Cd) for non-dummy models; predictions inverse-transformed",
        "selection_rule": "Lowest validation RMSE independently per target; no test tuning or train+validation refit",
        "raw_sha256": provenance["sha256"], "source_revision": provenance["revision"],
        "split_sha256": hashlib.sha256((ROOT / "data/splits/membership.csv").read_bytes()).hexdigest(),
        "python": platform.python_version(), "packages": {p: importlib.metadata.version(p) for p in ["numpy", "pandas", "scipy", "scikit-learn", "xgboost", "matplotlib", "joblib"]},
        "training_seconds": durations,
        "limitations": ["2D source-simulation coefficient prediction, not experimental validation", "Fixed Reynolds number 100000", "No material, mass, structural, complete-wing or flight outputs", "Source-native CST; no geometry reconstruction yet", "Near-coefficient grouping is not a complete family holdout", "Feature-bound flags cannot guarantee in-distribution geometry"]}
    metadata["data_quality"] = json.loads((ROOT / "results/data_audit.json").read_text())
    metadata["limitations"].append("Source contains identical inputs with conflicting labels: exploratory baseline only pending investigation")
    joblib.dump({"models": models, "metadata": metadata}, ROOT / "models/airfoil_baseline.joblib", compress=3)
    save_json(ROOT / "models/model_card.json", metadata)
    print("TEST RESULTS (coefficient units):", flush=True)
    print(pd.DataFrame(test_metrics).to_string(index=False), flush=True)

if __name__ == "__main__":
    main()
