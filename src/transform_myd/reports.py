from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import pandas as pd
from .config import TransformConfig

def _column_profile_lines(df: pd.DataFrame, cfg: TransformConfig) -> List[str]:
   lines: List[str] = []
   cols = list(df.columns)
   ordered = [c for c in cfg.column_map.keys() if c in df.columns] + [c for c in cols if c not in cfg.column_map]
   for col in ordered:
       s = df[col]; total = len(s)
       non_null = int(s.notna().sum()); nulls = total - non_null
       empty = int(s.fillna("").astype(str).str.strip().eq("").sum())
       unique = int(s.nunique(dropna=True))
       lengths = s.fillna("").astype(str).str.len()
       min_len = int(lengths.min()) if total else 0; max_len = int(lengths.max()) if total else 0
       lines += [f"## {col}",
                 f"- non-null: **{non_null}** / {total}  |  null: **{nulls}**  |  empty (after strip): **{empty}**",
                 f"- unique: **{unique}**  |  len(min/max): **{min_len} / {max_len}**"]
       vc = s.astype(object).where(s.notna(), "NaN").value_counts(dropna=False).head(5)
       if len(vc):
           lines += ["", "| value | count |", "|---|---:|"]
           for v, cnt in vc.items():
               val = str(v); val = val if len(val) <= 80 else val[:77]+"..."
               lines.append(f"| `{val}` | {int(cnt)} |")
       lines.append("")
   return lines

def _report_filename(cfg: TransformConfig, label: str, stage: str, ext: str) -> Path:
   """Gebruik meta.naming.report of val op underscore-default; accepteer {ext} én legacy .EXT/.ext."""
   naming = (cfg.meta or {}).get("naming") or {}
   pattern = naming.get("report", "{datetime_hm_u}_{label_lower}_report_{stage}.{ext}")
   now = datetime.now()
   fmt = pattern.format(
       object=(cfg.meta or {}).get("object",""),
       variant=(cfg.meta or {}).get("variant",""),
       label=label, label_lower=label.lower(),
       date=now.strftime("%Y%m%d"),
       time=now.strftime("%H%M%S"),
       datetime=now.strftime("%Y%m%d_%H%M%S"),
       time_hm=now.strftime("%H%M"),
       datetime_hm=now.strftime("%Y%m%d %H%M"),
       datetime_hm_u=now.strftime("%Y%m%d_%H%M"),
       stage=stage, ext=ext, EXT=ext,
   )
   if ".EXT" in fmt: fmt = fmt.replace(".EXT", f".{ext}")
   if ".ext" in fmt: fmt = fmt.replace(".ext", f".{ext}")
   return cfg.log_dir / fmt

def _get_enc(cfg: TransformConfig, key: str, default: str) -> str:
   return ((cfg.meta or {}).get("encoding") or {}).get(key, default)

def _delta_lines_md(baseline: pd.DataFrame, current: pd.DataFrame) -> List[str]:
   lines: List[str] = ["", "### Delta t.o.v. RAW", "", "| column | changed | unchanged |", "|---|---:|---:|"]
   cols = [c for c in current.columns if c in baseline.columns]
   for c in cols:
       base = baseline[c].astype("string"); cur = current[c].astype("string")
       try: comp = (base == cur)
       except Exception: comp = (base.reset_index(drop=True) == cur.reset_index(drop=True))
       unchanged = int(comp.fillna(False).sum()); changed = int(len(cur) - unchanged)
       lines.append(f"| {c} | {changed} | {unchanged} |")
   lines.append("")
   return lines

def _delta_table_html(baseline: pd.DataFrame, current: pd.DataFrame) -> str:
   cols = [c for c in current.columns if c in baseline.columns]
   rows = []
   for c in cols:
       base = baseline[c].astype("string"); cur = current[c].astype("string")
       try: comp = (base == cur)
       except Exception: comp = (base.reset_index(drop=True) == cur.reset_index(drop=True))
       unchanged = int(comp.fillna(False).sum()); changed = int(len(cur) - unchanged)
       rows.append(f"<tr><td><code>{c}</code></td><td>{changed}</td><td>{unchanged}</td></tr>")
   if not rows: return ""
   return ("<h3>Delta t.o.v. RAW</h3>"
           "<table><tr><th>column</th><th>changed</th><th>unchanged</th></tr>"
           + "".join(rows) + "</table>")

def generate_report_md(df: pd.DataFrame, cfg: TransformConfig, label: str, stage: str, baseline: Optional[pd.DataFrame]=None) -> Path:
   lines: List[str] = [f"# Data Report – {label} ({stage})",
                       f"_Generated: {datetime.now().isoformat(timespec='seconds')}_", "",
                       f"Total rows: **{len(df)}**", ""]
   lines.extend(_column_profile_lines(df, cfg))
   if baseline is not None:
       lines.extend(_delta_lines_md(baseline, df))
   out_path = _report_filename(cfg, label, stage, "md")
   out_path.write_text("\n".join(lines), encoding=_get_enc(cfg, "reports_md", "utf-8-sig"))
   return out_path

def generate_report_html(df: pd.DataFrame, cfg: TransformConfig, label: str, stage: str, baseline: Optional[pd.DataFrame]=None) -> Path:
   def esc(x: str) -> str: return x.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
   css = ("<style>body{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:24px}"
          "h1{font-size:20px;margin-bottom:4px}h2{font-size:16px;margin-top:18px}"
          ".meta{color:#666;margin-bottom:12px}table{border-collapse:collapse;margin:6px 0 16px 0;width:640px}"
          "th,td{border:1px solid #ddd;padding:6px 8px;font-size:13px}th{background:#f6f6f6;text-align:left}"
          "code{background:#f3f3f3;padding:1px 4px;border-radius:4px}</style>")
   now = datetime.now()
   html = [f"<!doctype html><html><head><meta charset='utf-8'><title>{esc(label)} {esc(stage)}</title>{css}</head><body>",
           f"<h1>Data Report – {esc(label)} ({esc(stage)})</h1>",
           f"<div class='meta'>Generated: {esc(now.isoformat(timespec='seconds'))} &nbsp;|&nbsp; Rows: <b>{len(df)}</b></div>"]
   cols = list(df.columns)
   ordered = [c for c in cfg.column_map.keys() if c in df.columns] + [c for c in cols if c not in cfg.column_map]
   for col in ordered:
       s = df[col]; total = len(s); non_null = int(s.notna().sum()); nulls = total - non_null
       empty = int(s.fillna('').astype(str).str.strip().eq('').sum())
       unique = int(s.nunique(dropna=True)); lengths = s.fillna('').astype(str).str.len()
       min_len = int(lengths.min()) if total else 0; max_len = int(lengths.max()) if total else 0
       html.append(f"<h2>{esc(col)}</h2><table>")
       html.append("<tr><th>Metric</th><th>Value</th></tr>")
       html.append(f"<tr><td>non-null</td><td>{non_null} / {total}</td></tr>")
       html.append(f"<tr><td>null</td><td>{nulls}</td></tr>")
       html.append(f"<tr><td>empty (after strip)</td><td>{empty}</td></tr>")
       html.append(f"<tr><td>unique</td><td>{unique}</td></tr>")
       html.append(f"<tr><td>len(min/max)</td><td>{min_len} / {max_len}</td></tr>")
       vc = s.astype(object).where(s.notna(), "NaN").value_counts(dropna=False).head(5)
       if len(vc):
           html.append("<tr><th colspan='2'>top values</th></tr>")
           for v, cnt in vc.items():
               val = str(v); val = val if len(val) <= 120 else val[:117]+"..."
               html.append(f"<tr><td><code>{esc(val)}</code></td><td>{int(cnt)}</td></tr>")
       html.append("</table>")
   if baseline is not None:
       html.append(_delta_table_html(baseline, df))
   html.append("</body></html>")
   out_path = _report_filename(cfg, label, stage, "html")
   out_path.write_text("".join(html), encoding=_get_enc(cfg, "reports_html", "utf-8-sig"))
   return out_path

def write_reject_reasons_csv(reject_df: pd.DataFrame, log_dir: Path, label: str, cfg: TransformConfig):
   if "__errors" not in reject_df.columns or reject_df.empty: return None
   reasons = reject_df["__errors"].fillna("").astype(str).str.split("; ").explode()
   if reasons.empty: return None
   top = reasons.value_counts().rename_axis("reason").reset_index(name="count")
   out_path = log_dir / f"{datetime.now():%Y%m%d_%H%M}_{label.lower()}_reject_reasons.csv"
   enc = ((cfg.meta or {}).get("encoding") or {}).get("reports_csv", "utf-8-sig")
   top.to_csv(out_path, index=False, encoding=enc)
   return out_path
