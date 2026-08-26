#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
riddlar_citizens.py — RIDDLER-Citizens : Runtime Intelligence & Dispatch for Citizen Classification.

Détecte, classe et orchestre les citizens (agents) de l'écosystème gerivdb.
Base de données locale des citizens avec métadonnées et relations.

Usage:
    python scripts/riddlar_citizens.py --scan [--output-json]
    python scripts/riddlar_citizens.py --classify <intent_file>
    python scripts/riddlar_citizens.py --relate <citizen_id>

IntentHash: 0xRIDDLAR_CITIZENS_20260707
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
INTENTS_DIR = REPO_ROOT / "INTENTS"
CITIZENS_FILE = REPO_ROOT / "CITIZENS.md"
KNOWN_CITIZENS_DB = REPO_ROOT / "ontolocal" / "citizens" / "citizens.db.json"


@dataclass
class Citizen:
    """Représente un citoyen (agent/skill) de l'écosystème."""
    id: str
    title: str
    source: str
    intent_hash: str
    notes: str = ""
    status: str = "active"
    dependencies: List[str] = None
    layer: str = "L4-TOOLS"
    created_at: str = ""
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class RiddlerCitizens:
    """Classifie et orchestre les citizens de l'écosystème gerivdb."""

    def __init__(self, repo_root: Path = None):
        self.repo_root = repo_root or REPO_ROOT
        self.citizens: Dict[str, Citizen] = {}
        self.load_citizens_db()

    def load_citizens_db(self) -> None:
        """Charge la base de données des citizens."""
        if KNOWN_CITIZENS_DB.exists():
            with open(KNOWN_CITIZENS_DB, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Gérer les deux formats: direct ou avec 'citizens' key
                if 'citizens' in data:
                    citizens_data = data['citizens']
                else:
                    citizens_data = {k: v for k, v in data.items() if k not in ['metadata', 'tools', 'version']}
                
                for cid, cdata in citizens_data.items():
                    if isinstance(cdata, dict):
                        self.citizens[cid] = Citizen(**cdata)

    def save_citizens_db(self) -> None:
        """Sauvegarde la base de données des citizens."""
        KNOWN_CITIZENS_DB.parent.mkdir(parents=True, exist_ok=True)
        data = {cid: asdict(citizen) for cid, citizen in self.citizens.items()}
        with open(KNOWN_CITIZENS_DB, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def parse_citizens_md(self) -> List[Citizen]:
        """Parse le fichier CITIZENS.md pour extraire les citizens."""
        if not CITIZENS_FILE.exists():
            return []
        
        content = CITIZENS_FILE.read_text(encoding='utf-8')
        citizens = []
        
        # Pattern pour extraire les lignes du tableau
        pattern = r'\| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]*) \|'
        matches = re.findall(pattern, content)
        
        for match in matches:
            cid, title, source, intent_hash, notes = [m.strip() for m in match]
            if cid and cid != 'ID':  # Skip header
                citizen = Citizen(
                    id=cid,
                    title=title,
                    source=source,
                    intent_hash=intent_hash,
                    notes=notes
                )
                citizens.append(citizen)
                self.citizens[cid] = citizen
        
        return citizens

    def scan_intents(self) -> Dict[str, List[str]]:
        """Scanne le répertoire INTENTS et retourne les fichiers par type."""
        if not INTENTS_DIR.exists():
            return {}
        
        by_type = {
            'INTENT': [],
            'EPIC': [],
            'ADR': [],
            'PRD': [],
            'REPORT': [],
            'RPT': [],
            'GUI': [],
            'RUN': []
        }
        
        for intent_file in INTENTS_DIR.glob("*.md"):
            content = intent_file.read_text(encoding='utf-8')
            
            # Extraire le type depuis le frontmatter
            type_match = re.search(r'^type:\s*(\w+)', content, re.MULTILINE)
            if type_match:
                doc_type = type_match.group(1)
                if doc_type in by_type:
                    by_type[doc_type].append(str(intent_file))
        
        return by_type

    def extract_intent_hash(self, intent_path: Path) -> str:
        """Extrait l'intent_hash d'un fichier INTENT."""
        content = intent_path.read_text(encoding='utf-8')
        match = re.search(r'intent_hash:\s*(0x[\w]+)', content)
        return match.group(1) if match else ""

    def classify_intent(self, intent_path: Path) -> Dict:
        """Classe un INTENT et retourne son analyse."""
        content = intent_path.read_text(encoding='utf-8')
        
        # Extraire le frontmatter
        fm_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not fm_match:
            return {"error": "No frontmatter found"}
        
        frontmatter = fm_match.group(1)
        
        # Parser les champs
        fields = {}
        for line in frontmatter.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                fields[key.strip()] = value.strip().strip('"').strip("'")
        
        # Classification
        classification = {
            "path": str(intent_path),
            "type": fields.get('type', 'unknown'),
            "status": fields.get('status', 'unknown'),
            "intent_hash": fields.get('intent_hash', ''),
            "title": fields.get('title', intent_path.stem),
            "dependencies": self._extract_dependencies(content),
            "layer": self._determine_layer(fields),
            "can_be_citizen": self._can_be_citizen(fields),
            "citizen_id": self._suggest_citizen_id(fields)
        }
        
        return classification

    def _extract_dependencies(self, content: str) -> List[str]:
        """Extrait les dépendances d'un document."""
        deps = []
        
        # Chercher les références ADR
        adr_refs = re.findall(r'ADR-(\d+)', content)
        deps.extend([f"ADR-{adr}" for adr in adr_refs])
        
        # Chercher les références d'autres docs
        doc_refs = re.findall(r'(INTENT-\d+|EPIC-\d+|PRD-\d+)', content)
        deps.extend(doc_refs)
        
        return list(set(deps))

    def _determine_layer(self, fields: Dict) -> str:
        """Détermine la couche logique d'un document."""
        # Logique N+1/N+2/N+3/N+4
        if fields.get('type') == 'ADR':
            return 'L1-INFRA'  # ADR = governance layer
        if 'pipeline' in fields.get('title', '').lower():
            return 'L3_EMERGENCE'
        if 'sync' in fields.get('title', '').lower():
            return 'L3_EMERGENCE'
        return 'L4_TOOLS'

    def _can_be_citizen(self, fields: Dict) -> bool:
        """Détermine si un document peut devenir un citizen."""
        # Un citizen doit avoir un intent_hash valide
        intent_hash = fields.get('intent_hash', '')
        if not intent_hash or not intent_hash.startswith('0x'):
            return False
        
        # Et un type connu
        valid_types = ['INTENT', 'ADR', 'GUI', 'RUN']
        return fields.get('type') in valid_types

    def _suggest_citizen_id(self, fields: Dict) -> str:
        """Génère un ID de citizen suggéré."""
        intent_hash = fields.get('intent_hash', '')
        if intent_hash:
            # Extraire un ID court de l'intent_hash
            return f"CITIZEN_{intent_hash[-8:]}"
        return ""

    def relate_citizens(self, citizen_id: str) -> Dict:
        """Trouve les relations d'un citoyen avec les autres."""
        if citizen_id not in self.citizens:
            return {"error": f"Citizen {citizen_id} not found"}
        
        citizen = self.citizens[citizen_id]
        relations = {
            "citizen": citizen_id,
            "title": citizen.title,
            "dependencies": citizen.dependencies,
            "dependents": [],
            "layer": citizen.layer
        }
        
        # Trouver les citoyens qui dépendent de ce citoyen
        for cid, c in self.citizens.items():
            if citizen.id in c.dependencies:
                relations["dependents"].append(cid)
        
        return relations


def main():
    parser = argparse.ArgumentParser(description="RIDDLER-Citizens : Citizen Classification")
    parser.add_argument("--scan", action="store_true", help="Scan INTENTS directory")
    parser.add_argument("--output-json", action="store_true", help="Output as JSON")
    parser.add_argument("--classify", type=str, help="Classify a specific INTENT file")
    parser.add_argument("--relate", type=str, help="Find relations of a citizen")
    parser.add_argument("--list", action="store_true", help="List all known citizens")
    parser.add_argument("--sync-md", action="store_true", help="Sync CITIZENS.md with DB")
    
    args = parser.parse_args()
    
    riddler = RiddlerCitizens()
    
    if args.scan:
        intents_by_type = riddler.scan_intents()
        results = {
            "scan_timestamp": datetime.now().isoformat(),
            "by_type": intents_by_type,
            "total_intents": sum(len(v) for v in intents_by_type.values())
        }
        
        # Classifier chaque INTENT
        results["classifications"] = {}
        for doc_type, files in intents_by_type.items():
            for intent_file in files:
                classification = riddler.classify_intent(Path(intent_file))
                results["classifications"][Path(intent_file).stem] = classification
        
        if args.output_json:
            print(json.dumps(results, indent=2))
        else:
            print(f"\n[RIDDLER-Citizens] Scan complete:")
            for doc_type, files in intents_by_type.items():
                print(f"  {doc_type}: {len(files)} files")
            print(f"\nTotal: {results['total_intents']} documents found")
        
        riddler.save_citizens_db()
        return 0
    
    elif args.classify:
        classification = riddler.classify_intent(Path(args.classify))
        if args.output_json:
            print(json.dumps(classification, indent=2))
        else:
            print(f"\n[RIDDLER-Citizens] Classification:")
            for key, value in classification.items():
                print(f"  {key}: {value}")
        return 0
    
    elif args.relate:
        relations = riddler.relate_citizens(args.relate)
        if args.output_json:
            print(json.dumps(relations, indent=2))
        else:
            print(f"\n[RIDDLER-Citizens] Relations for {relations['citizen']}:")
            print(f"  Title: {relations['title']}")
            print(f"  Layer: {relations['layer']}")
            print(f"  Dependencies: {relations['dependencies']}")
            print(f"  Dependents: {relations['dependents']}")
        return 0
    
    elif args.list:
        if args.output_json:
            print(json.dumps({cid: asdict(c) for cid, c in riddler.citizens.items()}, indent=2))
        else:
            print(f"\n[RIDDLER-Citizens] Known Citizens ({len(riddler.citizens)}):")
            for cid, citizen in riddler.citizens.items():
                print(f"  {cid}: {citizen.title}")
        return 0
    
    elif args.sync_md:
        riddler.parse_citizens_md()
        riddler.save_citizens_db()
        print(f"[RIDDLER-Citizens] Synced {len(riddler.citizens)} citizens to database")
        return 0
    
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())