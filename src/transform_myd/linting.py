from __future__ import annotations
import importlib
import re
from pathlib import Path
from typing import List, Tuple

from .config import build_config


KNOWN_TRANSFORMS = {"strip", "upper", "lower", "zfill", "pad_left", "regex_replace", "to_int", "to_string", "custom"}


def lint_config(args) -> int:
    issues: List[Tuple[str, str, str]] = []
    try:
        cfg = build_config(args)
    except SystemExit as e:
        print(f"[E001] {e}")
        return 1

    targets = [cfg.column_map[k] for k in cfg.column_map.keys()]
    dups = {t for t in targets if targets.count(t) > 1}
    if dups:
        issues.append(("ERROR", "E002", f"Dubbele targetkolommen na mapping: {sorted(dups)}"))

    for col, mapping in (cfg.value_map or {}).items():
        if col not in cfg.column_map:
            issues.append(("WARN", "W201", f"value_map verwijst naar onbekende kolom '{col}'"))
        for k, v in mapping.items():
            if not isinstance(k, str) or not isinstance(v, str):
                issues.append(("ERROR", "E202", f"value_map voor '{col}' bevat niet-string key/value: {k!r}->{v!r}"))

    for col, rcfg in (cfg.value_rules or {}).items():
        if col not in cfg.column_map:
            issues.append(("WARN", "W101", f"value_rules bevat '{col}' dat niet in column_map staat"))
        if "max_length" in rcfg:
            try:
                ml = int(rcfg["max_length"])
                if ml <= 0:
                    issues.append(("ERROR", "E103", f"max_length voor '{col}' moet > 0 zijn"))
            except Exception:
                issues.append(("ERROR", "E103", f"max_length voor '{col}' is geen integer"))
        pat = rcfg.get("pattern")
        if pat:
            try:
                re.compile(pat)
            except re.error as e:
                issues.append(("ERROR", "E102", f"pattern voor '{col}' is ongeldig: {e}"))
        steps = rcfg.get("transforms", [])
        if isinstance(steps, list):
            for s in steps:
                if isinstance(s, str):
                    op = s
                elif isinstance(s, dict) and len(s) == 1:
                    op = next(iter(s.keys()))
                else:
                    issues.append(("WARN", "W104", f"transforms voor '{col}' bevat onherkenbare stap: {s!r}"))
                    continue
                if op not in KNOWN_TRANSFORMS:
                    issues.append(("WARN", "W104", f"onbekende transform '{op}' voor kolom '{col}'"))
        if "custom" in rcfg:
            c = rcfg["custom"]
            mod = c.get("module"); fn = c.get("function")
            if not mod or not fn:
                issues.append(("WARN", "W105", f"custom voor '{col}' mist module/function"))
            else:
                try:
                    m = importlib.import_module(mod)
                    getattr(m, fn)
                except ModuleNotFoundError:
                    issues.append(("WARN", "W105", f"custom module niet gevonden voor '{col}': {mod}"))
                except AttributeError:
                    issues.append(("WARN", "W105", f"custom functie niet gevonden voor '{col}': {fn} in {mod}"))
                except Exception as e:
                    issues.append(("WARN", "W105", f"custom import fout voor '{col}': {e}"))

    meta = cfg.meta or {}
    joins = meta.get("joins", [])
    sources = {s["name"] for s in meta.get("sources", [])} if meta.get("sources") else set()
    if joins and not sources:
        issues.append(("WARN", "W303", "joins gedefinieerd maar meta.sources ontbreekt/leeg"))
    for j in joins:
        r = j.get("right")
        if not r or (sources and r not in sources):
            issues.append(("ERROR", "E301", f"join.right '{r}' bestaat niet in sources"))
        if not (j.get("on") or (j.get("left_on") and j.get("right_on"))):
            issues.append(("ERROR", "E302", f"join mist 'on' of 'left_on/right_on'"))
    for s in meta.get("sources", []):
        if "sheet" not in s or s.get("sheet") in (None, ""):
            issues.append(("WARN", "W304", f"source '{s.get('name')}' mist 'sheet' – default wordt eerste sheet"))

    lvl_order = {"ERROR": 0, "WARN": 1}
    issues.sort(key=lambda x: (lvl_order[x[0]], x[1], x[2]))
    if issues:
        print("\nLint report:")
        for lvl, code, msg in issues:
            prefix = "!" if lvl == "ERROR" else "-"
            print(f" {prefix} [{code}] {msg}")
    else:
        print("Lint: geen issues gevonden.")

    has_error = any(lvl == "ERROR" for lvl, _, _ in issues)
    if has_error:
        return 1
    if getattr(args, "strict", False) and issues:
        return 1
    return 0


def lint_all(config_dir: Path, strict: bool = False) -> int:
    exit_code = 0
    for obj_path in sorted([p for p in config_dir.iterdir() if p.is_dir() and p.name != "_shared"]):
        variants = [p.name for p in obj_path.iterdir() if p.is_dir()]
        if variants:
            for var in sorted(variants):
                from argparse import Namespace
                ns = Namespace(
                    object_name=obj_path.name, variant_name=var, config_dir=str(config_dir),
                    input_file=None, output_file=None, reject_file=None, log_dir="logs",
                    sample=None, report=False, report_format="md",
                    scaffold_object=None, from_excel=None, force=False, dry_run=False,
                    runlist_path=None, lint=True, lint_all=False, strict=strict,
                    trace_config=False, no_txt_log=False, quiet=False, classic_summary=False,
                    ci=False, fail_on_rejects=False, fail_on_zero_valid=False,
                )
                print(f"\n== LINT {obj_path.name}_{var} ==")
                rc = lint_config(ns)
                exit_code = exit_code or rc
        else:
            from argparse import Namespace
            ns = Namespace(
                object_name=obj_path.name, variant_name=None, config_dir=str(config_dir),
                input_file=None, output_file=None, reject_file=None, log_dir="logs",
                sample=None, report=False, report_format="md",
                scaffold_object=None, from_excel=None, force=False, dry_run=False,
                runlist_path=None, lint=True, lint_all=False, strict=strict,
                trace_config=False, no_txt_log=False, quiet=False, classic_summary=False,
                ci=False, fail_on_rejects=False, fail_on_zero_valid=False,
            )
            print(f"\n== LINT {obj_path.name} ==")
            rc = lint_config(ns)
            exit_code = exit_code or rc
    return exit_code

