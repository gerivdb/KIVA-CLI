#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selina_triadic_sync.py — Synchronisation triadique TOPOS/VERSES/ONTOLOGY.

SELINA = Symbolic Ecosystem Liaison & Intelligence Network Agent.
Synchronisation complète des trois strates :
- TOPOS : registre canonique des repos
- VERSES : concepts et versets de gouvernance
- ONTOLOGY : concepts ontologiques

Triadic Sync = TOPOS → VERSES → ONTOLOGY → TOPOS (boucle de cohérence)

Usage:
    python scripts/selina_triadic_sync.py --scan           # Scanner les écarts
    python scripts/selina_triadic_sync.py --sync           # Synchroniser
    python scripts/selina_triadic_sync.py --reconcile      # Réconcilier les gaps
    python scripts/selina_triadic_sync.py --report         # Rapport de cohérence

IntentHash: 0xSELINA_TRIADIC_SYNC_20260707
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Paths
REPO_ROOT = Path("D:/DO/WEB/TOOLS/L4-TOOLS/REPO-STANDARDS")
TOPOS_DIR = REPO_ROOT / "TOPOS"
VERSES_DIR = REPO_ROOT / "VERSES"
ONTOLOGY_DIR = Path("D:/DO/WEB/ONTOLOGY")
GOV_HUB = Path("D:/DO/WEB/TOOLS/L0-CANON/GOVERNANCE-HUB")


@dataclass
class SyncResult:
    """Résultat d'une opération de synchronisation."""
    source: str
    target: str
    files_synced: int = 0
    gaps_found: List[str] = None
    conflicts: List[str] = None
    status: str = "pending"
    timestamp: str = ""
    
    def __post_init__(self):
        if self.gaps_found is None:
            self.gaps_found = []
        if self.conflicts is None:
            self.conflicts = []
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class SelinaTriadicSync:
    """Synchronisation triadique TOPOS/VERSES/ONTOLOGY."""

    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or REPO_ROOT
        self.topos_registry = {}
        self.verses_concepts = {}
        self.ontology_terms = {}
        self._load_registries()

    def _load_registries(self) -> None:
        """Charge les trois registres."""
        # TOPOS registry/repos.json
        registries_file = GOV_HUB / "registry" / "repos.json"
        if registries_file.exists():
            self.topos_registry = json.loads(registries_file.read_text(encoding='utf-8'))
        
        # VERSES concepts
        if VERSES_DIR.exists():
            for concept_file in VERSES_DIR.rglob("*.md"):
                content = concept_file.read_text(encoding='utf-8')
                self.verses_concepts[concept_file.stem] = {
                    "path": str(concept_file),
                    "hash": hashlib.md5(content.encode()).hexdigest()[:8]
                }
        
        # ONTOLOGY concepts
        if ONTOLOGY_DIR.exists():
            for concept_file in ONTOLOGY_DIR.rglob("*.md"):
                content = concept_file.read_text(encoding='utf-8')
                self.ontology_terms[concept_file.stem] = {
                    "path": str(concept_file),
                    "hash": hashlib.md5(content.encode()).hexdigest()[:8]
                }

    def scan_gaps(self) -> Dict[str, List[str]]:
        """Scanne les gaps entre les trois strates."""
        gaps = {
            "topos_missing_verses": [],
            "verses_missing_ontology": [],
            "ontology_missing_topos": [],
            "hash_mismatches": []
        }
        
        # Vérifier les concepts TOPOS manquants dans VERSES
        for concept_name in self.topos_registry.get("concepts", {}).keys():
            if concept_name not in self.verses_concepts:
                gaps["topos_missing_verses"].append(concept_name)
        
        # Vérifier les concepts VERSES manquants dans ONTOLOGY
        for concept_name in self.verses_concepts.keys():
            if concept_name not in self.ontology_terms:
                gaps["verses_missing_ontology"].append(concept_name)
        
        # Vérifier les concepts ONTOLOGY manquants dans TOPOS
        for concept_name in self.ontology_terms.keys():
            if concept_name not in self.topos_registry.get("concepts", {}):
                gaps["ontology_missing_topos"].append(concept_name)
        
        return gaps

    def sync_topos_to_verses(self) -> SyncResult:
        """Synchronise TOPOS → VERSES."""
        result = SyncResult(
            source="TOPOS",
            target="VERSES",
            status="pending"
        )
        
        gaps = self.scan_gaps()
        result.gaps_found = gaps["topos_missing_verses"]
        
        # Créer les concepts manquants dans VERSES
        for concept_name in gaps["topos_missing_verses"]:
            concept_path = VERSES_DIR / f"{concept_name}.md"
            concept_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Générer le contenu du concept
            concept_data = self.topos_registry.get("concepts", {}).get(concept_name, {})
            content = f"""# {concept_name}

## Définition
{concept_data.get('definition', concept_name)}

## Contexte TOPOS
{concept_data.get('context', 'Concept défini dans TOPOS')}

## Statut
{concept_data.get('status', 'draft')}

---
*Généré par Selina Triadic Sync: {datetime.now().isoformat()}*
"""
            concept_path.write_text(content, encoding='utf-8')
            result.files_synced += 1
        
        result.status = "synced" if result.files_synced > 0 else "in_sync"
        return result

    def sync_verses_to_ontology(self) -> SyncResult:
        """Synchronise VERSES → ONTOLOGY."""
        result = SyncResult(
            source="VERSES",
            target="ONTOLOGY",
            status="pending"
        )
        
        gaps = self.scan_gaps()
        result.gaps_found = gaps["verses_missing_ontology"]
        
        # Créer les concepts manquants dans ONTOLOGY
        for concept_name in gaps["verses_missing_ontology"]:
            concept_path = ONTOLOGY_DIR / "concepts" / f"{concept_name}.md"
            concept_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Lire le contenu VERSES
            verses_path = VERSES_DIR / f"{concept_name}.md"
            content = verses_path.read_text(encoding='utf-8') if verses_path.exists() else f"# {concept_name}\n"
            
            content += f"""

## Métadonnées ONTOLOGY
- **Source**: VERSES
- **Status**: draft
- **Last sync**: {datetime.now().isoformat()}

---
*Synchronisé par Selina Triadic Sync*
"""
            concept_path.write_text(content, encoding='utf-8')
            result.files_synced += 1
        
        result.status = "synced" if result.files_synced > 0 else "in_sync"
        return result

    def sync_ontology_to_topos(self) -> SyncResult:
        """Synchronise ONTOLOGY → TOPOS."""
        result = SyncResult(
            source="ONTOLOGY",
            target="TOPOS",
            status="pending"
        )
        
        gaps = self.scan_gaps()
        result.gaps_found = gaps["ontology_missing_topos"]
        
        # Mettre à jour le registre TOPOS
        for concept_name in gaps["ontology_missing_topos"]:
            self.topos_registry.setdefault("concepts", {})[concept_name] = {
                "definition": concept_name,
                "status": "synced_from_ontology",
                "source": "ONTOLOGY",
                "sync_timestamp": datetime.now().isoformat()
            }
            result.files_synced += 1
        
        # Sauvegarder le registre TOPOS
        registries_file = GOV_HUB / "registry" / "repos.json"
        if registries_file.exists():
            registries_file.write_text(json.dumps(self.topos_registry, indent=2), encoding='utf-8')
        
        result.status = "synced" if result.files_synced > 0 else "in_sync"
        return result

    def full_triadic_sync(self) -> Dict[str, Any]:
        """Exécute la synchronisation triadique complète."""
        results = {
            "timestamp": datetime.now().isoformat(),
            "syncs": {},
            "gaps": self.scan_gaps(),
            "summary": {}
        }
        
        # 1. TOPOS → VERSES
        results["syncs"]["topos_to_verses"] = asdict(self.sync_topos_to_verses())
        
        # 2. VERSES → ONTOLOGY
        results["syncs"]["verses_to_ontology"] = asdict(self.sync_verses_to_ontology())
        
        # 3. ONTOLOGY → TOPOS
        results["syncs"]["ontology_to_topos"] = asdict(self.sync_ontology_to_topos())
        
        # Résumé
        results["summary"] = {
            "total_gaps": sum(len(g) for g in results["gaps"].values()),
            "files_synced": sum(s.get("files_synced", 0) for s in results["syncs"].values()),
            "sync_status": "complete"
        }
        
        return results

    def reconcile(self) -> Dict[str, Any]:
        """Récupère les écarts et propose des corrections."""
        gaps = self.scan_gaps()
        reconciliation = {
            "timestamp": datetime.now().isoformat(),
            "gaps": gaps,
            "recommendations": []
        }
        
        if gaps["topos_missing_verses"]:
            reconciliation["recommendations"].append({
                "action": "create_verses",
                "count": len(gaps["topos_missing_verses"]),
                "concepts": gaps["topos_missing_verses"]
            })
        
        if gaps["verses_missing_ontology"]:
            reconciliation["recommendations"].append({
                "action": "create_ontology",
                "count": len(gaps["verses_missing_ontology"]),
                "concepts": gaps["verses_missing_ontology"]
            })
        
        if gaps["ontology_missing_topos"]:
            reconciliation["recommendations"].append({
                "action": "update_topos",
                "count": len(gaps["ontology_missing_topos"]),
                "concepts": gaps["ontology_missing_topos"]
            })
        
        return reconciliation


def main():
    parser = argparse.ArgumentParser(description="SELINA Triadic Sync — Synchronisation TOPOS/VERSES/ONTOLOGY")
    parser.add_argument("--scan", action="store_true", help="Scanner les gaps entre les strates")
    parser.add_argument("--sync", action="store_true", help="Synchroniser triadiquement")
    parser.add_argument("--reconcile", action="store_true", help="Analyser et recommander")
    parser.add_argument("--report", action="store_true", help="Générer un rapport de cohérence")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    sync = SelinaTriadicSync()
    
    if args.scan:
        gaps = sync.scan_gaps()
        if args.json:
            print(json.dumps(gaps, indent=2))
        else:
            print(f"\n[SELINA-TRIADIC] Scan des gaps:")
            total = 0
            for gap_type, gaps_list in gaps.items():
                count = len(gaps_list)
                total += count
                print(f"  {gap_type}: {count}")
                if gaps_list and count <= 10:
                    for g in gaps_list:
                        print(f"    - {g}")
            print(f"\nTotal gaps: {total}")
        return 0
    
    elif args.sync:
        results = sync.full_triadic_sync()
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"\n[SELINA-TRIADIC] Synchronisation complète:")
            print(f"  Files synced: {results['summary']['files_synced']}")
            print(f"  Total gaps: {results['summary']['total_gaps']}")
            for sync_name, sync_result in results['syncs'].items():
                status = sync_result.get('status', 'unknown')
                files = sync_result.get('files_synced', 0)
                print(f"  {sync_name}: {status} ({files} files)")
        return 0
    
    elif args.reconcile:
        recon = sync.reconcile()
        if args.json:
            print(json.dumps(recon, indent=2))
        else:
            print(f"\n[SELINA-TRIADIC] Reconciliation:")
            for rec in recon['recommendations']:
                print(f"  {rec['action']}: {rec['count']} concepts")
        return 0
    
    elif args.report:
        gaps = sync.scan_gaps()
        report = {
            "timestamp": datetime.now().isoformat(),
            "topos_count": len(sync.topos_registry.get("concepts", {})),
            "verses_count": len(sync.verses_concepts),
            "ontology_count": len(sync.ontology_terms),
            "gaps": gaps,
            "coherence_score": 1.0 - (sum(len(g) for g in gaps.values()) / max(1, len(sync.topos_registry.get("concepts", {})) + 1))
        }
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"\n[SELINA-TRIADIC] Rapport de cohérence:")
            print(f"  TOPOS concepts: {report['topos_count']}")
            print(f"  VERSES concepts: {report['verses_count']}")
            print(f"  ONTOLOGY concepts: {report['ontology_count']}")
            print(f"  Coherence score: {report['coherence_score']:.2%}")
        return 0
    
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())