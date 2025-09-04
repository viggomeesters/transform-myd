from __future__ import annotations
import argparse
from pathlib import Path
from .pipeline import run_pipeline
from .linting import lint_config, lint_all
from .runlist import run_from_runlist
from .scaffold import scaffold

def parse_args():
   # ASCII-only description (Windows consoles met cp1252)
   p = argparse.ArgumentParser(description="Transform EXTRACT -> SAP Migrate Your Data CSV via YAML.")
   # PIPELINE
   p.add_argument("--object", "-o", dest="object_name", default=None,
                  help="Object/familie, bv. M140 of M140_BNKA (autosplit).")
   p.add_argument("--variant", "-v", dest="variant_name", default=None,
                  help="Variant binnen object, bv. BNKA.")
   p.add_argument("--config", "-c", dest="config_dir", default="config",
                  help="Config root (default: ./config)")
   p.add_argument("--input", "-i", dest="input_file", default=None,
                  help="Override enkel input pad (als meta.sources niet wordt gebruikt).")
   p.add_argument("--output", "-O", dest="output_file", default=None,
                  help="Override output CSV")
   p.add_argument("--rejects", "-r", dest="reject_file", default=None,
                  help="Override rejects CSV")
   p.add_argument("--logdir", dest="log_dir", default="logs",
                  help="Log directory (default: ./logs)")
   p.add_argument("--sample", type=int, default=None,
                  help="Alleen de eerste N rijen verwerken (na load/join).")
   p.add_argument("--report", action="store_true",
                  help="Genereer rapport(en).")
   p.add_argument("--report-format", choices=["md","html","both"], default="html",
                  help="Formaat van reports (default: html).")
   p.add_argument("--reports", dest="reports", default=None,
                  help="Stages comma-separated: raw,post,validation (default: raw,validation).")
   # SCAFFOLD
   p.add_argument("--scaffold", dest="scaffold_object", default=None,
                  help="Maak boilerplate config voor <OBJECT> of <OBJECT_VARIANT>.")
   p.add_argument("--from-excel", dest="from_excel", default=None,
                  help="Neem headers uit Excel voor column_map.yaml")
   p.add_argument("--force", action="store_true",
                  help="Overschrijf bestaande files bij scaffold.")
   p.add_argument("--dry-run", action="store_true",
                  help="Toon scaffold acties zonder te schrijven.")
   # RUNLIST & LINT
   p.add_argument("--runlist", dest="runlist_path", default=None,
                  help="YAML met batch runs (zie voorbeeld).")
   p.add_argument("--lint", action="store_true",
                  help="Lint de geselecteerde config (object/variant of runlist).")
   p.add_argument("--lint-all", action="store_true",
                  help="Lint alle objecten/varianten onder config/.")
   p.add_argument("--strict", action="store_true",
                  help="Warnings behandelen als errors (exit 1).")
   # TRACE & LOGGING
   p.add_argument("--trace-config", action="store_true",
                  help="Toon merge-lagen en gevonden YAML-bestanden.")
   p.add_argument("--no-txt-log", action="store_true",
                  help="Schrijf geen legacy TXT per-record log.")
   p.add_argument("--quiet", action="store_true",
                  help="Minimaliseer console-uitvoer (kernmeldingen + Summary).")
   p.add_argument("--classic-summary", action="store_true",
                  help="Print ook het oude blok-achtige summary overzicht (optioneel).")
   # CI & EXIT
   p.add_argument("--ci", action="store_true",
                  help="CI preset: quiet + no-txt-log + report(html) + strict + fail-on-... .")
   p.add_argument("--fail-on-rejects", action="store_true",
                  help="Exit met code 1 als er rejects zijn.")
   p.add_argument("--fail-on-zero-valid", action="store_true",
                  help="Exit met code 1 als er 0 geldige rijen zijn.")
   # LINEAGE
   p.add_argument("--no-lineage", action="store_true",
                  help="Voeg geen lineage-kolommen toe.")
   p.add_argument("--keep-lineage", action="store_true",
                  help="Behoud lineage-kolommen in de export CSV.")
   # ENCODING overrides
   p.add_argument("--encoding-out", dest="encoding_out", default=None,
                  help="Encoding voor export CSV (override, bv. utf-8-sig of cp1252).")
   p.add_argument("--encoding-rejects", dest="encoding_rejects", default=None,
                  help="Encoding voor rejects CSV (override).")
   return p.parse_args()

def main():
   args = parse_args()
   # CI preset
   if args.ci:
       args.quiet = True
       args.no_txt_log = True
       args.report = True
       args.report_format = "html"
       args.strict = True
       args.fail_on_rejects = True
       args.fail_on_zero_valid = True
   # Scaffold?
   if args.scaffold_object:
       scaffold(Path(args.config_dir),
                args.scaffold_object,
                Path(args.from_excel) if args.from_excel else None,
                force=args.force, dry_run=args.dry_run)
       return
   # Runlist?
   if args.runlist_path:
       if args.lint:
           code = run_from_runlist(Path(args.config_dir), Path(args.runlist_path),
                                   lint_only=True, strict=args.strict, trace=args.trace_config,
                                   global_sample=args.sample, global_report=args.report,
                                   global_report_format=args.report_format,
                                   quiet=args.quiet, no_txt_log=args.no_txt_log,
                                   classic_summary=args.classic_summary,
                                   fail_on_rejects=args.fail_on_rejects,
                                   fail_on_zero_valid=args.fail_on_zero_valid)
           raise SystemExit(code)
       else:
           code = run_from_runlist(Path(args.config_dir), Path(args.runlist_path),
                                   lint_only=False, strict=args.strict, trace=args.trace_config,
                                   global_sample=args.sample, global_report=args.report,
                                   global_report_format=args.report_format,
                                   quiet=args.quiet, no_txt_log=args.no_txt_log,
                                   classic_summary=args.classic_summary,
                                   fail_on_rejects=args.fail_on_rejects,
                                   fail_on_zero_valid=args.fail_on_zero_valid)
           raise SystemExit(code)
   # Lint?
   if args.lint_all:
       raise SystemExit(lint_all(Path(args.config_dir), strict=args.strict))
   if args.lint:
       raise SystemExit(lint_config(args))
   # Single run
   res = run_pipeline(args)
   exit_code = 0
   if args.fail_on_rejects and res.get("rejected", 0) > 0:
       exit_code = 1
   if args.fail_on_zero_valid and res.get("valid", 0) == 0:
       exit_code = 1
   if exit_code:
       raise SystemExit(exit_code)

if __name__ == "__main__":
   main()
