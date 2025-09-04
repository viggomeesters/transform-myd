from __future__ import annotations
from typing import Any, Dict
import importlib
import pandas as pd


def _to_int_str(val: Any) -> str:
    s = "" if pd.isna(val) else str(val).strip()
    if s == "":
        return ""
    try:
        return str(int(float(s)))
    except Exception:
        return s


def apply_transforms(df: pd.DataFrame, rules: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
    if not rules:
        return df
    for col, cfg in rules.items():
        steps = cfg.get("transforms")
        if not steps:
            continue
        if col not in df.columns:
            df[col] = ""
        s = df[col].where(~df[col].isna(), "")

        def ensure_str(x):
            return "" if pd.isna(x) else str(x)

        for step in steps:
            if isinstance(step, str):
                op, arg = step, None
            elif isinstance(step, dict) and len(step) == 1:
                op, arg = next(iter(step.items()))
            else:
                continue

            if op == "strip":
                s = s.astype(str).str.strip()
            elif op == "upper":
                s = s.astype(str).str.upper()
            elif op == "lower":
                s = s.astype(str).str.lower()
            elif op == "zfill":
                s = s.astype(str).apply(lambda v: v.zfill(int(arg)) if v.strip() != "" else "")
            elif op == "pad_left":
                s = s.astype(str).apply(lambda v: v.rjust(int(arg.get("width", 0)), str(arg.get("fillchar", " "))) if v.strip() != "" else "")
            elif op == "regex_replace":
                pat = arg.get("pattern"); repl = arg.get("repl", "")
                if pat:
                    s = s.astype(str).str.replace(pat, repl, regex=True)
            elif op == "to_int":
                s = s.apply(_to_int_str)
            elif op == "to_string":
                s = s.apply(ensure_str)
            elif op == "custom":
                mod = importlib.import_module(arg["module"]); fn = getattr(mod, arg["function"])
                s = s.apply(lambda v: fn(v))
            else:
                pass

        df[col] = s
    return df

