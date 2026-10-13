"""Predict from a CSV with the nine source-native input columns."""
import argparse
import joblib
import numpy as np
import pandas as pd
from common import ROOT

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input CSV with eight CST columns and AoA")
    parser.add_argument("--output", default=str(ROOT / "results/predictions.csv"))
    parser.add_argument("--reynolds", type=float, default=100000)
    args = parser.parse_args()
    if args.reynolds != 100000:
        parser.error("This model supports Reynolds number 100000 only.")
    bundle = joblib.load(ROOT / "models/airfoil_baseline.joblib")
    meta = bundle["metadata"]
    df = pd.read_csv(args.input)
    missing = set(meta["features"]) - set(df.columns)
    if missing:
        parser.error(f"Missing features: {sorted(missing)}")
    x = df[meta["features"]].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(x).all().all():
        parser.error("Inputs must be finite numbers.")
    flags = np.zeros(len(df), dtype=bool)
    for c, (low, high) in meta["training_bounds"].items():
        flags |= ((x[c] < low) | (x[c] > high)).to_numpy()
    for target, model in bundle["models"].items():
        df[target + "_predicted"] = model.predict(x)
    df["outside_training_feature_bounds"] = flags
    df["reynolds_number"] = 100000
    df.to_csv(args.output, index=False)
    print(f"Saved {len(df)} predictions; {int(flags.sum())} rows outside training feature bounds.")
    print("These flags do not establish geometry validity or full-wing feasibility.")

if __name__ == "__main__":
    main()
