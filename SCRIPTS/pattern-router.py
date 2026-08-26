#!/usr/bin/env python3
"""
Pattern Router - Routes tasks to appropriate patterns based on keywords
"""

import sys
import re

PATTERNS = [
    ("lire|verifier|inspecter", "Pattern A (read atomique)"),
    ("scanner emojis|caracteres non-ASCII", "Pattern B (bash simple)"),
    ("creer|ecrire|nouveau fichier", "Pattern C (write)"),
    ("modifier|mettre a jour|corriger", "Pattern D (edit)"),
    ("deployer|copier vers repos|multi-repo", "Pattern E (sequence 1 repo/fois)"),
    ("installer|telecharger|setup outil", "devtools-probe"),
    ("pousser|push API|create_or_update_file", "pre-push-path-audit"),
    ("merger|PR prete|merge_pull_request", "ext-code-reviewer"),
    ("fin de session|tout est merge|cloture", "session-closeout (D5)"),
    ("debut de session|nouvelle session multi-repo", "session-boot-sequence"),
    ("deleguer|Agent Manager|sous-agent", "agent-budget-check"),
    ("cloner|git clone|clone local", "hitl-clone-gate + clone-causal-prevention"),
    ("ADR|decision architecture|nouveau pattern", "adr-governance-gate"),
    ("je ne trouve pas|n'existe pas localement", "clone-causal-prevention"),
    ("analyse comparative|compare avec|quels gaps", "anamorphoser"),
    ("sandbox|verify agent|test via box", "GATE-10 (conscience ecosystemique)"),
    ("review PR|code review|inline comment", "diff0-fork"),
    ("PR ouverte|merge|merger PR", "pr-lifecycle-gate"),
    ("gap|contradiction|impense", "ARGUS (couche logique N+2)"),
    ("orchestrer|router|pipeline|resolver", "CTULU (couche logique N+3)"),
    ("audit|meta-assurance|verifier coherence", "GOVERNANCE-HUB (couche logique N+4)"),
    ("objet explicite|gouvernance fonctionnelle", "GOVERNANCE-HUB/NEXUS (couche logique N+1)"),
    ("merge|synchroniser|post-merge|fetch|rebase|sync|pull", "post-merge-sync"),
    ("selina|sync cross-repo|desynchronisation", "selina_sync.py"),
    ("ecosystem|repos manquants|compter repos|scan ecosystem", "GATE-10 (ecosystem health verification)"),
]

def route_task(task_description):
    """Route a task description to the appropriate pattern"""
    task_lower = task_description.lower()
    
    for pattern, handler in PATTERNS:
        if re.search(pattern, task_lower):
            return handler
    
    return "Pattern A (read atomique) - default"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pattern-router.py '<task_description>'")
        print("\nExample:")
        print("  python pattern-router.py 'verifier le contenu du repo'")
        print("  python pattern-router.py 'scanner les emojis dans le code'")
        sys.exit(1)
    
    task = " ".join(sys.argv[1:])
    result = route_task(task)
    print(f"[ROUTER] Task: {task}")
    print(f"[ROUTER] Route: {result}")