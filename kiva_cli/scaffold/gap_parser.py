"""
Parse un GAP_REPORT SGR et extrait les métadonnées nécessaires
pour générer un scanner déclaratif YAML.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml, glob as glob_module, re


@dataclass
class GapMeta:
    gap_id:   str
    title:    str
    severity: str
    source:   str
    trit:     str
    action:   str
    family:   str = ""
    status:   str = "open"


# ── Inférence du CHECK_TYPE depuis les métadonnées du gap ────────────

CHECK_INFERENCE_RULES = [
    # (keyword, sub_keyword, check_type, params_hints)
    ("scanner",    "missing|absent",  "file_exists",   {"path": "{argus_root}/scanners/declared/{slug}_health.yaml"}),
    ("config",     "manqu|absent",    "composite",     {}),
    ("rapport|report", "perime|stale", "file_age",     {"max_age_hours": 26}),
    ("test|pytest", "",               "command",       {"cmd": "cd {root} && python -m pytest -q --tb=no"}),
    ("enregistr",  "known_repo",      "yaml_query",    {"query": "P0_CONSTITUTIONAL[?name == '{source}']", "expect_empty": False}),
    ("worker",     "",                "key_present",   {"key": "workers", "min_value": 1}),
    ("route",      "",                "yaml_query",    {"query": "routes", "expect_empty": False}),
    ("cron",       "",                "key_present",   {"key": "schedule"}),
]


def infer_check_type(gap: GapMeta) -> tuple:
    text = "{} {}".format(gap.title, gap.action).lower()
    for keyword, sub_keyword, check_type, hints in CHECK_INFERENCE_RULES:
        if keyword in text:
            if not sub_keyword or re.search(sub_keyword, text):
                return check_type, hints
    return "file_exists", {"path": "{root}/TODO_path_to_check"}


def _slugify(name: str) -> str:
    return name.lower().replace("-", "_").replace(" ", "_")


def parse_gap(report_path: Path, gap_id: str) -> Optional[GapMeta]:
    report = yaml.safe_load(report_path.read_text(encoding="utf-8"))
    for priority_gaps in report.get("by_priority", {}).values():
        for gap in priority_gaps:
            if isinstance(gap, dict) and gap.get("id") == gap_id:
                return GapMeta(
                    gap_id=gap["id"],
                    title=gap.get("title", ""),
                    severity=gap.get("severity", "P2"),
                    source=gap.get("source", ""),
                    trit=gap.get("trit", "TritObserve"),
                    action=gap.get("action", ""),
                    family=gap.get("family", ""),
                    status=gap.get("status", "open"),
                )
    return None


def find_latest_report(reports_root: Path) -> Optional[Path]:
    matches = sorted(
        glob_module.glob(str(reports_root / "sgr" / "GAP_REPORT-*.yaml")),
        key=lambda x: Path(x).stat().st_mtime
    )
    return Path(matches[-1]) if matches else None
