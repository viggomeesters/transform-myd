from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import List, Optional

def _print(msg: str, quiet: bool=False):
    if not quiet: print(msg)

def log_step(name: str, ok: bool, info: str="", quiet: bool=False):
    symbol = "✓" if ok else "✗"
    _print(f"[{symbol}] {name}{f' – {info}' if info else ''}", quiet)

def write_txt_log(log_dir: Path, label: str, summary_lines: List[str], per_record_lines: List[str], pattern: str | None = None) -> Optional[Path]:
    """Schrijf legacy TXT-log met uniform default-patroon; respecteer meta.naming.log als meegegeven."""
    now = datetime.now()
    label_lower = label.lower()
    if not pattern:
        pattern = "{datetime_hm_u}_{label_lower}_log.txt"
    fname = pattern.format(
        datetime_hm_u=now.strftime("%Y%m%d_%H%M"),
        datetime_hm=now.strftime("%Y%m%d %H%M"),
        label_lower=label_lower,
        label=label,
    )
    log_file = log_dir / fname
    with log_file.open("w", encoding="utf-8") as fp:
        fp.write("\n".join(summary_lines + ["", "# Per-record log"] + per_record_lines))
    return log_file
