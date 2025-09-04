from __future__ import annotations
from pathlib import Path
from typing import Optional, Tuple
import pandas as pd


COLUMN_MAP_TEMPLATE = """# column_map.yaml — bron→doel kolommen
{BODY}
"""
VALUE_MAP_TEMPLATE = "{}\n"
VALUE_RULES_TEMPLATE = """# value_rules.yaml — transforms & validatie (voorbeelden)
#ORT01:
#  pattern: '^[^0-9]*$'
#SWIFT:
#  transforms: [strip, upper]
#  max_length: 11
"""
META_TEMPLATE_SINGLE = """# meta.yaml — enkel-bestand (backward compat)
input_file:  "{stem}_raw.xlsx"
output_file: "S_{stem}#FreeText_Mandatory.csv"
reject_file: "{stem_lower}_rejected.csv"
"""


def _scaffold_paths(config_root: Path, object_or_combo: str) -> Tuple[Path, str]:
    combo = object_or_combo.replace("/", "_").strip("_")
    parts = combo.split("_")
    if len(parts) == 2:
        obj, var = parts
        base = config_root / obj / var
        stem = combo
    else:
        obj = parts[0]
        base = config_root / obj
        stem = obj
    return base, stem


def scaffold(config_root: Path, object_or_combo: str, from_excel: Optional[Path],
             force: bool = False, dry_run: bool = False) -> None:
    base, stem = _scaffold_paths(config_root, object_or_combo)
    body = '# SOURCE1: "TARGET1"\n# SOURCE2: "TARGET2"\n'
    if from_excel:
        try:
            df = pd.read_excel(from_excel, nrows=0, engine="openpyxl")
            cols = [str(c).strip() for c in df.columns]
            if cols:
                body = "\n".join(f'{c}: "{c}"' for c in cols) + "\n"
        except Exception as e:
            print(f"[!] Waarschuwing: kon kolommen niet lezen uit {from_excel}: {e}")

    files = {
        base / "column_map.yaml": COLUMN_MAP_TEMPLATE.format(BODY=body),
        base / "value_map.yaml": VALUE_MAP_TEMPLATE,
        base / "value_rules.yaml": VALUE_RULES_TEMPLATE,
        base / "meta.yaml": META_TEMPLATE_SINGLE.format(stem=stem, stem_lower=stem.lower()),
    }

    print(f"Scaffold → {base}")
    if not dry_run:
        base.mkdir(parents=True, exist_ok=True)
    for path, content in files.items():
        if path.exists() and not force:
            print(f"  skip  {path} (bestaat al)")
            continue
        print(f"  write {path}")
        if not dry_run:
            path.write_text(content, encoding="utf-8")
    print("Gereed." + (" (dry-run)" if dry_run else ""))

