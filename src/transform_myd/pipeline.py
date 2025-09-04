from __future__ import annotations
import hashlib, os, re, unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List
import pandas as pd
from .config import build_config, parse_object_variant
from .io_excel import load_dataframe
from .mappings import apply_value_maps
from .transforms import apply_transforms
from .validate import apply_value_rules
from .reports import generate_report_md, generate_report_html, write_reject_reasons_csv
from .logging import log_step, _print, write_txt_log

def build_label(args) -> str:
   obj, var = parse_object_variant(args.object_name, args.variant_name)
   return f"{obj}_{var}" if obj and var else (obj or "UNSPECIFIED")

def _tz(name: str) -> ZoneInfo:
   try: return ZoneInfo(name)
   except Exception: return ZoneInfo("UTC")

def _maybe_sanitize_texts(df: pd.DataFrame, cfg) -> pd.DataFrame:
   text_cfg = ((cfg.meta or {}).get("text") or {})
   if not text_cfg: return df
   df = df.copy()
   obj_cols = [c for c in df.columns if df[c].dtype == "object"]
   norm = (text_cfg.get("normalize") or "none").upper()
   strip_ctrl = bool(text_cfg.get("strip_control", False))
   collapse_ws = bool(text_cfg.get("collapse_ws", False))
   repair_mj = bool(text_cfg.get("repair_mojibake", False))
   ctrl_re = re.compile(r"[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]")
   def fix(s):
       if not isinstance(s, str): return s
       x = s
       if norm in ("NFC","NFKC","NFD","NFKD"): x = unicodedata.normalize(norm, x)
       if strip_ctrl: x = ctrl_re.sub("", x)
       if collapse_ws: x = re.sub(r"\s+", " ", x).strip()
       if repair_mj and "Ã" in x:
           if re.search(r"Ã[\x80-\xBF]", x):
               try: x = x.encode("latin1","strict").decode("utf-8","strict")
               except Exception: pass
       return x
   for c in obj_cols: df[c] = df[c].map(fix)
   return df

def _add_lineage(df: pd.DataFrame, label: str, cfg, args) -> pd.DataFrame:
   meta_line = (cfg.meta or {}).get("lineage", {}) or {}
   if getattr(args, "no_lineage", False) or not meta_line.get("enabled", True): return df
   df = df.copy()
   tz = _tz(meta_line.get("tz", "Europe/Amsterdam")); now = datetime.now(tz)
   run_id = f"{now:%Y%m%d_%H%M}_{label.lower()}"; df["__run_id"] = run_id
   df["__row_id"] = range(1, len(df)+1)
   try: mtime = datetime.fromtimestamp(os.path.getmtime(cfg.input_file), tz)
   except Exception: mtime = now
   df["__ingest_ts"] = mtime.isoformat(timespec="seconds")
   df["__transform_ts"] = now.isoformat(timespec="seconds")
   uid_cfg = meta_line.get("uid", {}) or {}
   if uid_cfg.get("enabled") and uid_cfg.get("keys"):
       keys = uid_cfg["keys"]; length = int(uid_cfg.get("length", 16))
       salt_tpl = uid_cfg.get("salt", "{label}")
       salt = salt_tpl.format(object=(cfg.meta or {}).get("object",""),
                              variant=(cfg.meta or {}).get("variant",""),
                              label=label, label_lower=label.lower())
       def row_uid(row) -> str:
           parts = []
           for k in keys:
               val = row.get(k, ""); val = "" if pd.isna(val) else str(val).strip().lower()
               parts.append(val)
           return hashlib.sha256((salt+"|"+"|".join(parts)).encode("utf-8")).hexdigest()[:length]
       df["__uid"] = df.apply(row_uid, axis=1)
   return df

def _warn_if_mojibake(df: pd.DataFrame, quiet: bool):
   suspects = ("Ã¶","Ã¤","Ã¼","ÃŸ","Ã©","Ãª","Ã¡","Ãº","Ã±","Ã¸","Ã¥")
   try:
       sample = df.select_dtypes("object").astype("string").stack().astype(str).head(1000)
       if sample.str.contains("|".join(map(re.escape, suspects)), na=False).any():
           _print("⚠️  Verdachte mojibake gedetecteerd in tekst. Tip: utf-8-sig aanlaten of text.repair_mojibake=true.", quiet)
   except Exception:
       pass

def run_pipeline(args):
   label = build_label(args); cfg = build_config(args)

   df = load_dataframe(cfg)
   df = _maybe_sanitize_texts(df, cfg)
   df = _add_lineage(df, label, cfg, args)
   _warn_if_mojibake(df, args.quiet)
   log_step("A. Rijen ingelezen", True, f"{len(df)}", args.quiet)

   if getattr(args, "sample", None) and args.sample > 0:
       df = df.head(args.sample); log_step("A1. Sample", True, f"eerste {len(df)} rijen", args.quiet)

   # --- Stages bepalen: CLI > meta.reports.stages > default
   if getattr(args, "reports", None):
       stages = [s.strip() for s in str(args.reports).split(",") if s.strip()]
   else:
       meta_reports = ((cfg.meta or {}).get("reports") or {})
       stages = meta_reports.get("stages") or ["raw","validation"]

   # --- RAW snapshot vóór maps/transforms
   raw_df = df.copy()
   raw_report_paths: List[str] = []
   if getattr(args, "report", False) and ("raw" in stages):
       if args.report_format in ("md","both"):   raw_report_paths.append(str(generate_report_md(raw_df.copy(), cfg, label, "raw")))
       if args.report_format in ("html","both"): raw_report_paths.append(str(generate_report_html(raw_df.copy(), cfg, label, "raw")))
       if raw_report_paths: log_step("B1. Raw report", True, " / ".join(raw_report_paths[-2:]), args.quiet)

   # --- Maps & Transforms
   df = apply_value_maps(df, cfg.value_map)
   for col in cfg.column_map:
       if col not in df.columns: df[col] = ""
   df = apply_transforms(df, cfg.value_rules)
   log_step("E. Transforms toegepast", True, "", args.quiet)

   # --- Post-transform report (+ delta vs RAW)
   post_report_paths: List[str] = []
   if getattr(args, "report", False) and ("post" in stages):
       if args.report_format in ("md","both"):   post_report_paths.append(str(generate_report_md(df.copy(), cfg, label, "post", baseline=raw_df)))
       if args.report_format in ("html","both"): post_report_paths.append(str(generate_report_html(df.copy(), cfg, label, "post", baseline=raw_df)))
       if post_report_paths: log_step("E1. Post report", True, " / ".join(post_report_paths[-2:]), args.quiet)

   # --- Validate
   valid_df, reject_df, errors = apply_value_rules(df, cfg.value_rules)
   log_step("F. Validatie voltooid", True, f"{len(valid_df)}/{len(df)} geldig", args.quiet)

   # --- Lineage kolommen borgen in valid/reject
   lineage_cols = [c for c in df.columns if c.startswith("__")]
   for lc in lineage_cols:
       if lc not in valid_df.columns and lc in df.columns:
           try: valid_df[lc] = df.loc[valid_df.index, lc]
           except Exception: pass
       if lc not in reject_df.columns and lc in df.columns:
           try: reject_df[lc] = df.loc[reject_df.index, lc]
           except Exception: pass

   # --- Export (optioneel lineage aan einde)
   export_cols = list(cfg.column_map.keys())
   meta_lineage = (cfg.meta or {}).get("lineage", {}) or {}
   keep_lineage = getattr(args, "keep_lineage", False) or bool(meta_lineage.get("keep_in_export", False))
   if keep_lineage and lineage_cols:
       export_cols = export_cols + [c for c in lineage_cols if c in valid_df.columns]
   out_df = valid_df[export_cols].rename(columns=cfg.column_map)

   # Encodings
   enc_cfg = ((cfg.meta or {}).get("encoding") or {})
   enc_out = getattr(args, "encoding_out", None) or enc_cfg.get("output") or "utf-8-sig"
   enc_rej = getattr(args, "encoding_rejects", None) or enc_cfg.get("rejects") or "utf-8-sig"

   out_df.to_csv(cfg.output_file, index=False, encoding=enc_out)
   reject_df.to_csv(cfg.reject_file, index=False, encoding=enc_rej)
   log_step("G. Output-bestanden", True, f"{len(out_df)}/{len(df)} ✓, rejects {len(reject_df)}", args.quiet)

   # Legacy TXT log (met BOM)
   log_file_path = None
   if not getattr(args, "no_txt_log", False):
       total, good, bad = len(df), len(valid_df), len(reject_df)
       summary_lines = [f"Label             : {label}",
                        f"Total records     : {total:>6}",
                        f"Valid records     : {good:>6}",
                        f"Rejected records  : {bad:>6}", "",
                        f"Export  : {cfg.output_file} ({good} rijen)",
                        f"Rejects : {cfg.reject_file} ({bad} rijen)"]
       per_rec = [f"Row {i+2}: {'REJECT – ' + ', '.join(errors[i]) if i in errors else 'OK'}" for i in df.index]
       log_pattern = ((cfg.meta or {}).get("naming") or {}).get("log")
       enc_log = enc_cfg.get("log_txt", "utf-8-sig")
       log_file_path = write_txt_log(cfg.log_dir, label, summary_lines, per_rec, pattern=log_pattern, encoding=enc_log)
       if log_file_path: log_step("G0. TXT log", True, str(log_file_path), args.quiet)

   # Reports na validatie
   val_report_paths: List[str] = []
   if getattr(args, "report", False) and ("validation" in stages):
       if args.report_format in ("md","both"):   val_report_paths.append(str(generate_report_md(valid_df.copy(), cfg, label, "validation")))
       if args.report_format in ("html","both"): val_report_paths.append(str(generate_report_html(valid_df.copy(), cfg, label, "validation")))
       reasons_csv = write_reject_reasons_csv(reject_df, cfg.log_dir, label, cfg)
       if reasons_csv: log_step("G1. Reject reasons CSV", True, str(reasons_csv), args.quiet)
       if val_report_paths: log_step("G2. Validation report", True, " / ".join(val_report_paths[-2:]), args.quiet)

   total, good, bad = len(df), len(valid_df), len(reject_df)
   _print("\n— Summary —", args.quiet)
   _print(f"Label   : {label}", args.quiet)
   _print(f"Rows    : total={total}, valid={good}, rejected={bad}", args.quiet)
   _print(f"Export  : {cfg.output_file}", args.quiet)
   _print(f"Rejects : {cfg.reject_file}", args.quiet)
   if log_file_path: _print(f"TXT log : {log_file_path}", args.quiet)
   if raw_report_paths:  _print("Report  : " + " | ".join(raw_report_paths), args.quiet)
   if post_report_paths: _print("Report  : " + " | ".join(post_report_paths), args.quiet)
   if val_report_paths:  _print("Report  : " + " | ".join(val_report_paths), args.quiet)
   return {"total": total, "valid": good, "rejected": bad}
