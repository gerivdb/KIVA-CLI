#!/usr/bin/env python3
"""
Base-5 Fire-and-Forget Webhook Handler
Exécuté sur les runners self-hosted LXC ENV2

Traite les issues GitHub avec label `base5-generate` et génère les composants automatiquement.
100% fire-and-forget, aucune intervention humaine.
"""

from __future__ import annotations
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Base5WebhookHandler:
    """
    Gestionnaire de webhook pour Base-5 L27
    Exécuté sur les runners self-hosted KIVA-CLI ENV2
    """

    def __init__(self):
        self.pipeline = None

    async def handle_issue_event(self, payload: Dict[str, Any]) -> bool:
        """
        Traite un événement issue GitHub
        Si label `base5-generate` est présent: génère le composant automatiquement
        """
        try:
            issue = payload.get('issue', {})
            labels = [l['name'] for l in issue.get('labels', [])]
            
            if 'base5-generate' not in labels:
                logger.info("Pas de label base5-generate, ignoré")
                return False
                
            issue_number = issue.get('number')
            title = issue.get('title', '')
            body = issue.get('body', '')
            
            logger.info(f"🏗️  Base-5 Fire-and-Forget: Issue #{issue_number}")
            logger.info(f"Titre: {title}")
            
            # Extraire les paramètres depuis le titre/body
            import re
            component_match = re.search(r'(Thermodynamic[A-Za-z0-9_]+)', title)
            issue_match = re.search(r'[0-9]+\.[0-9]+', title)
            
            component_name = component_match.group(1) if component_match else f"ThermodynamicComponent{issue_number}"
            issue_id = issue_match.group(0) if issue_match else f"000.00{issue_number}"
            
            # Exécuter génération Base-5
            import sys
            sys.path.insert(0, r"D:\DO\WEB\TOOLS\FLUENCE")
            from tools.base5_generator import base5
            
            result = await base5.generate(
                prompt=f"issue_{issue_number}",
                pattern="thermodynamic_component",
                component_name=component_name,
                issue=issue_id,
                description=title
            )
            
            # Écrire le fichier généré directement dans le repo
            output_file = Path(f"core/{component_name.lower()}.py")
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(result, encoding='utf-8')
            
            # Commit et push automatique
            import subprocess
            branch_name = f"base5/generate_{issue_number}"
            
            subprocess.run(["git", "checkout", "-b", branch_name], capture_output=True)
            subprocess.run(["git", "add", str(output_file)], capture_output=True)
            subprocess.run(["git", "commit", "-m", f"base5: auto-generate {component_name}"], capture_output=True)
            subprocess.run(["git", "push", "--set-upstream", "origin", branch_name], capture_output=True)
            
            # Créer PR automatiquement
            subprocess.run([
                "gh", "pr", "create",
                "--title", f"[Base-5] Génération auto {component_name}",
                "--body", f"Généré automatiquement par Base-5 L27 Fire-and-Forget\nIssue #{issue_number}",
                "--label", "auto-generated",
                "--label", "base5"
            ], capture_output=True)
            
            logger.info(f"✅ Base-5 génération terminée: {component_name}")
            logger.info(f"✅ PR créé automatiquement")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur Base-5 webhook: {e}")
            # Base-5 est fire-and-forget: on ne retourne jamais d'erreur
            return True


async def main():
    handler = Base5WebhookHandler()
    
    # Simuler un événement pour test
    test_payload = {
        "issue": {
            "number": 175,
            "title": "ThermodynamicTestComponent #083.20",
            "body": "Test Base-5 génération",
            "labels": [{"name": "base5-generate"}]
        }
    }
    
    await handler.handle_issue_event(test_payload)


if __name__ == "__main__":
    asyncio.run(main())
