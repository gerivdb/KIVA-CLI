"""
kiva scaffold scanner — genere un scanner declaratif YAML depuis un gap SGR.

Usage:
  kiva scaffold scanner --gap-id SGR-KIVA-001
  kiva scaffold scanner --gap-id SGR-KIVA-001 --from-report path/to/GAP_REPORT.yaml
  kiva scaffold scanner --list-gaps --from-report path/to/GAP_REPORT.yaml
  kiva scaffold scanner --all-p1 --from-report path/to/GAP_REPORT.yaml
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
from ..scaffold.gap_parser import parse_gap, find_latest_report, GapMeta
from ..scaffold.scanner_template import generate_from_gap_id


DEFAULT_REPORT_ROOT = Path("D:/DO/WEB/TOOLS/reports")
DEFAULT_OUTPUT_DIR = Path("D:/DO/WEB/TOOLS/L3-CITIZENS/ARGUS/scanners/declared")


def cmd_scaffold_scanner(args: argparse.Namespace) -> int:
    # Resoudre le chemin du rapport
    if args.from_report:
        report_path = Path(args.from_report)
    else:
        report_path = find_latest_report(DEFAULT_REPORT_ROOT)
        if not report_path:
            print("ERREUR: Aucun GAP_REPORT trouve. Utiliser --from-report <path>")
            return 1
    print("Rapport : {}".format(report_path.name))

    output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Mode --list-gaps
    if args.list_gaps:
        import yaml
        report = yaml.safe_load(report_path.read_text(encoding="utf-8"))
        print("\n=== Gaps disponibles ===")
        for prio in ("P1", "P2", "P3"):
            gaps = report.get("by_priority", {}).get(prio, [])
            for g in gaps:
                if isinstance(g, dict):
                    status_icon = "OK" if g.get("status") in ("closed", "exception") else "OPEN"
                    print("  [{}] {} {} — {}".format(status_icon, prio, g.get("id", "?"),
                                                    g.get("title", "")[:60]))
        return 0

    # Mode --all-p1
    if args.all_p1:
        import yaml
        report = yaml.safe_load(report_path.read_text(encoding="utf-8"))
        p1_open = [
            g for g in report.get("by_priority", {}).get("P1", [])
            if isinstance(g, dict) and g.get("status") not in ("closed", "exception", "triaged")
        ]
        if not p1_open:
            print("Aucun gap P1 ouvert — rien a scaffolder")
            return 0
        print("Scaffolding {} gap(s) P1...".format(len(p1_open)))
        created = []
        for g in p1_open:
            try:
                out_path, _ = generate_from_gap_id(g["id"], report_path, output_dir)
                created.append(out_path)
                print("  OK {} → {}".format(g["id"], out_path.name))
            except Exception as e:
                print("  ERREUR {} — {}".format(g["id"], e))
        print("\n{} scanner(s) cree(s) dans {}".format(len(created), output_dir))
        print("Verifier les lignes TODO avant deploiement")
        return 0

    # Mode --gap-id
    if not args.gap_id:
        print("ERREUR: --gap-id requis (ou --list-gaps / --all-p1)")
        return 1

    try:
        out_path, content = generate_from_gap_id(args.gap_id, report_path, output_dir)
        print("\nScanner genere : {}".format(out_path))
        print("\n{}\n".format(content))
        print("Prochaines etapes :")
        print("  1. Verifier les lignes TODO dans {}".format(out_path.name))
        print("  2. python -m engine.declarative_runner {} [key=value ...]".format(out_path))
        return 0
    except ValueError as e:
        print("ERREUR: {}".format(e))
        return 1


def add_subparser(subparsers):
    p = subparsers.add_parser("scanner", help="Generer un scanner declaratif depuis un gap SGR")
    p.add_argument("--gap-id", help="ID du gap SGR (ex: SGR-KIVA-001)")
    p.add_argument("--from-report", help="Chemin vers GAP_REPORT.yaml")
    p.add_argument("--output-dir", help="Dossier de sortie (defaut: scanners/declared)")
    p.add_argument("--list-gaps", action="store_true", help="Lister tous les gaps disponibles")
    p.add_argument("--all-p1", action="store_true", help="Scaffolder tous les P1 ouverts")
    p.set_defaults(func=cmd_scaffold_scanner)
