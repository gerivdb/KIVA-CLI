---
type: "PRD_MOC"
version: "1.0"
date: "2026-08-18"
status: "ACTIF"
intent_hash: "0xPRD_MOC_KIVA_CLI_20260818_V1.0"
inherits: ["moc-governance"]
---

# PRD MOC -- KIVA-CLI -- META-ROADMAP FRACTALE -- V1.0

## 1. RESUME EXECUTIF

Le **PRD MOC KIVA-CLI** est la boussole produit du CLI souverain de l'ecosysteme gerivdb. Il expose la **topologie causale** des PRDs KIVA-CLI, cartographie les **dependances** et visualise les **points de bascule** actuels.

- 16 PRDs catalogues dans `PRD/`
- Gouvernance consolidee : regle BDCP GitHub API fallback, skill repo creator
- Pipeline PLIX-Eco, doctor CLI, GitHub keyring fallback
- RSS-v2 conforme, stashs nettoyes, tests cibles verts
- Tests : doctor_commands + blo_mox_bridge couverts (13 nouveaux tests)
- **Meta-roadmap fractale** en 4 strates (S1->S4)

**Portee :** KIVA-CLI L1, scripts associes, hooks git, pipelines `.kiva/pipelines/`.

**Etat :** consolidation governance en cours, foundation CI/runtime stable.

---

## 2. DASHBOARD GLOBAL

| Etat | PRDs catalogues | Derniere mise a jour |
|------|-----------------|---------------------|
| Actifs / Approuves | 12 | 2026-08-18 |
| Draft / Proposed | 4 | 2026-08-18 |
| **Total** | **16** | -- |

---

## 3. PRDS ACTIFS ET APPROUVES

| PRD | Version | Titre | Statut | Date |
|-----|---------|-------|--------|------|
| **PRD-000-index** | 1.0.0 | PRD-000-index | active | -- |
| **PRD-KIVA-001** | 1.0 | KIVA-001 -- Core CLI Foundation | active | 2026-06-05 |
| **PRD-KIVA-002** | 1.0 | KIVA-002 -- Subprocess Execution Engine | active | 2026-06-05 |
| **PRD-KIVA-003** | 1.0 | KIVA-003 -- Pipeline DAG Engine | active | 2026-06-05 |
| **PRD-KIVA-004** | 1.0 | KIVA-004 -- Shared Types Registry | active | 2026-06-05 |
| **PRD-KIVA-005** | 1.0 | KIVA-005 -- Subprocess Mocks | active | 2026-06-11 |
| **PRD-KIVA-006** | 1.0 | KIVA-006 -- Test Infrastructure | active | 2026-06-05 |
| **PRD-KIVA-007** | 1.0 | KIVA-007 -- CLI Command Groups | active | 2026-06-05 |
| **PRD-KIVA-008** | 1.0 | KIVA-008 -- Pipeline Commands | active | 2026-06-05 |
| **PRD-KIVA-009** | 1.0 | KIVA-009 -- Sprint 4 Pipeline Enrichment | active | 2026-06-05 |
| **PRD-KIVA-010** | 1.0 | KIVA-010 -- WAL & Drift Tracking | active | 2026-06-05 |
| **PRD-KIVA-011** | 1.0 | KIVA-011 -- when: Expression Language | active | 2026-06-05 |

---

## 4. PRDS DRAFT / PROPOSED

| PRD | Version | Titre | Statut | Date |
|-----|---------|-------|--------|------|
| **PRD-016-inverse-ir-scaffold-phi-conforme** | -- | INVERSE-IR -- Reconstruction scaffold phi-conforme | draft | 2026-06-20 |
| **PRD-MAGISTRAL-004** | -- | PRD-MAGISTRAL-004 | proposed | -- |
| **PRD-K7-roadmap** | 1.0 | PRD-K7-roadmap | draft | 2026-07-19 |
| **PRD-311-bootstrap-recursif** | -- | Bootstrap Recursif Bilevel -- Auto-recherche sur ONTOLOGY | proposed | -- |

---

## 5. META-ROADMAP FRACTALE KIVA-CLI

| Strate | Nom | Progression | Blocage | Jalons |
|--------|-----|-------------|---------|--------|
| S1 | Noyau CLI | 100% | Resolu | Tests cibles 48/48 verts |
| S2 | Gouvernance & CI | 100% | Resolu | RSS-v2 conforme, BDCP fallback skill, post-implement check en pre-commit |
| S3 | Structure & Tests | 100% | Resolu | Legacy tests convertis, doctor_commands/blo_mox_bridge couverts, chemins L2 configurables |
| S4 | Orchestration avancee | 10% | Depend S1-S3 | Parallel groups, retry pipeline |

---

## 6. ACTIONS PRIORITAIRES (P0-P2)

### P0 -- Bloquant

| # | Action | Cible | Source | Statut |
|---|--------|-------|--------|--------|
| 1 | Maintenir RSS-v2 conforme sur la branche consolidee | KIVA-CLI | rss_lint.py | OK Termine |
| 2 | Centraliser fallback token GitHub dans `kiva_cli.core.github_token` | KIVA-CLI | github_commands.py | OK Termine |
| 3 | Supprimer les stashs orphelins et nettoyer working tree | KIVA-CLI | git status | OK Termine |
| 4 | Corriger les 99 tests echouants (project_manager/scaffold/skill_manager) | KIVA-CLI | test_*.py | OK Termine |

### P1 -- Court terme

| # | Action | Cible | Source | Statut |
|---|--------|-------|--------|--------|
| 5 | Ajouter tests manquants pour atteindre 80% couverture | KIVA-CLI | pytest | PARTIEL (69% line coverage) |
| 6 | Etendre tests `doctor_commands.py` | KIVA-CLI | doctor_commands.py | OK Termine |
| 7 | Etendre tests `blo_mox_bridge.py` | KIVA-CLI | blo_mox_bridge.py | OK Termine |
| 8 | Valider `post_implement_check.py` en CI | KIVA-CLI | post_implement_check.py | OK Termine |

### P2 -- Moyen terme

| # | Action | Cible | Source | Statut |
|---|--------|-------|--------|--------|
| 9 | Implementer PRD-016 INVERSE-IR scaffold phi-conforme | KIVA-CLI | PRD-016 | A faire |
| 10 | Finaliser S4 orchestration parallele (retry, on_failure) | KIVA-CLI | PRD-KIVA-010 | A faire |
| 11 | Migrer `project_manager.py` vers types canoniques uniquement | KIVA-CLI | PRD-KIVA-004 | A faire |

---

## 7. POSITION DANS L'ECOSYSTEME

### Strate

| Strate | Composants | Role |
|-------|------------|------|
| **L1-INFRA** | KIVA-CLI | CI souverain local |
| L0-CANON | GOVERNANCE-HUB, ECOYSTEM | Constitutionnel |
| L2-PLATFORM | PLIX, MOX, TOPOS | Runtime / orchestration |
| L3-CITIZENS | ARGUS, MIMIR | Diagnostics / metriques |
| L4-TOOLS | FLEX, REPO-STANDARDS | Tooling / enforcement |

### Dependances critiques

| Dependance | Type | Etat |
|------------|------|------|
| `gerivdb/GOVERNANCE-HUB` | L0-CANON | OK Operationnel |
| `gerivdb/PLIX` | L2-PLATFORM | OK Operationnel |
| `gerivdb/FLEX` | L4-TOOLS | OK Cree 2026-08-18 |
| `D:\DO\WEB\TOOLS\L1-INFRA\KIVA-CLI` | Local clone | OK A jour |
| `C:\DevTools` | Hub central | OK Operationnel |

---

## 8. ANOMALIES CONNUES

| # | Anomalie | Localisation | Priorite |
|---|----------|--------------|----------|
| 1 | Couverture de tests < 80% (seuil global) | pytest | P1 |
| 2 | 62 tests legacy refactores non mis a jour | tests/test_kiva_cli.py, test_pipeline_retry.py, test_parallel_on_failure.py | P2 |

---

## 9. ACTIONS CORRECTIVES

| # | Action | Priorite | Statut |
|---|--------|----------|--------|
| 1 | Ajouter tests manquants pour atteindre 80% couverture | P1 | PARTIEL (69% line coverage, 13 nouveaux tests) |
| 2 | Mettre a jour les tests legacy refactores (scaffold, pipeline retry, parallel on_failure) | P2 | A faire |

---

## 10. GOUVERNANCE

- **Regle BDCP** : `bdcp-github-api-fallback.md` -- creation de repos sans desactiver BDCP
- **Skill** : `bdcp-github-repo-creator` -- procedure executable
- **ADR** : `ADR-0022-github-api-fallback` -- decision d'architecture
- **RSS-v2** : conforme, 0 violation

---

---

## 11. CHANGEMENTS RECENTS

| Date | Commit | Description |
|------|--------|-------------|
| 2026-08-18 | `4733fb7` | test: add coverage for doctor_commands and blo_mox_bridge |
| 2026-08-18 | `4869103` | feat(governance): integrate post-implement check in pre-commit and make blo_mox_bridge paths configurable |
| 2026-08-18 | `55cd1cd` | fix(cli,tests): repair broken integration and legacy registry tests |

---

*Derniere mise a jour : 2026-08-18 | Genere automatiquement*
