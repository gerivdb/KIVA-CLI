#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSS-v3 Pre-Commit Guard
Valide la presence et la conformite de ROADMAPS/vector.yaml
IntentHash: 0XRSS_V3_PRE_COMMIT_GUARD_20260625
"""

import os
import sys
import yaml
from datetime import date, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
ROADMAPS_DIR = REPO_ROOT / "ROADMAPS"
VECTOR_FILE = ROADMAPS_DIR / "vector.yaml"
MILESTONES_FILE = ROADMAPS_DIR / "milestones.yaml"
DEPENDENCIES_FILE = ROADMAPS_DIR / "dependencies.yaml"
BLOCKERS_FILE = ROADMAPS_DIR / "blockers.yaml"
HISTORY_FILE = ROADMAPS_DIR / "history.yaml"

REQUIRED_FILES = [VECTOR_FILE, MILESTONES_FILE, DEPENDENCIES_FILE, BLOCKERS_FILE, HISTORY_FILE]

HORIZONS_VALID = {"30d", "90d", "1a", "indefini"}
SEVERITIES_VALID = {"CRITICAL", "HIGH", "MODERATE", "LOW"}
MILESTONE_STATUSES = {"not_started", "in_progress", "done", "blocked"}
HISTORY_ACTIONS = {"creation", "amendment", "milestone_reached", "blocker_resolved", "pivot"}


def check_file_exists():
    """Verifie que tous les fichiers obligatoires existent."""
    missing = [str(f.relative_to(REPO_ROOT)) for f in REQUIRED_FILES if not f.exists()]
    if missing:
        print(f"[RSS-v3] Fichiers manquants : {', '.join(missing)}")
        return False
    return True


def check_vector():
    """Valide le vector.yaml."""
    try:
        with open(VECTOR_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"[RSS-v3] vector.yaml invalide : {e}")
        return False

    if not isinstance(data, dict):
        print("[RSS-v3] vector.yaml : racine doit etre un mapping")
        return False

    v = data.get("vector")
    if not v:
        print("[RSS-v3] vector.yaml : champ 'vector' manquant")
        return False

    # Champs requis
    for field in ["horizon", "direction", "velocity_observed", "mass", "last_amended"]:
        if field not in v:
            print(f"[RSS-v3] vector.yaml : champ 'vector.{field}' manquant")
            return False

    # Validations
    if v["horizon"] not in HORIZONS_VALID:
        print(f"[RSS-v3] vector.yaml : horizon '{v['horizon']}' invalide (doit etre dans {HORIZONS_VALID})")
        return False

    if not isinstance(v["direction"], list) or len(v["direction"]) == 0:
        print("[RSS-v3] vector.yaml : direction doit etre une liste non vide")
        return False

    if not (0.0 <= v["velocity_observed"] <= 1.0):
        print(f"[RSS-v3] vector.yaml : velocity_observed {v['velocity_observed']} hors range [0.0, 1.0]")
        return False

    if not (0.0 <= v["mass"] <= 1.0):
        print(f"[RSS-v3] vector.yaml : mass {v['mass']} hors range [0.0, 1.0]")
        return False

    # Taille du fichier < 2KB
    if VECTOR_FILE.stat().st_size > 2048:
        print(f"[RSS-v3] vector.yaml : fichier trop gros ({VECTOR_FILE.stat().st_size} bytes > 2048)")
        return False

    return True


def check_milestones():
    """Valide le milestones.yaml."""
    try:
        with open(MILESTONES_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"[RSS-v3] milestones.yaml invalide : {e}")
        return False

    milestones = data.get("milestones", [])
    if not milestones:
        print("[RSS-v3] milestones.yaml : aucun jalon defini")
        return False

    for m in milestones:
        for field in ["id", "name", "owner", "status", "target_date"]:
            if field not in m:
                print(f"[RSS-v3] milestones.yaml : jalon sans champ '{field}'")
                return False
        if m["status"] not in MILESTONE_STATUSES:
            print(f"[RSS-v3] milestones.yaml : statut '{m['status']}' invalide")
            return False

    return True


def check_blockers():
    """Valide le blockers.yaml."""
    try:
        with open(BLOCKERS_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"[RSS-v3] blockers.yaml invalide : {e}")
        return False

    blockers = data.get("blockers", [])
    for b in blockers:
        for field in ["id", "severity", "description", "impact", "resolution", "owner", "target_resolution"]:
            if field not in b:
                print(f"[RSS-v3] blockers.yaml : bloqueur sans champ '{field}'")
                return False
        if b["severity"] not in SEVERITIES_VALID:
            print(f"[RSS-v3] blockers.yaml : severite '{b['severity']}' invalide")
            return False

    return True


def check_history():
    """Valide le history.yaml (v1: entries[], v2: amendments[])."""
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"[RSS-v3] history.yaml invalide : {e}")
        return False

    # v2 schema: amendments[]
    amendments = data.get("amendments", [])
    if amendments:
        for a in amendments:
            for field in ["date", "event", "description"]:
                if field not in a:
                    print(f"[RSS-v3] history.yaml : amendment sans champ '{field}'")
                    return False
        return True

    # v1 schema: entries[]
    entries = data.get("entries", [])
    if not entries:
        print("[RSS-v3] history.yaml : aucune entree dans l'historique")
        return False

    for e in entries:
        for field in ["date", "action", "description", "actor"]:
            if field not in e:
                print(f"[RSS-v3] history.yaml : entree sans champ '{field}'")
                return False
        if e["action"] not in HISTORY_ACTIONS:
            print(f"[RSS-v3] history.yaml : action '{e['action']}' invalide")
            return False

    return True


def main():
    print("=== RSS-v3 Pre-Commit Guard ===")

    all_ok = True

    if not check_file_exists():
        all_ok = False

    if not check_vector():
        all_ok = False

    if not check_milestones():
        all_ok = False

    if not check_blockers():
        all_ok = False

    if not check_history():
        all_ok = False

    if all_ok:
        print("[RSS-v3] OK — ROADMAPS/ conforme")
        return 0
    else:
        print("[RSS-v3] FAILED — Corriger les erreurs ci-dessus")
        return 1


if __name__ == "__main__":
    sys.exit(main())
