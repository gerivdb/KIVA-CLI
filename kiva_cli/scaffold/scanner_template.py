"""
Génère un scanner YAML déclaratif depuis un GapMeta.
"""
from __future__ import annotations
from pathlib import Path
from .gap_parser import GapMeta, infer_check_type, _slugify
import yaml


def _build_check(gap: GapMeta, idx: int = 1) -> dict:
    check_type, hints = infer_check_type(gap)
    slug = _slugify(gap.source)
    check_id = "{}-{:03d}".format(slug.upper()[:3], idx)

    base = {
        "id": check_id,
        "severity": gap.severity,
        "title": gap.title,
        "type": check_type,
        "remediation": gap.action,
    }

    resolved_hints = {}
    for k, v in hints.items():
        if isinstance(v, str):
            v = v.replace("{source}", gap.source)
            v = v.replace("{slug}", slug)
        resolved_hints[k] = v

    if check_type == "composite":
        base["operator"] = "AND"
        base["checks"] = [
            {"type": "file_exists", "path": "{{root}}/config/{}.yaml".format(slug),
             "# TODO": "Ajuster le chemin"},
            {"type": "key_present", "file": "{{root}}/config/{}.yaml".format(slug),
             "key": "# TODO: cle a verifier"},
        ]
    else:
        base.update(resolved_hints)

    return base


def generate_scanner_yaml(gap: GapMeta, output_path: Path) -> str:
    slug = _slugify(gap.source)
    check_main = _build_check(gap, idx=1)

    scanner = {
        "scanner_id": "{}_health".format(slug),
        "citizen": gap.source,
        "trit": gap.trit,
        "version": "1.0.0",
        "gap_origin": gap.gap_id,
        "checks": [check_main],
    }

    # Ajouter un check monitoring si la famille le suggere
    if any(kw in gap.family.lower() for kw in ("monitor", "sync", "pipeline", "health")):
        scanner["checks"].append({
            "id": "{}-002".format(slug.upper()[:3]),
            "severity": "P2",
            "title": "Rapport {} recent (< 48h)".format(gap.source),
            "type": "file_age",
            "glob": "{{reports_root}}/{}/report-*.yaml".format(slug),
            "max_age_hours": 48,
            "remediation": "Relancer le pipeline {}".format(gap.source),
            "# TODO": "Ajuster le glob selon le chemin reel des rapports",
        })

    content = yaml.dump(scanner, allow_unicode=True, sort_keys=False,
                        default_flow_style=False, width=100)

    header = """\
# ─────────────────────────────────────────────────────────────────
# Scanner ARGUS — {}
# Genere depuis gap SGR : {}
# Severity : {} | Trit : {}
# ─────────────────────────────────────────────────────────────────
# ⚠️  Verifier les lignes marquees "# TODO" avant deploiement
# ─────────────────────────────────────────────────────────────────
""".format(gap.source, gap.gap_id, gap.severity, gap.trit)

    final = header + content
    output_path.write_text(final, encoding="utf-8")
    return final


def generate_from_gap_id(gap_id: str, report_path: Path, output_dir: Path) -> tuple:
    from .gap_parser import parse_gap
    gap = parse_gap(report_path, gap_id)
    if not gap:
        raise ValueError("Gap '{}' introuvable dans {}".format(gap_id, report_path))
    slug = _slugify(gap.source)
    output_path = output_dir / "{}_health.yaml".format(slug)
    content = generate_scanner_yaml(gap, output_path)
    return output_path, content
