from __future__ import annotations
from argparse import Namespace
from pathlib import Path
from typing import Optional
import yaml

from .pipeline import run_pipeline


def run_from_runlist(config_root: Path, runlist_path: Path, lint_only: bool = False, strict: bool = False,
                     trace: bool = False, global_sample: Optional[int] = None, global_report: bool = False,
                     global_report_format: str = "md", quiet: bool = False, no_txt_log: bool = False,
                     classic_summary: bool = False, fail_on_rejects: bool = False, fail_on_zero_valid: bool = False) -> int:
    data = yaml.safe_load(runlist_path.read_text(encoding="utf-8"))
    jobs = data.get("jobs", [])
    exit_code = 0
    for j in jobs:
        job_sample = j.get("sample", None)
        job_report = j.get("report", None)
        job_report_format = j.get("report_format", None)
        job_quiet = j.get("quiet", None)

        ns = Namespace(
            object_name=j.get("object"),
            variant_name=j.get("variant"),
            config_dir=str(config_root),
            input_file=j.get("input_file"),
            output_file=j.get("output_file"),
            reject_file=j.get("reject_file"),
            log_dir=j.get("log_dir", "logs"),
            sample=job_sample if job_sample is not None else global_sample,
            report=job_report if job_report is not None else global_report,
            report_format=job_report_format if job_report_format is not None else global_report_format,
            scaffold_object=None, from_excel=None, force=False, dry_run=False,
            runlist_path=None, lint=lint_only, lint_all=False, strict=strict,
            trace_config=trace, no_txt_log=no_txt_log,
            quiet=job_quiet if job_quiet is not None else quiet,
            classic_summary=classic_summary,
            ci=False, fail_on_rejects=fail_on_rejects, fail_on_zero_valid=fail_on_zero_valid,
        )
        label = f"{j.get('object')}_{j.get('variant')}" if j.get("variant") else j.get("object")
        if lint_only:
            print(f"\n=== LINT {label} ===")
            from .linting import lint_config
            rc = lint_config(ns)
            exit_code = exit_code or rc
        else:
            print(f"\n=== RUN {label} ===")
            res = run_pipeline(ns)
            if fail_on_rejects and res["rejected"] > 0:
                exit_code = 1
            if fail_on_zero_valid and res["valid"] == 0:
                exit_code = 1
    return exit_code

