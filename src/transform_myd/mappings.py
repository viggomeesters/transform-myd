from __future__ import annotations
from typing import Any, Dict
import pandas as pd


def apply_value_maps(df: pd.DataFrame, maps: Dict[str, Dict[str, str]]) -> pd.DataFrame:
    if not maps:
        return df
    for col, mapping in maps.items():
        if col not in df.columns:
            continue
        series = df[col]
        df[col] = series.map(lambda v: mapping.get("" if pd.isna(v) else str(v).strip(),
                                                  "" if pd.isna(v) else str(v).strip()))
    return df

