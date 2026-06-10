---
id: PRD-001
title: "PRD-KIVA-001 — Test-Repair Agent"
repo: unknown
status: draft
created: "2026-06-11"
author: gerivdb
---
# PRD-KIVA-001 — Test-Repair Agent

<!-- Rédigé conformément à PRD-TEMPLATE.md et PRD-ROUTING-STANDARD.md -->

## Métadonnées

| Champ | Valeur |
|---|---|
| **Repo cible** | `KIVA-CLI` |
| **Destination** | `KIVA-CLI/PRD/` |
| **Transversalité** | NON (mono-repo, mais foundational pour l'autonomie No-HITL de tout l'écosystème) |
| **Repos impactés** | KIVA-CLI (primary). Les réparations produites peuvent impacter les repos cibles (BRAIN, FLUENCE, ECOYSTEM, NEXUS) via les skills de push/PR. |
| **Priorité** | P1 |
| **Epic parent** | N/A (s'inscrit dans la série des agents autonomes KIVA) |
| **Statut** | DRAFT |
| **Auteur** | @gerivdb (ECOS Ecosystem - H0 Autonomous) |
| **Date création** | 2026-05-21 |
| **Dernière mise à jour** | 2026-05-21 |
| **Référence standard** | [PRD-ROUTING-STANDARD](https://github.com/gerivdb/ECOYSTEM/blob/main/GOVERNANCE-HUB/governance-rules/PRD-ROUTING-STANDARD.md) |

---

## Contexte et problème

KIVA-CLI est conçu pour fonctionner en mode **H0_AUTONOMOUS_BASE3_NO_HITL** (zéro intervention humaine).

Cependant, le système actuel détecte les défaillances mais **ne les répare pas automatiquement** de manière intelligente :

### Problèmes identifiés dans le codebase

1. **PostCommitVerifierSkill** (`kiva_cli/core/post_commit_verifier_skill.py`)
   - Excellent pour détecter les échecs silencieux après push (SHA mismatch, fichiers manquants, branch protection failures)
   - Déclenche `auto_rollback` en cas d'échec
   - **Mais** : il ne propose **aucune réparation** du contenu lui-même (ex: corriger une mauvaise référence après un refactor de types)

2. **AutoRollbackPipeline** (`kiva_cli/core/auto_rollback_pipeline.py`)
   - Gère le rollback sur dérive φ-CPS
   - Restaure l'état WAL/ECOS_ROOT
   - **Mais** : rollback = retour en arrière, pas de **réparation proactive** du code qui a causé la dérive

3. **PipelineManager + SkillManager** (`kiva_cli/core/pipeline_manager.py`, `tools/ecosystem/skill_manager.py`)
   - Utilisent des `ValidationState` fragmentés (PENDING/SUCCESS/FAILED vs UNKNOWN/VALID/INVALID)
   - Les skills échouent souvent sur des erreurs "classiques" d'autonomie :
     - Imports cassés après refactor
     - États Base-3/Base-4 incohérents
     - Fichiers générés manquants ou mal formés
     - Subprocess mocks défaillants (voir PRD-KIVA-005)

4. **Tests et simulations de défaillance**
   - `test_post_commit_verifier_skill.py`, `test_auto_rollback_pipeline.py`, `test_nohitl_master_pipeline.py`, `test_integration.py`
   - Beaucoup de tests simulent des **échecs** et vérifient que le système "détecte + rollback"
   - **Aucun mécanisme** pour que l'agent **répare** la cause racine et relance avec succès

### Conséquence

Le mode No-HITL est **fragile** : une seule erreur de refactor (ex: après l'implémentation de PRD-KIVA-004 Shared Types Registry) peut casser des dizaines de fichiers et nécessiter une intervention manuelle, violant le contrat H0.

---

## Objectifs

**Objectif principal :**

> En tant qu'orchestrateur KIVA autonome (H0), je veux un **Test-Repair Agent** qui, après chaque défaillance détectée (test échec, skill failure, post-commit verification failure, φ-CPS drift), analyse la cause, propose ou applique une réparation minimale et sûre, et relance la validation — le tout sans intervention humaine.

**Critères de succès mesurables :**

- [ ] Agent capable de réparer au minimum les 5 classes d'erreurs les plus fréquentes identifiées dans les tests actuels :
  1. Import / référence cassée (surtout après consolidation des types KIVA-004)
  2. État Base-3/Base-4 incohérent (mauvais `ValidationState` ou `LifecycleState`)
  3. Fichier manquant ou SHA mismatch après push (PostCommitVerifier)
  4. Configuration dérivée (kiva.yaml, ECOS_ROOT.json, templates)
  5. Subprocess / mock défaillant (en lien avec PRD-KIVA-005)
- [ ] Intégration native avec `PostCommitVerifierSkill` + `AutoRollbackPipeline` + `PipelineManager`
- [ ] Utilise exclusivement les types canoniques de `core/types.py` (PRD-KIVA-004)
- [ ] Produit un **RepairReport** traçable dans le WAL global (IntentHash + φ-CPS delta + avant/après)
- [ ] Taux de réparation automatique ≥ 70 % sur les scénarios de test existants (mesuré via nouvelle suite de tests)
- [ ] Zéro régression sur les chemins de rollback existants (le repair est optionnel et safe)

---

## Périmètre

### In Scope ✅

- Création de l'agent : `kiva_cli/agents/test_repair_agent.py` (ou `core/test_repair_agent.py`)
- Analyseur de défaillance (parse pytest output, skill logs, verification results, WAL events)
- Réparateurs modulaires (Repair Strategies) :
  - `ImportRepairStrategy`
  - `StateMachineRepairStrategy` (correction des ValidationState/LifecycleState)
  - `PostCommitContentRepairStrategy` (génère le bon fichier manquant ou corrige le SHA)
  - `ConfigDriftRepairStrategy`
  - `SubprocessMockRepairStrategy` (pont vers PRD-KIVA-005)
- `RepairReport` dataclass (avec IntentHash, phi_delta, actions appliquées, confidence)
- Intégration dans le `PipelineManager` (nouveau StepType : `TEST_REPAIR`)
- Tests unitaires + scénarios d'intégration (simulation de pannes + réparation)
- Documentation d'utilisation et des stratégies supportées

### Out of Scope ❌

- Réparation de bugs sémantiques complexes ("le test est rouge parce que la logique métier est fausse") — scope humain ou agent de niveau supérieur
- Réparation cross-repo complète (ce sera le rôle du NEXUS Sync Agent v2 - PRD-XECO-001)
- Génération de nouveaux tests (ce sera PRD-KIVA-002 Stub Generator)
- Audit Windows (PRD-KIVA-003)
- Exécution en continu comme daemon (sera géré plus tard via daemon_manager)

---

## Spécifications fonctionnelles

### 1. Architecture de l'agent

```
TestRepairAgent
├── FailureAnalyzer (parse logs, WAL, VerificationResult, pytest JSON)
├── RepairPlanner (choisit 1..N stratégies selon pattern détecté)
├── RepairExecutor (applique les patches de manière sûre + git-friendly)
├── RepairReporter (génère RepairReport + écrit dans GlobalWALManager)
└── Integration hooks (PostCommitVerifier, PipelineManager, SkillManager)
```

### 2. Repair Strategies (minimum viable)

| Stratégie | Défaillance typique | Action de réparation |
|-----------|---------------------|----------------------|
| `ImportRepairStrategy` | `ModuleNotFoundError`, import cassé après refactor types | Remplace l'import par `from kiva_cli.core.types import ...` + met à jour `__init__.py` |
| `StateMachineRepairStrategy` | Mauvais `ValidationState` (PENDING vs UNKNOWN, SUCCESS vs VALID) | Normalise vers les enums canoniques de `core/types.py` |
| `PostCommitContentRepairStrategy` | Fichier manquant ou SHA mismatch après push | Régénère le fichier attendu à partir du template / skill source + re-push |
| `ConfigDriftRepairStrategy` | kiva.yaml / ECOS_ROOT.json / template obsolète | Applique le template courant + recalcule IntentHash |
| `SubprocessMockRepairStrategy` | Test qui échoue sur subprocess réel (pas de mock) | Injecte le bon mock (lien avec PRD-KIVA-005) |

### 3. Contrat de sortie : `RepairReport`

```python
@dataclass
class RepairReport:
    repair_id: str
    intent_hash: str
    failure_source: str  # ex: "post_commit_verifier:abc123"
    detected_pattern: str
    strategies_applied: List[str]
    files_modified: List[str]
    success: bool
    confidence: float  # 0.0 - 1.0
    phi_cps_delta: float
    before_state: Dict
    after_state: Dict
    wal_event_id: str
```

### 4. Intégration dans le pipeline existant

Ajout d'un nouveau `StepType.REPAIR` dans `PipelineManager`.

Le `PostCommitVerifierSkill` pourra, en cas de `INVALID`, invoquer optionnellement le Test-Repair Agent avant de déclencher le rollback.

---

## Critères d'acceptation

```gherkin
Given un pipeline No-HITL pousse des fichiers et le PostCommitVerifier détecte un SHA mismatch
When le Test-Repair Agent est activé
Then il identifie le pattern "contenu manquant après refactor types"
And il applique ImportRepairStrategy + PostCommitContentRepairStrategy
And il relance la vérification
Then le statut global passe à VALID sans rollback
And un RepairReport avec IntentHash est écrit dans le Global WAL

Given un test échoue avec "ValidationState.SUCCESS" alors que le type canonique est "VALID"
When le Test-Repair Agent analyse l'échec
Then il applique StateMachineRepairStrategy
And normalise tous les usages vers les types de core/types.py (PRD-KIVA-004)
And les tests suivants passent

Given plusieurs stratégies sont candidates
When le RepairPlanner calcule les scores
Then il choisit la combinaison avec le plus haut confidence × plus faible φ-CPS impact
And n'applique jamais de réparation dont la confidence < 0.6 sans demande explicite
```

---

## Dépendances inter-repos

| Repo | Type de dépendance | PRD lié |
|---|---|---|
| KIVA-CLI (interne) | Dépend de `core/types.py` (Shared Types Registry) | PRD-KIVA-004 |
| KIVA-CLI | Peut invoquer / être invoqué par PipelineManager, SkillManager, PostCommitVerifierSkill | — |
| (futur) | Les réparations peuvent être poussées vers BRAIN / FLUENCE / ECOYSTEM via les skills existants | PRD-XECO-001 (NEXUS Sync) |

---

## Architecture / Design

**Emplacement proposé :**
- `kiva_cli/agents/test_repair_agent.py`
- `kiva_cli/core/repair_strategies/` (package avec une classe par stratégie)
- Réutilisation massive de `GlobalWALManager`, `IntentHashValidator`, `PhiCPSCalculator`

**Flux typique :**
1. Échec détecté (PostCommitVerifier / Pipeline / Skill)
2. `FailureAnalyzer` construit un `FailureSignature`
3. `RepairPlanner` sélectionne les stratégies
4. `RepairExecutor` applique (dry-run possible)
5. `RepairReporter` persiste le rapport + φ-CPS + IntentHash
6. Re-validation automatique

**Sécurité :**
- Toute réparation est versionnée (git)
- Rollback possible du repair lui-même via l'AutoRollbackPipeline existant
- Seuil de confiance configurable
- Mode "propose only" (ne fait que suggérer le patch)

---

## Risques

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Réparation incorrecte qui empire l'état | Moyenne | Haut | Confidence threshold + dry-run + rollback automatique du repair |
| Explosion du nombre de stratégies à maintenir | Moyenne | Moyen | Architecture plugin + seulement 5 stratégies dans le MVP |
| Conflit avec le mode "strict No-HITL" (trop d'autonomie) | Basse | Moyen | Le repair est **optionnel** et activable par feature flag ou par le PipelineManager |
| Performance (analyse de gros logs) | Basse | Bas | Analyse incrémentale + cache des signatures |

---

## Références

- **PRD fondateur** : PRD-KIVA-004 — Shared Types Registry (`core/types.py`)
- **Composants existants à étendre** :
  - `kiva_cli/core/post_commit_verifier_skill.py`
  - `kiva_cli/core/auto_rollback_pipeline.py`
  - `kiva_cli/core/pipeline_manager.py`
  - `tools/ecosystem/skill_manager.py`
  - `kiva_cli/core/global_wal_manager.py`
- **Tests de référence** :
  - `tests/test_post_commit_verifier_skill.py`
  - `tests/test_auto_rollback_pipeline.py`
  - `tests/test_nohitl_master_pipeline.py`
  - `tests/test_integration.py`
- Règle d'autorité : PRD-ROUTING-STANDARD v1.0.0
- Mode de fonctionnement cible : `H0_AUTONOMOUS_BASE3_NO_HITL`

---

**Fin du PRD-KIVA-001**

> Ce PRD transforme KIVA-CLI d'un système qui "détecte et rollback" en un système qui **"détecte, répare et continue"** — condition sine qua non pour un vrai mode autonome H0.
