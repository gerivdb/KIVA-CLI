---
id: PRD-003
title: PRD-KIVA-003 — Windows Compatibility Auditor
repo: unknown
status: draft
created: '2026-06-11'
author: gerivdb
type: '"PRD"'
version: '"1.0"'
date: '2026-06-11'
intent_hash: 0xPRD_PRD_003_KIVA_003_WINDOWS_AUDIT_20260611
---

# PRD-KIVA-003 — Windows Compatibility Auditor

## Métadonnées

| Champ | Valeur |
|---|---|
| **Repo cible** | `KIVA-CLI` |
| **Destination** | `KIVA-CLI/PRD/` |
| **Transversalité** | NON (mais impact fort sur tout l'écosystème qui tourne majoritairement sur Windows) |
| **Repos impactés** | KIVA-CLI, DevTools, tous les repos utilisant des scripts PowerShell / CMD |
| **Priorité** | P2 |
| **Epic parent** | N/A |
| **Statut** | DRAFT |
| **Auteur** | @gerivdb |
| **Date création** | 2026-05-21 |
| **Dernière mise à jour** | 2026-05-21 |
| **Référence standard** | PRD-ROUTING-STANDARD |

---

## Contexte et problème

L'écosystème gerivdb est **majoritairement développé et exécuté sur Windows** (PowerShell 7, CMD wrappers, chemins Windows, encodage, LXC sous Windows, etc.).

Pourtant il n'existe aucun outil centralisé qui :

- Audite la compatibilité Windows d'un repo ou d'un script
- Détecte les violations des règles KiloCode (ex: `cd` + `&` au lieu de `powershell -File`, here-strings, caractères non-ASCII, etc.)
- Vérifie les wrappers CMD obligatoires
- Mesure la dette technique Windows (paths durs, encoding, subprocess non mockés, etc.)

Les règles actuelles (`harmonisation-v8.md`, `slm-fragmented-approach.md`, `ecos-cli-launcher.md`) sont documentées mais **non automatisées**.

---

## Objectifs

Créer un **Windows Compatibility Auditor** (agent + CLI) qui scanne un repo et produit un rapport de conformité Windows + suggestions de correction, en s'appuyant sur les types canoniques et le Subprocess Mock Orchestrator.

**Critères de succès :**
- Commande `kiva audit windows --path . --report`
- Détection des anti-patterns listés dans les règles KiloCode
- Score de compatibilité (0-100) + liste priorisée de violations
- Intégration dans les pipelines CI (étape bloquante ou warning)
- Utilisation des mocks subprocess pour les tests de l'auditor lui-même

---

## Périmètre

### In Scope

- `kiva_cli/auditors/windows_auditor.py`
- Règles auditables (basées sur les fichiers .kilocode/rules/*.md existants)
- Rapport JSON + Markdown + SARIF (pour GitHub)
- Intégration avec le Stub Generator et le Test-Repair Agent (proposition de fixes)
- Tests avec le nouveau Subprocess Mock Orchestrator

### Out of Scope (pour MVP)

- Correction automatique complète (sera fait par Test-Repair Agent)
- Audit d'autres plateformes (Linux/macOS spécifique)

---

## Spécifications fonctionnelles

Règles principales à auditer (exemples) :

- Usage de `cd foo && bar` au lieu de `powershell -File`
- Présence de here-strings problématiques
- Chemins durs Windows vs Path
- Encodage de fichiers (UTF-8 BOM, etc.)
- Appels subprocess directs vs orchestrator
- Violation des règles SLM Fragmented (commandes trop longues dans bash)

---

## Critères d'acceptation

```gherkin
Given un repo avec plusieurs violations des règles Windows
When on lance l'auditor
Then il produit un rapport avec score < 70 et liste priorisée
And il peut être intégré dans un pipeline KIVA sans toucher au système réel (grâce aux mocks)
```

---

## Dépendances

- PRD-KIVA-004 (types)
- PRD-KIVA-005 (Subprocess Mock Orchestrator) — fortement recommandé pour tester l'auditor
- Règles existantes dans `.kilocode/rules/`

---

## Références

- `.kilocode/rules/harmonisation-v8.md` (CMD wrapper)
- `.kilocode/rules/slm-fragmented-approach.md`
- `.kilocode/rules/ecos-cli-launcher*.md`
- `tools/patch_ecos_workflows.ps1`, `Add-EcosPath.ps1`, etc.

---

**Fin du PRD-KIVA-003**

> L'auditeur Windows est le garant que les règles d'orchestration de l'écosystème restent respectées à grande échelle, surtout dans un contexte où la majorité des agents et développeurs sont sur Windows.
