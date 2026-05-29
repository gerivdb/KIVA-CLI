# STRATUM RELAY — KIVA-CLI (L3)

**VAGUE**: 2 | **Synchro**: 2026-05-29 | **Hub**: gerivdb/LLM-REPO

- **Strate** : `L3` — Systeme moteur CLI
- **Role canonique** : CLI orchestrateur projets/apps — scaffolding KIVA
- **Parent** : L2 (BRAIN)
- **Enfants** : L4 (KIVA execute les deploiements)

## Regles locales
- R1 — KIVA-CLI orchestre les projets/apps — tout scaffolding passe par KIVA-CLI.
- R2 — KIVA execute, KIVA-CLI definit — ne pas inverser.
- Anti-pattern: deployer un projet sans passer par KIVA-CLI.

## Karpathy-Recall local (Vague 2 — 5Q)
1. Apres migration v1.1.0, que contient ECOS-CLI et que NE contient-il PLUS ?
2. Qu'est-ce que BLO et quel format de base de donnees utilise-t-il ?
3. Quelle commande ecos * est la plus critique a tester ?
4. Quelle est la frontiere entre KIVA-CLI (L3) et ECOS-CLI (L3) ?
5. Pourquoi KIVA-CLI ne doit-il pas executer directement les deploiements ?
