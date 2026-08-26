---
type: "PRD_MOC"
version: "1.2"
date: "2026-08-19"
status: "ACTIF"
intent_hash: "0xPRD_MOC_KIVA_CLI_20260819_V1.2"
inherits: ["moc-governance"]
---

# PRD MOC -- KIVA-CLI -- META-ROADMAP FRACTALE -- V1.1

## 1. RESUME EXECUTIF

Le **PRD MOC KIVA-CLI** est la boussole produit du CLI souverain de l'ecosysteme gerivdb. Il expose la **topologie causale** des PRDs KIVA-CLI, cartographie les **dependances** et visualise les **points de bascule** actuels.

- 16 PRDs catalogues dans `PRD/`
- Gouvernance consolidee : regle BDCP GitHub API fallback, skill repo creator
- Pipeline PLIX-Eco, doctor CLI, GitHub keyring fallback
- RSS-v2 conforme, stashs nettoyes
- **Couverture tests globale : 43.84% (manque ~36% pour atteindre 80%)**
- **Tests legacy legacy refactores : 54/62 corriges (87%)** -- 8 restants
- **Tests integration : 12/12 passes** (WAL, phi-CPS, cross-repo, ternary logic)
- **Tests pipeline/parallel : 20/20 passes** (retry, on_failure, parallel groups)
- **Tests kiva_cli : 34/34 passes** (legacy compat functions restored)
- Meta-roadmap fractale en 4 strates (S1->S4) -- S4 a 15%

**Portee :** KIVA-CLI L1, scripts associes, hooks git, pipelines `.kiva/pipelines/`.

**Etat :** Consolidation governance terminee, legacy tests 87% corriges, foundation CI/runtime stable. **Blocant majeur : couverture tests 43.84% < 80% requis.**

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
| S1 | Noyau CLI | 100% | Resolu | Tests cibles 48/48 verts, legacy compat restored (34/34) |
| S2 | Gouvernance & CI | 100% | Resolu | RSS-v2 conforme, BDCP fallback skill, post-implement check, frontmatter validation en pre-commit |
| S3 | Structure & Tests | 87% | 8 tests restants | Legacy tests 54/62 corriges, pipeline/parallel 20/20, integration 12/12 |
| S4 | Orchestration avancee | 15% | S3 complet | Parallel groups, retry pipeline -- architecture prete, tests a finaliser |

**Couverture tests globale : 43.84% (seuil requis : 80%)**

---

## 6. ACTIONS PRIORITAIRES (P0-P2)

### P0 -- Bloquant (doit etre fait avant tout)

| # | Action | Cible | Source | Statut |
|---|--------|-------|--------|--------|
| 1 | Atteindre 80% couverture de tests globale | KIVA-CLI | pytest | **BLOQUANT -- 43.84% (manque ~36%)** |
| 2 | Finaliser S4 orchestration parallele (tests) | KIVA-CLI | PRD-KIVA-010 | Architecture prete, tests a finaliser |

### P1 -- Court terme

| # | Action | Cible | Source | Statut |
|---|--------|-------|--------|--------|
| 3 | Implementer PRD-016 INVERSE-IR scaffold phi-conforme | KIVA-CLI | PRD-016 | A faire |
| 4 | Migrer `project_manager.py` vers types canoniques uniquement | KIVA-CLI | PRD-KIVA-004 | A faire |
| 5 | Documenter workflows BDCP fallback et skills associes | KIVA-CLI | bdcp-github-api-fallback.md | A faire |

### P2 -- Moyen terme

| # | Action | Cible | Source | Statut |
|---|--------|-------|--------|--------|
| 6 | Ajouter tests pour modules 0% : nexus_commands.py (695l), epic_commands.py (427l), wal_commands.py (393l), pipeline_commands.py (273l), tql.py, project_commands.py, topos_commands.py, repo_commands.py, monitoring.py | KIVA-CLI | tests/ | A faire |
| 7 | Corriger test_audit_stale_branch (probleme parsing date ISO) | KIVA-CLI | test_*.py | A faire |
| 8 | Nettoyer warnings datetime.utcnow() deprecie dans tout le codebase | KIVA-CLI | *.py | A faire |

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
| 1 | Couverture de tests < 80% (43.84% vs 80% requis) | pytest | **P0 -- Bloquant** |
| 2 | S4 orchestration parallele non finalisee (15%) | parallel_executor.py, pipeline_retry.py, parallel_on_failure.py | P0 |
| 3 | Modules sans tests (0% couverture) : nexus_commands.py, epic_commands.py, wal_commands.py, pipeline_commands.py, tql.py, project_commands.py, topos_commands.py, repo_commands.py, monitoring.py + ~40 autres | kiva_cli/ | P1 |
| 4 | PRD-016 INVERSE-IR scaffold phi-conforme non implemente | PRD-016 | P1 |
| 5 | project_manager.py non migre vers types canoniques | kiva_cli/core/ | P1 |
| 6 | Documentation workflows BDCP fallback incomplete | bdcp-github-api-fallback.md | P1 |
| 7 | Test test_audit_stale_branch : probleme parsing date ISO | tests/ | P2 |
| 8 | Warnings datetime.utcnow() deprecié dans tout le codebase | *.py | P2 |

---

## 9. ACTIONS CORRECTIVES

| # | Action | Priorite | Statut |
|---|--------|----------|--------|
| 1 | Ajouter tests manquants pour atteindre 80% couverture | **P0** | BLOQUANT -- 43.84% actuel |
| 2 | Finaliser S4 orchestration parallele (tests finalisation) | **P0** | Architecture prete, tests a finaliser |
| 3 | Implementer PRD-016 INVERSE-IR scaffold phi-conforme | P1 | A faire |
| 4 | Migrer project_manager.py vers types canoniques uniquement | P1 | A faire |
| 5 | Documenter workflows BDCP fallback et skills associes | P1 | A faire |
| 6 | Ajouter tests pour modules 0% (nexus, epic, wal, pipeline, tql, etc.) | P1 | A faire |
| 7 | Corriger test_audit_stale_branch (probleme parsing date ISO) | P2 | A faire |
| 8 | Nettoyer warnings datetime.utcnow() deprecié | P2 | A faire |

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
| 2026-08-19 | -- | Mise a jour PRD MOC V1.2 : actualisation etat 65% complet, couverture 43.84%, actions P0/P1/P2 actualisees |
| 2026-08-18 | `4733fb7` | test: add coverage for doctor_commands and blo_mox_bridge |
| 2026-08-18 | `4869103` | feat(governance): integrate post-implement check in pre-commit and make blo_mox_bridge paths configurable |
| 2026-08-18 | `55cd1cd` | fix(cli,tests): repair broken integration and legacy registry tests |

---

## 12. PROCHAINES ETAPES CONCRETES

1. **Continuer pattern tests** : Creer tests pour `nexus_commands.py` -> `epic_commands.py` -> `wal_commands.py` (plus gros impact)
2. **Finaliser S4** : Tests pour `parallel_executor.py`, `pipeline_retry.py`, `parallel_on_failure.py` (architecture deja la)
3. **PRD-016** : Creer scaffold INVERSE-IR phi-conforme
4. **Migration types** : Remplacer `project_manager.py` par types canoniques de `kiva_cli.core.types`

---

*Derniere mise a jour : 2026-08-19 | Genere automatiquement*
