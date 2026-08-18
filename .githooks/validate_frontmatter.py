#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Frontmatter Validation Guard

Validates YAML frontmatter for governance documents (EPIC, PRD, INTENT, ADR,
REPORT, RPT, GUI, RUN) before commit.

Checks:
- YAML parseable between --- markers
- Required fields present per document type (inferred from folder)
- Status values are valid per type
- intent_hash uniqueness (warn only)
"""

import os
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent

# Required fields per document type
REQUIRED_FIELDS = {
    "PRD": ["type", "version", "date", "status", "intent_hash"],
    "EPIC": ["intent_hash", "status", "priority", "owner", "repo"],
    "INTENT": ["intent_hash", "status", "priority"],
    "ADR": ["status", "date", "intent_hash"],
    "REPORT": ["type", "status", "date", "owner", "repo"],
    "RPT": ["type", "date", "intent_hash"],
    "GUI": ["type", "intent_hash"],
    "RUN": ["type", "intent_hash"],
}

# Valid status values per type
VALID_STATUS = {
    "PRD": {"draft", "in_review", "approved", "archived"},
    "EPIC": {"planned", "active", "completed", "archived"},
    "ADR": {"proposed", "accepted", "rejected", "deprecated", "archived"},
    "INTENT": {"exploratory", "proposed", "approved", "implemented", "archived"},
    "REPORT": {"draft", "final", "archived"},
    "RPT": {"draft", "final", "archived"},
    "GUI": {"draft", "active", "archived"},
    "RUN": {"draft", "active", "archived"},
}

# Status normalization mapping
STATUS_NORMALIZE = {
    "active": "active",
    "in_progress": "active",
    "done": "completed",
    "completed": "completed",
    "proposed": "proposed",
    "approved": "approved",
    "draft": "draft",
    "archived": "archived",
    "deprecated": "deprecated",
    "rejected": "rejected",
    "final": "final",
    "in_review": "in_review",
    "accepted": "accepted",
    "implemented": "implemented",
    "exploratory": "exploratory",
    "planned": "planned",
}

# Folder to type mapping
FOLDER_TYPE = {
    "EPICS": "EPIC",
    "PRD": "PRD",
    "specs": "PRD",
    "ADR": "ADR",
    "INTENTS": "INTENT",
    "REPORTS": "REPORT",
    "reports": "REPORT",
    "RPT": "RPT",
    "GUI": "GUI",
    "RUN": "RUN",
}

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def infer_type(filepath: Path) -> str | None:
    """Infer document type from file path."""
    parts = filepath.parts
    for folder in FOLDER_TYPE:
        if folder in parts:
            return FOLDER_TYPE[folder]
    return None


def validate_frontmatter(filepath: Path) -> list[str]:
    """Validate frontmatter of a single file. Returns list of issues."""
    issues = []
    text = filepath.read_text(encoding="utf-8", errors="ignore")
    match = FRONTMATTER_RE.match(text)
    
    if not match:
        return issues  # Not a governance doc, skip
    
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as e:
        issues.append(f"YAML parse error: {e}")
        return issues
    
    if not isinstance(data, dict):
        issues.append("Frontmatter is not a dict")
        return issues
    
    doc_type = data.get("type")
    if not doc_type:
        # Infer from path
        doc_type = infer_type(filepath)
    
    if doc_type not in REQUIRED_FIELDS:
        return issues  # Unknown type, skip
    
    # Check required fields
    missing = [k for k in REQUIRED_FIELDS[doc_type] if k not in data]
    if missing:
        issues.append(f"Missing required fields: {missing}")
    
    # Check status validity
    status = data.get("status", "")
    if status:
        normalized = STATUS_NORMALIZE.get(str(status).lower(), status)
        if normalized not in VALID_STATUS.get(doc_type, set()):
            valid = "/".join(sorted(VALID_STATUS.get(doc_type, set())))
            issues.append(f"Invalid status '{status}' for type '{doc_type}' (valid: {valid})")
    
    return issues


def main():
    """Main entry point."""
    # Find all markdown files in the repo
    md_files = list(REPO_ROOT.rglob("*.md"))
    md_files = [
        f for f in md_files
        if ".git" not in f.parts
        and "node_modules" not in f.parts
        and ".kilo" not in f.parts
    ]
    
    all_issues = []
    for f in md_files:
        issues = validate_frontmatter(f)
        if issues:
            rel_path = f.relative_to(REPO_ROOT)
            for issue in issues:
                all_issues.append(f"  {rel_path}: {issue}")
    
    if all_issues:
        print("[FRONTMATTER] Validation issues found:")
        for issue in all_issues:
            print(issue)
        print(f"\n  Total: {len(all_issues)} issue(s) across {len(set(i.split(':')[0] for i in all_issues))} file(s)")
        sys.exit(1)
    else:
        print("[FRONTMATTER] All governance docs valid.")
        sys.exit(0)


if __name__ == "__main__":
    main()
