from __future__ import annotations
from pathlib import Path
import csv, re, unicodedata
from typing import Dict, List, Tuple

import pandas as pd

def _norm(s: str) -> str:
    """
    Normaliseer voor matching:
    - unicode deaccent
    - upper
    - verwijder alle niet-alfanumerieke tekens
    """
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.upper()
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s

def _read_excel_headers(path: str|Path, sheet=None, header_row: int=1) -> List[str]:
    df = pd.read_excel(path, sheet_name=sheet, header=header_row-1, nrows=0, engine="openpyxl")
    cols = [str(c).strip() for c in df.columns]
    return cols

def _read_csv_header(path: str|Path) -> Tuple[List[str], str]:
    """
    Lees 1e regel van CSV en probeer delimiter te snuffen.
    """
    raw = Path(path).read_bytes()
    text = raw.decode("utf-8-sig")  # slik BOM
    lines = text.splitlines()
    sample = lines[0] if lines else ""
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",",";","|","\t"])
        delim = dialect.delimiter
    except Exception:
        delim = ","
    reader = csv.reader([sample], delimiter=delim)
    headers = next(reader, [])
    headers = [h.strip() for h in headers]
    return headers, delim

def _map_to_template(sources: List[str], targets: List[str]) -> Tuple[Dict[str,str], Dict]:
    """
    Bouw mapping: key=source (Excel), value=target (SAP).
    Exacte match op genormaliseerde naam.
    """
    t_by_norm = {}
    for t in targets:
        t_by_norm.setdefault(_norm(t), t)
    mapping = {}
    matched = 0
    for s in sources:
        ns = _norm(s)
        t = t_by_norm.get(ns)
        if t:
            mapping[s] = t
            matched += 1
    unmatched_targets = [t for t in targets if _norm(t) not in {_norm(v) for v in mapping.values()}]
    unmatched_sources = [s for s in sources if s not in mapping]
    return mapping, {"matched": matched,
                     "unmatched_targets": unmatched_targets,
                     "unmatched_sources": unmatched_sources}

def _map_identity(sources: List[str]) -> Dict[str,str]:
    """
    Eenvoudig: output == source (handig om snel te starten).
    """
    return {s: s for s in sources}

def generate_column_map_from_excel(
    excel_path: str|Path,
    sheet=None,
    header_row: int=1,
    template_csv: str|Path|None=None,
    mode: str="identity",
):
    """
    Retourneert (mapping, notes)
    mapping: dict {source_header: target_header}
    notes:   dict met matched/unmatched lijsten (alleen zinvol met template)
    """
    sources = _read_excel_headers(excel_path, sheet=sheet, header_row=header_row)
    if template_csv:
        targets, _ = _read_csv_header(template_csv)
        mapping, notes = _map_to_template(sources, targets)
        if mode == "identity":
            # vul niet-gematchte sources toch met identity als convenience
            for s in sources:
                mapping.setdefault(s, s)
        return mapping, notes
    else:
        return _map_identity(sources), {}
