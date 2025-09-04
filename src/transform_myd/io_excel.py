from __future__ import annotations
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from .config import TransformConfig


def _read_excel_df(path: Path, sheet: Any | None, dtype: Any = "string") -> pd.DataFrame:
    kw = dict(dtype=str if dtype == "string" else dtype, engine="openpyxl")
    if sheet is None:
        df = pd.read_excel(path, sheet_name=0, **kw)
    else:
        df = pd.read_excel(path, sheet_name=sheet, **kw)
    if isinstance(df, dict):
        first_key = next(iter(df))
        df = df[first_key]
    return df.rename(columns=str.strip)


def load_dataframe(cfg: TransformConfig) -> pd.DataFrame:
    meta = cfg.meta or {}
    sources = meta.get("sources")
    if not sources:
        sheet = meta.get("sheet")
        return _read_excel_df(cfg.input_file, sheet, dtype="string")

    dfs: Dict[str, pd.DataFrame] = {}
    for src in sources:
        name = src["name"]
        path = Path(src["path"])
        sheet = src.get("sheet")
        dtype = src.get("dtype", "string")
        dfs[name] = _read_excel_df(path, sheet, dtype=dtype)

    base_name = meta.get("base", sources[0]["name"])
    df = dfs[base_name]

    for f in meta.get("filters", []):
        df = df.query(f)

    for j in meta.get("joins", []):
        right = dfs[j["right"]]
        how = j.get("how", "left")
        on = j.get("on")
        left_on = j.get("left_on")
        right_on = j.get("right_on")
        suffixes = tuple(j.get("suffixes", ("", "_r")))
        if on:
            df = df.merge(right, how=how, on=on, suffixes=suffixes)
        else:
            df = df.merge(right, how=how, left_on=left_on, right_on=right_on, suffixes=suffixes)

    return df

