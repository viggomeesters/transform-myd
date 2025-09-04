from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import yaml
from .logging import _print

@dataclass
class TransformConfig:
    column_map: Dict[str, str]
    value_map: Dict[str, Dict[str, str]]
    value_rules: Dict[str, Dict[str, Any]]
    meta: Dict[str, Any]
    input_file: Path
    output_file: Path
    reject_file: Path
    log_dir: Path

def deep_merge(a: Any, b: Any) -> Any:
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            out[k] = deep_merge(out[k], v) if k in out else v
        return out
    return b

def parse_object_variant(obj: Optional[str], var: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if obj and not var and "_" in obj:
        left, right = obj.split("_", 1)
        return left, right
    return obj, var

def yaml_load_if_exists(path: Path):
    if path.exists():
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    return None

def assemble_layers(config_root: Path, object_name: Optional[str], variant_name: Optional[str]) -> List[Path]:
    layers = [config_root / "_shared"]
    if object_name:
        layers.append(config_root / object_name / "_shared")
        if variant_name:
            layers.append(config_root / object_name / variant_name)
        else:
            layers.append(config_root / object_name)
    return [p for p in layers if p.exists()]

def trace_layers(config_root: Path, object_name: Optional[str], variant_name: Optional[str], quiet: bool=False) -> None:
    layers = assemble_layers(config_root, object_name, variant_name)
    _print("• Config layers (least → most specific):", quiet)
    for p in layers: _print(f"   - {p}", quiet)
    for fname in ("column_map.yaml","value_map.yaml","value_rules.yaml","meta.yaml"):
        _print(f"• Files for {fname}:", quiet)
        seen = False
        for p in layers:
            f = p / fname
            if f.exists(): _print(f"   ✓ {f}", quiet); seen = True
        if not seen: _print("   (none)", quiet)

def load_layered_configs(config_root: Path, object_name: Optional[str], variant_name: Optional[str]):
    col_map, val_map, val_rules, meta = {}, {}, {}, {}
    for base in assemble_layers(config_root, object_name, variant_name):
        cm = yaml_load_if_exists(base / "column_map.yaml") or yaml_load_if_exists(base / "column_map.yml")
        vm = yaml_load_if_exists(base / "value_map.yaml")  or yaml_load_if_exists(base / "value_map.yml")
        vr = yaml_load_if_exists(base / "value_rules.yaml")or yaml_load_if_exists(base / "value_rules.yml")
        me = yaml_load_if_exists(base / "meta.yaml")       or yaml_load_if_exists(base / "meta.yml")
        if cm: col_map  = deep_merge(col_map, cm)
        if vm: val_map  = deep_merge(val_map, vm)
        if vr: val_rules= deep_merge(val_rules, vr)
        if me: meta     = deep_merge(meta, me)
    return col_map, val_map, val_rules, meta

# ---------- Naming helpers ----------
def _tokens(object_name: Optional[str], variant_name: Optional[str]) -> Dict[str, str]:
    label = f"{object_name}_{variant_name}" if object_name and variant_name else (object_name or variant_name or "")
    now = datetime.now()
    return {
        "object": object_name or "",
        "variant": variant_name or "",
        "label": label,
        "object_lower": (object_name or "").lower(),
        "variant_lower": (variant_name or "").lower(),
        "label_lower": label.lower(),
        "date": now.strftime("%Y%m%d"),
        "time": now.strftime("%H%M%S"),
        "datetime": now.strftime("%Y%m%d_%H%M%S"),
        "time_hm": now.strftime("%H%M"),
        "datetime_hm": now.strftime("%Y%m%d %H%M"),
        "datetime_hm_u": now.strftime("%Y%m%d_%H%M"),  # ← underscore variant
    }

def _expand(template: str, tok: Dict[str, str]) -> str:
    try:
        return template.format(**tok)
    except Exception:
        return template

def _join_if_relative(base: Path, maybe_path: str | Path) -> Path:
    p = Path(maybe_path)
    return p if p.is_absolute() else (base / p)

def build_config(args) -> TransformConfig:
    config_root = Path(args.config_dir)
    obj, var = parse_object_variant(args.object_name, args.variant_name)
    if getattr(args, "trace_config", False):
        trace_layers(config_root, obj, var, quiet=getattr(args, "quiet", False))

    column_map, value_map, value_rules, meta = load_layered_configs(config_root, obj, var)
    if not column_map:
        raise SystemExit("column_map ontbreekt (ook na merge). Zet ’m in config/_shared of object/variant-map.")

    tok = _tokens(obj, var)

    # Directories
    dirs_defaults = {"raw": "data/raw","out": "data/out","rejects": "data/rejects"}
    dirs = deep_merge(dirs_defaults, (meta.get("dirs") or {}))
    raw_dir, out_dir, rej_dir = Path(dirs["raw"]), Path(dirs["out"]), Path(dirs["rejects"])
    for d in (raw_dir, out_dir, rej_dir): d.mkdir(parents=True, exist_ok=True)

    # Naming (defaults al op underscore-stijl)
    naming = meta.get("naming") or {}
    pat_input   = naming.get("input")    # optioneel
    pat_output  = naming.get("output",  "{datetime_hm_u}_{label_lower}_output.csv")
    pat_rejects = naming.get("rejects", "{datetime_hm_u}_{label_lower}_rejected.csv")

    # input
    if args.input_file:
        input_file = Path(args.input_file)
    elif "input_file" in meta:
        input_file = _join_if_relative(raw_dir, _expand(str(meta["input_file"]), tok))
    elif pat_input:
        input_file = raw_dir / _expand(pat_input, tok)
    else:
        input_file = raw_dir / "bank_raw.xlsx"

    # output / rejects
    if args.output_file:
        output_file = Path(args.output_file)
    elif "output_file" in meta:
        output_file = _join_if_relative(out_dir, _expand(str(meta["output_file"]), tok))
    else:
        output_file = out_dir / _expand(pat_output, tok)

    if args.reject_file:
        reject_file = Path(args.reject_file)
    elif "reject_file" in meta:
        reject_file = _join_if_relative(rej_dir, _expand(str(meta["reject_file"]), tok))
    else:
        reject_file = rej_dir / _expand(pat_rejects, tok)

    log_dir = Path(args.log_dir); log_dir.mkdir(parents=True, exist_ok=True)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    reject_file.parent.mkdir(parents=True, exist_ok=True)

    return TransformConfig(
        column_map, value_map, value_rules, meta,
        input_file, output_file, reject_file, log_dir
    )
