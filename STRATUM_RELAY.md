# STRATUM RELAY — KIVA-CLI (L3)

**VAGUE**: 3 | **Synchro**: 2026-05-29 | **Hub**: gerivdb/LLM-REPO

- **Strate** : `L3` — Systeme moteur CLI
- **Role canonique** : CLI orchestrateur projets/apps — scaffolding KIVA
- **Parent** : L2 (KIVA)
- **Enfants** : L4 (KIVA execute les deploiements)

## Regles locales
- R1 — KIVA-CLI orchestre les projets/apps — tout scaffolding passe par KIVA-CLI.
- R2 — KIVA execute, KIVA-CLI definit — ne pas inverser.
- Anti-pattern: deployer un projet sans passer par KIVA-CLI.

## Karpathy-Recall local (Vague 3 — 10Q)
1. Apres migration v1.1.0, que contient ECOS-CLI et que NE contient-il PLUS ?
2. Qu'est-ce que BLO et quel format de base de donnees utilise-t-il ?
3. Quelle commande ecos * est la plus critique a tester ?
4. Quelle est la frontiere entre KIVA-CLI (L3) et ECOS-CLI (L3) ?
5. Pourquoi KIVA-CLI ne doit-il pas executer directement les deploiements ?
6. Quels types de projets/apps KIVA-CLI peut-il scaffolder et comment KIVA les execute-t-il ?
7. Quel est le format de sortie du scaffolding KIVA-CLI et ou est-il stocke ?
8. Comment KIVA-CLI verifie-t-il qu'un projet est conforme avant de le deleguer a KIVA ?
9. Quelles sont les differences entre le mode 'create' et le mode 'deploy' dans KIVA-CLI ?
10. Comment KIVA-CLI integre-t-il le registre ECOS pour les dependances multi-repo ?

## Dependances directes

- **Parent (amont)** : KIVA (L2) — KIVA-CLI recoit les directives de scaffolding de KIVA.
- **Enfants (aval)** : Aucun — KIVA-CLI est une feuille de la chaine; il delegue l'execution a KIVA (L4).

## Vague de mise a jour

| Vague | Contenu | Statut |
|-------|---------|--------|
| 2 | Identite + regles + Karpathy-Recall 5Q | Deploye |
| **3 (courante)** | Recall etendu a 10Q + section Dependances | Deploye |
| 4 (suivante) | Tests de validation KIVA-CLI + integration BLO | Planifie |
