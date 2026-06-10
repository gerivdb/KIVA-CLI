---
id: PRD-004
title: "PRD-KIVA-004 — Shared Types Registry"
repo: unknown
status: draft
created: "2026-06-11"
author: gerivdb
---
# PRD-KIVA-004 — Shared Types Registry

<!-- Copier ce template, remplir tous les champs, supprimer les commentaires -->

## Métadonnées

| Champ | Valeur |
|---|---|
| **Repo cible** | `KIVA-CLI` |
| **Destination** | `KIVA-CLI/PRD/` |
| **Transversalité** | NON (mono-repo foundational pour KIVA-CLI) |
| **Repos impactés** | KIVA-CLI (primary). Potentiel export futur vers NEXUS pour cross-repo types. |
| **Priorité** | P1 |
| **Epic parent** | N/A |
| **Statut** | DRAFT |
| **Auteur** | @gerivdb (ECOS Ecosystem - H0 Autonomous) |
| **Date création** | 2026-05-21 |
| **Dernière mise à jour** | 2026-05-21 |
| **Référence standard** | [PRD-ROUTING-STANDARD](https://github.com/gerivdb/ECOYSTEM/blob/main/GOVERNANCE-HUB/governance-rules/PRD-ROUTING-STANDARD.md) |

---

## Contexte et problème

KIVA-CLI souffre d'une **fragmentation massive des types fondamentaux** à travers le codebase :

### État actuel (découvert lors de l'exploration du repo)

| Type | Localisations actuelles (duplications) | Problème |
|------|---------------------------------------|----------|
| `ValidationState` (Base-3) | `tools/ecosystem/skill_manager.py`, `kiva_cli/core/pipeline_manager.py` (re-import), `kiva_cli/core/project_manager.py` (redéfinition indépendante), `kiva_cli/core/deployment_manager.py`, multiples tests | États incohérents (PENDING/SUCCESS/FAILED vs UNKNOWN/VALID/INVALID). Imports circulaires ou cassés. |
| `LifecycleState` (Base-4) | `kiva_cli/core/project_manager.py` (GENESIS/ACTIVE/DEPRECATED/ARCHIVED), `kiva_cli/core/pipeline_manager.py` (redéfinition), `tests/test_nohitl_master_pipeline.py` | Deux machines d'états parallèles pour le même concept. |
| `DeploymentResult` | `kiva_cli/core/project_manager.py`, `kiva_cli/core/deployment_manager.py` | Deux implémentations avec champs différents. |
| `ValidationResult` / `ConfigResult` | `kiva_cli/core/config_validator.py`, `kiva_cli/core/config_manager.py` | Sémantiques proches mais structures incompatibles. |
| `Status` (Base-3 literals) | `kiva_cli/__init__.py` (définition centrale), mais ignorée dans la majorité des modules au profit de strings ou enums locaux | La "vérité" centrale n'est pas utilisée. |
| `FrameworkType`, `Template`, `ProjectConfig` | Uniquement dans `project_manager.py` ou `template_registry.py` | Pas de contrat partagé pour les 4 agents KIVA à venir. |

### Impact bloquant

Ce chaos de types **bloque directement** les 4 autres PRDs KIVA prioritaires :

- **PRD-KIVA-001** (Test-Repair Agent) : impossible de réparer des états incohérents sans source unique.
- **PRD-KIVA-002** (Stub Generator) : stubs générés à partir de types dupliqués → tests fragiles.
- **PRD-KIVA-003** (Windows Auditor) : audits de compatibilité impossibles sans contrats stables.
- **PRD-KIVA-005** (Subprocess Mocks) : mocks de subprocess dépendent de Result types fragmentés.

**Règle violée** : "Un PRD doit vivre là où son implémentation sera réalisée" (PRD-ROUTING-STANDARD §2). Le registry de types est **le** foundational block pour tout le reste de KIVA-CLI.

---

## Objectifs

**Objectif principal :**

> En tant que développeur KIVA-CLI (et futur auteur des agents Test-Repair, Stub Generator, etc.), je veux un **registre central unique** de tous les types fondamentaux (`kiva_cli/core/types.py`) afin que toutes les couches (core, commands, tools, tests, agents futurs) importent depuis **une seule source de vérité**, garantissant la cohérence Base-3/Base-4, IntentHash et φ-CPS sur tout l'écosystème KIVA.

**Critères de succès mesurables :**

- [ ] Fichier unique `kiva_cli/core/types.py` contenant toutes les définitions canoniques.
- [ ] Zéro duplication de `ValidationState`, `LifecycleState`, `*Result` dataclasses dans le reste du code (après migration).
- [ ] Tous les modules KIVA-CLI importent depuis `from kiva_cli.core.types import ...` (ou via `kiva_cli.core`).
- [ ] `__all__` explicite + documentation inline (docstrings + exemples).
- [ ] Shims de dépréciation (warnings) pour les anciens emplacements pendant la transition.
- [ ] Les 4 PRDs KIVA suivants (001,002,003,005) peuvent être rédigés et implémentés sans ambiguïté de types.
- [ ] Tests existants passent après refactor minimal (ou avec plan de migration documenté).
- [ ] Ajout dans `kiva_cli/__init__.py` pour exposition publique contrôlée.

---

## Périmètre

### In Scope ✅

- Création de `kiva_cli/core/types.py`
- Définition canonique de :
  - Base-3 : `ValidationState` (UNKNOWN=0 / VALID=1 / INVALID=-1) + helpers
  - Base-4 : `LifecycleState` (GENESIS / ACTIVE / DEPRECATED / ARCHIVED)
  - Base-3 status literals (si on garde le Literal de `__init__.py`)
  - Tous les `*Result` dataclasses unifiés (ConfigResult, ValidationResult, DeploymentResult, etc.)
  - Domain models : `ProjectConfig`, `Template`, `FrameworkType`, `DeploymentStrategy`, etc.
  - Type aliases : `IntentHash`, `PhiCPSValue`, `RepoPath`, `EntityId`, etc.
  - Constantes et enums transversaux KIVA (ex: `Base3`, `Base4`)
- Mise à jour de `kiva_cli/core/__init__.py` pour ré-exporter les types
- Guide de migration court (dans le fichier ou docs/)
- Ajout de tests unitaires minimaux pour le registry lui-même
- Mise à jour de la documentation (README ou docs/types.md si existe)

### Out of Scope ❌

- Refactor complet de tous les fichiers utilisant les anciens types (ce sera le travail des agents des PRDs 001-005)
- Création d'un registry cross-repo (NEXUS level) — ce PRD reste mono-repo KIVA-CLI
- Changement des sémantiques existantes (on consolide, on ne réinvente pas)
- Mise à jour des dépendances externes (DevTools, ECOYSTEM, etc.)

---

## Spécifications fonctionnelles

### 1. Base-3 Ternary Validation Types

```python
from enum import IntEnum
from typing import Literal

class ValidationState(IntEnum):
    """Base-3 semantic validation state."""
    UNKNOWN = 0
    VALID = 1
    INVALID = -1

# Type alias pour compatibilité string (là où utilisé)
ValidationStateStr = Literal["UNKNOWN", "VALID", "INVALID"]
```

Helpers :
- `is_valid(state)`, `is_invalid(state)`, `as_int(state)`, `from_str(s) -> ValidationState`

### 2. Base-4 Lifecycle Types

```python
class LifecycleState(IntEnum):
    """Base-4 project / pipeline lifecycle."""
    GENESIS = 0
    ACTIVE = 1
    DEPRECATED = 2
    ARCHIVED = 3
```

Transitions valides documentées (comme actuellement dans project_manager).

### 3. Result Contracts (unifiés)

Un seul pattern de Result :

```python
@dataclass
class KivaResult:
    """Base result contract for all KIVA operations."""
    success: bool
    validation_state: ValidationState
    message: str
    intent_hash: Optional[str] = None
    phi_cps_delta: float = 0.0
    artifacts: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

# Spécialisations
@dataclass
class ConfigResult(KivaResult):
    config_data: Optional[Dict[str, Any]] = None

@dataclass
class DeploymentResult(KivaResult):
    target: str = ""
    # ... champs spécifiques
```

### 4. Domain Core Types

- `FrameworkType(Enum)` : fastapi, react, go_service, python_lib, docker_compose, lxc_container, etc.
- `ProjectConfig` (dataclass complète avec tous les champs actuels)
- `Template` (dataclass)
- `DeploymentStrategy(Enum)`
- `PipelineType`, `StepType`, `ExecutionState`, `SkillType`, etc. (tous les enums actuellement dispersés)

### 5. Type Aliases & Constants

```python
IntentHash = str          # "0x..."
PhiCPSValue = float
RepoPath = Path
EntityId = str
Status = Literal["PENDING", "SUCCESS", "FAILED"]
```

### 6. Registry / Export

- Fichier : `kiva_cli/core/types.py`
- `from kiva_cli.core.types import *` (contrôlé par `__all__`)
- Ré-export dans `kiva_cli/core/__init__.py`
- Exposition optionnelle dans `kiva_cli/__init__.py` (pub API)

### 7. Compatibilité & Migration

- Les anciens fichiers gardent des imports avec `DeprecationWarning` pointant vers le nouveau registry.
- Script ou notice de migration pour les 4 PRDs suivants.

---

## Critères d'acceptation

```gherkin
Given un développeur importe des types KIVA
When il fait "from kiva_cli.core.types import ValidationState, LifecycleState, DeploymentResult"
Then il obtient les définitions canoniques uniques (pas de duplication dans le reste du repo)

Given un module legacy importe encore l'ancien ValidationState
When le code est exécuté
Then un DeprecationWarning clair est émis pointant vers kiva_cli/core/types.py

Given les 4 PRDs KIVA suivants (001-005) sont rédigés
When leurs auteurs consultent le Shared Types Registry
Then ils trouvent tous les contrats nécessaires (Base-3/4, Results, ProjectConfig, etc.) sans ambiguïté

Given un test existant utilise ValidationState.SUCCESS
When on exécute la suite après introduction du registry
Then les tests passent (ou le plan de migration documenté explique les 3 lignes à changer)
```

---

## Dépendances inter-repos

| Repo | Type de dépendance | PRD lié |
|---|---|---|
| (aucune pour ce PRD) | Mono-repo KIVA-CLI uniquement | N/A |

*Note : Une fois stabilisé, ce registry pourra être promu comme "KIVA Types Standard" dans NEXUS (PRD-XECO-001) pour les autres repos de l'écosystème.*

---

## Architecture / Design (si applicable)

**Fichier unique de vérité :**

```
KIVA-CLI/
├── kiva_cli/
│   ├── core/
│   │   ├── types.py           ← NOUVEAU : Single Source of Truth
│   │   ├── __init__.py        ← met à jour les exports
│   │   ├── project_manager.py ← utilise les types (migration progressive)
│   │   ├── pipeline_manager.py
│   │   ├── config_validator.py
│   │   └── ...
│   └── __init__.py            ← expose publiquement si besoin
```

**Principes :**
- Tout ce qui est "état sémantique Base-3/4", "résultat d'opération", "modèle domaine KIVA" → dans `types.py`
- Pas de logique métier dans `types.py` (seulement définitions + helpers purs)
- Utilisation d'IntEnum pour Base-3/Base-4 (compatibilité avec les valeurs numériques existantes dans WAL, DB, etc.)
- Dataclasses pour tous les résultats (facile à sérialiser en JSON pour WAL / API)

**Diagramme de dépendances cible (après migration) :**

```
tous modules KIVA
       │
       ▼
kiva_cli.core.types   (source unique)
       ▲
       │
kiva_cli.core.* (managers, validators...)
```

---

## Risques

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Breaking changes pendant la migration des 4 agents | Moyenne | Haut | Shims + DeprecationWarning + guide de migration détaillé dans le PRD et le fichier types.py |
| Tests existants cassés en masse | Moyenne | Moyen | Phase "compat layer" avant suppression des anciens types ; exécution complète de la suite de tests avant merge |
| Confusion "quel ValidationState utiliser ?" pendant transition | Haute | Bas | Documentation très claire dans types.py + mise à jour immédiate des imports dans les nouveaux fichiers (agents) |
| Désalignement futur avec NEXUS types | Basse | Moyen | Ce PRD reste KIVA-CLI ; la promotion cross-repo sera traitée dans PRD-XECO-001 |

---

## Références

- **Règle d'autorité** : [PRD-ROUTING-STANDARD](https://github.com/gerivdb/ECOYSTEM/blob/main/GOVERNANCE-HUB/governance-rules/PRD-ROUTING-STANDARD.md)
- **Template officiel** : [PRD-TEMPLATE.md](https://github.com/gerivdb/ECOYSTEM/blob/main/GOVERNANCE-HUB/hub-templates/PRD-TEMPLATE.md)
- **Registre central** : [ECOYSTEM/PRD/INDEX.md](https://github.com/gerivdb/ECOYSTEM/blob/main/PRD/INDEX.md)
- **PRDs KIVA dépendants** :
  - PRD-KIVA-001 — Test-Repair Agent
  - PRD-KIVA-002 — Stub Generator from Tests
  - PRD-KIVA-003 — Windows Compatibility Auditor
  - PRD-KIVA-005 — Subprocess Mock Orchestrator
- **PRD transversal bloqué sans ça** : PRD-XECO-001 — NEXUS Sync Agent v2
- Codebase analysis (2026-05-21) : exploration de `kiva_cli/core/`, `tools/ecosystem/`, `tests/`, `kiva_cli/__init__.py`, `project_manager.py`, `pipeline_manager.py`, `config_validator.py`, `config_manager.py`, `deployment_manager.py`, `template_registry.py`

---

**Fin du PRD-KIVA-004**

> Ce PRD est la **pierre angulaire** des 4 agents KIVA restants.  
> Une fois implémenté et adopté, la cohérence de tout l'orchestrateur KIVA-CLI (et potentiellement de l'écosystème) repose sur ce registre unique.
