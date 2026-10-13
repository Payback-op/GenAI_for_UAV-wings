"""Audit all columns and split connected filename/near-coefficient groups."""
import hashlib
import json
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from sklearn.model_selection import GroupShuffleSplit
from common import ROOT, CST, FEATURES, TARGETS, SEED, save_json

NEAR_TOLERANCE = 1e-4  # Euclidean distance in supplied eight-dimensional CST space.

def main():
    raw = ROOT / "data/raw/airfoils.csv"
    meta = json.loads((raw.parent / "source.json").read_text())
    if hashlib.sha256(raw.read_bytes()).hexdigest() != meta["sha256"]:
        raise ValueError("Raw dataset checksum changed.")
    df = pd.read_csv(raw)
    required = ["Filename"] + FEATURES + TARGETS
    if set(df.columns) != set(required):
        raise ValueError(f"Unexpected columns: {list(df.columns)}")
    numeric = df[FEATURES + TARGETS].apply(pd.to_numeric, errors="coerce")
    invalid = ~np.isfinite(numeric).all(axis=1) | df.Filename.isna() | (df.Filename.astype(str).str.strip() == "")
    nonpositive_drag = numeric.Cd <= 0
    audit = {"raw_rows": len(df), "filename_count": int(df.Filename.nunique()),
        "missing_by_column": {c: int(v) for c, v in df.isna().sum().items()},
        "nonfinite_or_unparseable_numeric": {c: int(v) for c, v in (~np.isfinite(numeric)).sum().items()},
        "invalid_rows": int(invalid.sum()), "nonpositive_drag_rows": int(nonpositive_drag.sum()),
        "column_ranges": {c: {"min": float(numeric[c].min()), "max": float(numeric[c].max())} for c in numeric},
        "raw_sha256": meta["sha256"], "reynolds_number": 100000}
    df[FEATURES + TARGETS] = numeric
    df.insert(0, "source_row", np.arange(len(df)))
    rejected = df[invalid | nonpositive_drag].copy()
    df = df[~(invalid | nonpositive_drag)].copy()
    duplicate = df.duplicated(subset=required)
    audit["exact_duplicate_rows_removed"] = int(duplicate.sum())
    df = df[~duplicate].reset_index(drop=True)
    # Join every identical filename and every near-identical coefficient vector.
    shapes = df[CST].drop_duplicates().reset_index(drop=True)
    tuples = [tuple(row) for row in shapes.to_numpy()]
    lookup = {v: i for i, v in enumerate(tuples)}
    parent = list(range(len(shapes)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    def union(i, j):
        a, b = find(i), find(j)
        if a != b:
            parent[max(a, b)] = min(a, b)
    pairs = cKDTree(shapes.to_numpy()).query_pairs(NEAR_TOLERANCE)
    for i, j in sorted(pairs):
        union(i, j)
    shape_ids = np.array([lookup[tuple(row)] for row in df[CST].to_numpy()])
    df["shape_id"] = shape_ids
    inconsistent = 0
    for _, part in df.groupby("Filename", sort=True):
        ids = part.shape_id.unique()
        inconsistent += int(len(ids) > 1)
        for i in ids[1:]:
            union(int(ids[0]), int(i))
    df["geometry_group"] = [f"g{find(int(i)):05d}" for i in shape_ids]
    exact_aliases = df.groupby("shape_id").Filename.nunique()
    conflicts = df.groupby(CST + ["AoA"])[TARGETS].nunique().max(axis=1) > 1
    label_summary = df.groupby(CST + ["AoA"])[TARGETS].agg(["min", "max", "count"])
    label_summary.columns = ["_".join(c) for c in label_summary.columns]
    for target in TARGETS:
        label_summary[target + "_spread"] = label_summary[target + "_max"] - label_summary[target + "_min"]
    conflict_report = label_summary[(label_summary.Cl_spread > 0) | (label_summary.Cd_spread > 0)].reset_index()
    audit.update({"unique_coefficient_vectors": len(shapes), "near_coefficient_pairs": len(pairs),
        "coefficient_distance_tolerance": NEAR_TOLERANCE,
        "shapes_with_multiple_filename_aliases": int((exact_aliases > 1).sum()),
        "filenames_with_multiple_vectors": inconsistent,
        "input_combinations_with_conflicting_labels": int(conflicts.sum()),
        "maximum_conflicting_label_spread": {t: float(label_summary[t + "_spread"].max()) for t in TARGETS},
        "label_conflict_policy": "Retain source rows, keep identical inputs in one group, treat baseline as exploratory; no arbitrary averaging or label correction.",
        "geometry_groups": int(df.geometry_group.nunique()), "usable_rows": len(df),
        "grouping_limit": "Coefficient proximity is a conservative proxy, not verified coordinate or airfoil-family equivalence. No shape reconstruction or physical label validation performed."})
    trainval, test = next(GroupShuffleSplit(n_splits=1, test_size=0.15, random_state=SEED).split(df, groups=df.geometry_group))
    train_sub, val_sub = next(GroupShuffleSplit(n_splits=1, test_size=0.15/0.85, random_state=SEED+1).split(df.iloc[trainval], groups=df.iloc[trainval].geometry_group))
    df["split"] = "test"
    df.loc[trainval[train_sub], "split"] = "train"
    df.loc[trainval[val_sub], "split"] = "validation"
    assert df.groupby("geometry_group").split.nunique().max() == 1
    assert df.groupby("Filename").split.nunique().max() == 1
    audit["splits"] = {s: {"rows": len(p), "groups": int(p.geometry_group.nunique())} for s, p in df.groupby("split")}
    for folder in ["data/processed", "data/splits", "results"]:
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    df.to_csv(ROOT / "data/processed/airfoils.csv", index=False)
    rejected.to_csv(ROOT / "data/processed/rejected_rows.csv", index=False)
    conflict_report.to_csv(ROOT / "results/label_conflicts.csv", index=False)
    df[["source_row", "Filename", "shape_id", "geometry_group", "split"]].to_csv(ROOT / "data/splits/membership.csv", index=False)
    save_json(ROOT / "results/data_audit.json", audit)
    save_json(ROOT / "data/processed/schema.json", {"features": FEATURES, "targets": TARGETS,
        "AoA_units": "degrees", "coefficient_units": "dimensionless", "CST_convention": "Source-native; reconstruction not yet verified",
        "reynolds_number": 100000, "seed": SEED, "group_tolerance": NEAR_TOLERANCE})
    print(json.dumps(audit, indent=2))

if __name__ == "__main__":
    main()
