---
id: PRD-008
title: "PRD-KIVA-008 — kiva pipeline chain / AutoChainManager"
repo: unknown
status: draft
created: "2026-06-11"
author: gerivdb
---
# PRD-KIVA-008 — kiva pipeline chain / AutoChainManager

**ID** : `PRD-KIVA-008`
**Scope** : `KIVA-CLI` (mono-repo)
**Statut** : `DRAFT`
**Priorité** : P1
**Date de création** : 2026-05-22
**Auteur** : gerivdb
**Intent Hash** : `0xPRD008::kiva-pipeline-chain::2026-05-22`
**Dépend de** : PRD-KIVA-007 (AutoChain Integration Layer — DONE)
**Impact écosystème** : KIVA-CLI, ECOYSTEM (ECOS_ROOT.json), NEXUS (SOT)

---

## 1. Contexte

PRD-KIVA-007 a livré :
- Le guard `HAS_AUTOCHAIN` (vérification qu'un repo est éligible à l'enchaînement)
- `run_chain()` — exécution séquentielle d'une séquence de commandes KIVA
- L'option `--chain` sur les commandes ciblées

**Problème ouvert (P1.5)** : `run_chain()` fonctionne en mode hardcodé — la séquence est définie dans le code Python, pas dans un fichier déclaratif versionneable. Cela bloque :

1. La réutilisabilité entre repos (chaque repo veut son propre pipeline)
2. La composabilité (un step peut dépendre d'un autre)
3. L'auditabilité NEXUS (pas de trace YAML dans `.nexus/` ni dans le WAL)
4. L'intégration CI/CD (`kiva cicd run` ne peut pas appeler `run_chain()` sans hard-code)

**Objectif de PRD-KIVA-008** : rendre les pipelines d'enchaînement KIVA **déclaratifs, versionnables et gouvernés par NEXUS**.

---

## 2. Objectifs

| # | Objectif | Mesure de succès |
|---|----------|------------------|
| O1 | Pipeline déclaratif en YAML | Fichier `.kiva/pipelines/<name>.yaml` lisible et validé |
| O2 | AutoChainManager pilotée par YAML | `run_chain()` résout le graphe et exécute dans l'ordre |
| O3 | CLI `kiva pipeline run <name>` | Commande opérationnelle avec `--dry-run` et `--env` |
| O4 | Guard `HAS_PIPELINE` | Vérifie l'existence du fichier avant exécution |
| O5 | Traçabilité WAL | Chaque exécution émet un événement `PIPELINE_RUN` dans le WAL |
| O6 | CI-safe mode | Pas d'interaction interactive en mode `--ci` |

---

## 3. Spécifications fonctionnelles

### F1 — Format déclaratif YAML (`.kiva/pipelines/<name>.yaml`)

```yaml
# .kiva/pipelines/build.yaml
# SOT: gerivdb/NEXUS
# Gouverné par: kiva pipeline run build

name: build
version: "1.0"
description: "Pipeline de build + test + nexus-sync pour BLO"
repo: BLO
nexus_status: ACTIVE

env:
  default:
    KIVA_ENV: dev
  ci:
    KIVA_ENV: ci
    KIVA_CI_SAFE: "true"

steps:
  - id: lint
    cmd: kiva script run lint
    description: "Lint du code source"
    on_failure: abort

  - id: test
    cmd: kiva script run tests
    description: "Suite de tests (pytest)"
    depends_on: [lint]
    on_failure: abort

  - id: nexus_sync
    cmd: kiva nexus tracking init {REPO} --path {REPO_PATH}
    description: "Sync .nexus/ tracking"
    depends_on: [test]
    on_failure: warn
    skip_if_exists: true

  - id: gate
    cmd: kiva gate check
    description: "Vérification phi-CPS gate"
    depends_on: [nexus_sync]
    on_failure: abort
```

**Règles du format** :
- `depends_on` : liste d'IDs de steps — résolution topologique (DAG)
- `on_failure` : `abort` | `warn` | `skip` | `continue`
- `skip_if_exists` : booléen — si le step a déjà un artefact attendu, sauter
- Variables d'interpolation : `{REPO}`, `{REPO_PATH}`, `{KIVA_ENV}`, `{INTENT_HASH}`
- Chemins de recherche des pipelines (par ordre de priorité) :
  1. `.kiva/pipelines/<name>.yaml` (repo local)
  2. `~/.kiva/pipelines/<name>.yaml` (user global)
  3. Built-in pipelines (`kiva_cli/pipelines/builtin/<name>.yaml`)

---

### F2 — AutoChainManager (extension de KIVA-007)

**Classe** : `kiva_cli/core/auto_chain_manager.py`

```python
class AutoChainManager:
    def load_pipeline(self, name: str, search_paths: list[Path]) -> Pipeline
    def validate(self, pipeline: Pipeline) -> ValidationResult
    def resolve_order(self, pipeline: Pipeline) -> list[Step]  # toposort DAG
    def run(self, pipeline: Pipeline, env: str, dry_run: bool, ci_safe: bool) -> ChainResult
    def emit_wal_event(self, result: ChainResult) -> None
```

**`ChainResult`** (dataclass) :
```python
@dataclass
class ChainResult:
    pipeline_name: str
    repo: str
    env: str
    steps_total: int
    steps_ok: int
    steps_skipped: int
    steps_failed: int
    duration_ms: int
    intent_hash: str
    timestamp: str
    aborted: bool
    abort_reason: Optional[str]
```

**Comportement de `resolve_order()`** :
- Construit un graphe orienté acyclique (DAG) depuis `depends_on`
- Lève `PipelineCycleError` si cycle détecté
- Retourne la liste triée par niveau (breadth-first topologique)

**Comportement de `run()`** :
- Exécute chaque step dans l'ordre résolu
- Respecte `on_failure` (abort coupe l'exécution, warn continue, skip saute)
- En mode `dry_run` : affiche la séquence sans exécuter
- En mode `ci_safe` : désactive toute interaction interactive, sort avec code 1 sur abort
- Injecte les variables d'env (`{REPO}`, `{REPO_PATH}`, etc.) dans chaque `cmd`

---

### F3 — Commande CLI `kiva pipeline`

**Nouveau groupe** : `kiva_cli/commands/pipeline_commands.py`

```
kiva pipeline
├── run <name>         Exécute un pipeline déclaratif
│   Options :
│     --env ENV        Contexte d'env (default: dev)
│     --dry-run        Affiche sans exécuter
│     --ci             Mode CI-safe (pas d'interactif, exit code strict)
│     --path PATH      Override du chemin repo (comme nexus tracking init)
│
├── list               Liste les pipelines disponibles (local + global + builtin)
├── validate <name>    Valide le YAML sans exécuter
└── show <name>        Affiche le DAG résolu (ordre d'exécution)
```

**Exemples d'usage** :
```powershell
# Exécution normale
kiva pipeline run build

# Mode CI (dans un script GitHub Actions / PowerShell)
kiva pipeline run build --env ci --ci

# Preview du DAG sans exécution
kiva pipeline run build --dry-run

# Validation du fichier YAML
kiva pipeline validate build

# Liste tous les pipelines disponibles
kiva pipeline list
```

---

### F4 — Guard `HAS_PIPELINE` + CI-safe

Extension du mécanisme guard de KIVA-007 :

```python
# kiva_cli/core/guards.py
def has_pipeline(name: str, search_paths: list[Path]) -> GuardResult:
    """Vérifie qu'un pipeline <name> est résolvable avant exécution."""
    ...

def ci_safe_guard(ctx: click.Context) -> None:
    """En mode --ci, abort si une commande tente une interaction utilisateur."""
    ...
```

**Comportement** :
- `HAS_PIPELINE` : si le pipeline n'est pas trouvé → message clair + liste des pipelines disponibles + `sys.exit(1)`
- `CI_SAFE` : monkey-patch `click.confirm()` et `click.prompt()` pour les remplacer par une erreur explicite en mode CI

---

### F5 — Traçabilité WAL

Chaque exécution de pipeline émet un événement dans le WAL global :

```json
{
  "event_type": "PIPELINE_RUN",
  "repo": "BLO",
  "pipeline_name": "build",
  "env": "dev",
  "steps_total": 4,
  "steps_ok": 4,
  "steps_failed": 0,
  "duration_ms": 1234,
  "intent_hash": "0x...",
  "timestamp": "2026-05-22T03:21:00Z",
  "aborted": false
}
```

---

## 4. Dépendances techniques

| Dépendance | Version / Source | Rôle |
|-----------|-----------------|------|
| `PyYAML` | `>=6.0` (déjà dans `pyproject.toml`) | Parsing YAML |
| `kiva_cli.core.auto_chain_manager` | KIVA-007 (DONE) | Base `run_chain()` |
| `kiva_cli.commands.wal_commands` | KIVA-CLI main | Émission WAL |
| `kiva_cli.commands.gate_command` | KIVA-CLI main | Intégration gate |
| `kiva_cli.commands.nexus_commands` | KIVA-008 (ce PRD) | Step nexus_sync |
| `graphlib` | stdlib Python 3.9+ | Toposort DAG |

> **Note** : `graphlib.TopologicalSorter` est disponible en stdlib Python ≥ 3.9. Pas de dépendance externe pour le DAG.

---

## 5. Fichiers à créer / modifier

| Fichier | Action | Description |
|---------|--------|-------------|
| `kiva_cli/commands/pipeline_commands.py` | **CRÉER** | Groupe CLI `kiva pipeline` |
| `kiva_cli/core/auto_chain_manager.py` | **MODIFIER** | Ajout `load_pipeline()`, `resolve_order()`, `emit_wal_event()` |
| `kiva_cli/core/pipeline_types.py` | **CRÉER** | Dataclasses `Pipeline`, `Step`, `ChainResult`, `ValidationResult` |
| `kiva_cli/core/guards.py` | **MODIFIER** | Ajout `has_pipeline()`, `ci_safe_guard()` |
| `kiva_cli/kiva.py` | **MODIFIER** | Import + enregistrement `pipeline_cli` → `"pipeline"` |
| `kiva_cli/pipelines/builtin/` | **CRÉER** | Dossier + pipelines built-in (ex: `default-build.yaml`) |
| `tests/test_pipeline_commands.py` | **CRÉER** | Tests unitaires F1-F4 |
| `tests/test_auto_chain_manager.py` | **MODIFIER** | Ajout tests `load_pipeline`, `resolve_order`, DAG cycle |

---

## 6. Critères d'acceptation

| ID | Critère | Validation |
|----|---------|------------|
| AC-1 | `kiva pipeline run build --dry-run` affiche le DAG résolu sans exécuter | Test manuel + test unitaire |
| AC-2 | Un pipeline avec `depends_on` cyclique lève `PipelineCycleError` | `test_auto_chain_manager.py::test_cycle_detection` |
| AC-3 | `on_failure: abort` arrête l'exécution au premier step en erreur | `test_pipeline_commands.py::test_abort_on_failure` |
| AC-4 | `on_failure: warn` continue et note l'erreur dans `ChainResult` | `test_pipeline_commands.py::test_warn_on_failure` |
| AC-5 | `kiva pipeline run build --ci` sort avec code 1 si abort | Test CI (subprocess) |
| AC-6 | Chaque run émet un événement `PIPELINE_RUN` dans le WAL | `test_pipeline_commands.py::test_wal_event_emitted` |
| AC-7 | `kiva pipeline list` liste les pipelines des 3 niveaux (local/global/builtin) | Test manuel |
| AC-8 | Variables `{REPO}`, `{REPO_PATH}`, `{KIVA_ENV}` interpolées correctement | `test_pipeline_types.py::test_interpolation` |
| AC-9 | Guard `HAS_PIPELINE` sort avec message clair si pipeline introuvable | `test_auto_chain_manager.py::test_has_pipeline_missing` |
| AC-10 | `kiva pipeline validate build` échoue proprement sur YAML invalide | `test_pipeline_commands.py::test_validate_invalid_yaml` |

---

## 7. Contraintes & hors-scope

### Dans le scope
- Exécution locale uniquement (pas de remote runner)
- DAG simple (steps + depends_on) — pas de conditions `if/when` (reporté à KIVA-009)
- Pipelines stockés en YAML local — pas de pull depuis NEXUS remote (reporté à KIVA-010)

### Hors scope (KIVA-009+)
- Conditions dynamiques (`when: env == 'prod'`)
- Parallelisme entre steps indépendants
- Planification temporelle (cron)
- Remote pipeline registry (NEXUS-hosted)
- UI dashboard `kiva dashboard pipeline`

---

## 8. Plan d'implémentation

| Sprint | Étape | Fichiers | Durée estimée |
|--------|-------|----------|---------------|
| Sprint 1 | Types + parser YAML (F1) | `pipeline_types.py`, `auto_chain_manager.py` (load + validate) | ~1h |
| Sprint 2 | DAG resolver + run() (F2) | `auto_chain_manager.py` (resolve_order, run) | ~1h |
| Sprint 3 | CLI `kiva pipeline` (F3) | `pipeline_commands.py`, `kiva.py` | ~30min |
| Sprint 4 | Guards + WAL (F4 + F5) | `guards.py`, `wal_commands.py` | ~30min |
| Sprint 5 | Tests (AC-1 à AC-10) | `tests/test_pipeline_*` | ~1h |

**Total estimé** : ~4h

---

## 9. Gouvernance NEXUS

| Champ | Valeur |
|-------|--------|
| `Canonical_Source` | `gerivdb/NEXUS` |
| `Repo` | `gerivdb/KIVA-CLI` |
| `Entity_Type` | `PRD` |
| `Nexus_Status` | `DRAFT` |
| `Last_Synced_At` | `2026-05-22T03:21:00Z` |
| `Conflict_Flag` | `false` |
| `Operational_Owner` | `gerivdb` |

---

## 10. Historique

| Date | Changement | Auteur |
|------|------------|--------|
| 2026-05-22 | Création (DRAFT) | gerivdb / KIVA |
