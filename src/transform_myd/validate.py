from __future__ import annotations
from typing import Any, Dict, List, Tuple
import importlib
import pandas as pd


def apply_value_rules(df: pd.DataFrame, rules: Dict[str, Dict[str, Any]]) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[int, List[str]]]:
    if not rules:
        return df.copy(), df.iloc[0:0].copy(), {}

    errors: Dict[int, List[str]] = {}
    for col, cfg in rules.items():
        if col not in df.columns:
            series = pd.Series([""] * len(df), index=df.index, dtype="string")
        else:
            series = df[col].fillna("").astype(str).str.strip()

        if cfg.get("required"):
            bad_idx = series[series == ""].index
            for i in bad_idx:
                errors.setdefault(i, []).append(f"{col} is required")

        pat = cfg.get("pattern")
        if pat:
            mism = series[(series != "") & (~series.str.match(pat, na=False))].index
            for i in mism:
                errors.setdefault(i, []).append(f"{col} mismatches {pat}")

        if "max_length" in cfg:
            ml = int(cfg["max_length"])
            too_long = series[series.str.len() > ml].index
            for i in too_long:
                errors.setdefault(i, []).append(f"{col} longer than {ml}")

        custom = cfg.get("custom")
        if custom:
            mod = importlib.import_module(custom["module"]); fn = getattr(mod, custom["function"])
            for i, v in series.items():
                try:
                    if v == "" and not cfg.get("required", False):
                        continue
                    if not fn(v):
                        errors.setdefault(i, []).append(f"{col} custom failed")
                except Exception as e:
                    errors.setdefault(i, []).append(f"{col} custom error: {e}")

    error_idx = pd.Index([i for i in errors.keys() if isinstance(i, int) and i in df.index])
    valid_mask = ~df.index.isin(error_idx)
    valid_df = df.loc[valid_mask].copy()
    reject_df = df.loc[~valid_mask].copy()
    if not reject_df.empty:
        reject_df["__errors"] = reject_df.index.map(lambda i: "; ".join(errors.get(i, [])))
    return valid_df, reject_df, errors

