# PRD KIVA-012 — Pipelines as First-Class Nexus Citizens

**Status** : DRAFT  
**Version** : 0.1  
**Date** : 2026-05-22  
**Owner** : gerivdb  
**Nexus_Status** : À_VALIDER_NEXUS  
**Depends on** : KIVA-008, KIVA-009, KIVA-010, KIVA-011  

---

## 1. Contexte

Après KIVA-011, les pipelines KIVA sont des objets riches : DAG, conditions `when:`, retry,
`on_failure: notify`, et drift detection via le WAL. Cependant ils restent **stateless du
point de vue de la gouvernance** : aucun enregistrement dans le WAL au chargement, aucune
traçabilité inter-runs, aucune métadonnée agrégée accessible via CLI.

KIVA-012 élève les pipelines au même niveau de gouvernance que les skills, daemons et
citizens : chaque pipeline devient un **citoyen NEXUS tracké, auditable et gouverné**.

---

## 2. Objectif principal

Permettre à n'importe quel opérateur de répondre en une commande aux questions :

- Quels pipelines existent dans cet environnement ?
- Quel est l'état de santé de chacun (last_success, success_rate, drift) ?
- Est-ce qu'un pipeline a changé depuis sa dernière exécution réussie ?
- Quel pipeline est orphelin (jamais exécuté, ou sans owner déclaré) ?

---

## 3. Périmètre

### In scope

- Découverte automatique des `.yaml` dans `.kiva/pipelines/`
- Enregistrement WAL à chaque `load_pipeline()` significatif (`PIPELINE_REGISTERED`,
  `PIPELINE_UPDATED`)
- Dataclass `PipelineRecord` : métadonnées agrégées par pipeline (last_run, last_success,
  success_rate, avg_duration_s, last_intent_hash, step_count, schema_hash)
- Store local léger `~/.kiva/pipeline_registry.json` (lecture/écriture atomique)
- Commandes `kiva nexus pipeline list|show|validate|history`
- Intégration `nexus drift check` : nouveau signal `pipeline_drift` (schema_hash changé
  depuis last_success)
- Détection de pipelines orphelins (aucun run en WAL, ou `operational_owner` absent)

### Out of scope (KIVA-013+)

- Scheduling / cron
- Templates de pipelines
- Marketplace / sharing
- Notifications externes (Slack, webhook)

---

## 4. Acceptance Criteria

| ID | Critère | Sprint |
|----|---------|--------|
| AC-K12-1 | `kiva nexus pipeline list` liste tous les `.yaml` de `.kiva/pipelines/` avec `name`, `version`, `nexus_status`, `step_count`, `last_run` | S1 |
| AC-K12-2 | `kiva nexus pipeline show <name>` affiche les métadonnées complètes d'un pipeline (dont `success_rate`, `avg_duration_s`, `last_intent_hash`) | S2 |
| AC-K12-3 | `kiva nexus pipeline validate <name>` retourne exit 0 si DAG valide + schéma conforme, exit 1 sinon | S1 |
| AC-K12-4 | `kiva nexus pipeline history <name>` affiche les N derniers runs WAL filtrés par pipeline name | S2 |
| AC-K12-5 | Chaque `kiva pipeline run <name>` enregistre un `PIPELINE_RUN` enrichi dans le registry (last_run, last_status, duration) | S2 |
| AC-K12-6 | `kiva nexus drift check` détecte le signal `pipeline_drift` si le `schema_hash` du YAML a changé depuis le `last_success` | S3 |
| AC-K12-7 | `kiva nexus pipeline list --orphan` liste les pipelines sans run en WAL ou sans `operational_owner` | S3 |
| AC-K12-8 | `PipelineRecord` est sérialisable en JSON et rechargeable sans perte (round-trip) | S1 |
| AC-K12-9 | Tous les chemins couverts par des tests unitaires (≥ 80% coverage sur les nouveaux modules) | S1–S3 |

---

## 5. Découpage en Sprints

### S1 — Foundation : PipelineRecord + Registry store + pipeline list/validate

**Durée estimée** : 1 session  
**Livrables** :

1. `kiva_cli/core/pipeline_registry.py`
   - `PipelineRecord` dataclass : `name`, `version`, `nexus_status`, `schema_hash`,
     `step_count`, `last_run_at`, `last_status`, `last_intent_hash`, `avg_duration_s`,
     `total_runs`, `success_runs`, `operational_owner`, `registered_at`
   - `PipelineRegistryStore` : lecture/écriture atomique JSON dans
     `~/.kiva/pipeline_registry.json` (thread-safe via `FileLock` ou write-then-rename)
   - `upsert_record(record)` + `get_record(name)` + `list_records()` + `find_orphans()`

2. `kiva nexus pipeline list` (sous-groupe `kiva nexus pipeline`)
   - Scanne `.kiva/pipelines/*.yaml`, charge chaque pipeline via `load_pipeline()`
   - Croise avec le store pour afficher `last_run`, `last_status`, `success_rate`
   - Option `--json` pour sortie machine-readable

3. `kiva nexus pipeline validate <name>`
   - Réutilise `detect_cycles()` + validation schéma du loader
   - Exit code 0/1 propre (idempotent, utilisable en pre-commit hook)

4. `tests/test_pipeline_registry.py` (AC-K12-8 + AC-K12-9 partiel)

**Contrats de données** :
```python
@dataclass
class PipelineRecord:
    name: str
    version: str = "1"
    nexus_status: str = "DRAFT"
    schema_hash: str = ""        # sha256(yaml_content)[:16]
    step_count: int = 0
    last_run_at: Optional[str] = None
    last_status: Optional[str] = None
    last_intent_hash: Optional[str] = None
    avg_duration_s: float = 0.0
    total_runs: int = 0
    success_runs: int = 0
    last_success_at: Optional[str] = None  # ISO du dernier SUCCESS (pour S3 drift)
    operational_owner: str = "gerivdb"
    registered_at: str = ""
```

---

### S2 — Runtime integration : enregistrement post-run + show + history

**Durée estimée** : 1 session  
**Livrables** :

1. Hook post-run dans `pipeline_runner.run_pipeline()` :
   - Après chaque run, appelle `PipelineRegistryStore.upsert_record()` avec les
     métriques du `PipelineResult` (status, duration, intent_hash)
   - Met à jour `avg_duration_s` via rolling average (formule : `avg = avg + (new - avg) / n`)
   - Non bloquant : exception dans le hook → log warning, pipeline result inchangé

2. `kiva nexus pipeline show <name>`
   - Affiche toutes les métadonnées `PipelineRecord` + last 3 runs depuis WAL
   - Colonne `schema_hash` pour détecter manuellement si le YAML a changé

3. `kiva nexus pipeline history <name> [--limit N]`
   - Wrapper sur `wal.query_events()` filtré par `pipeline_name` dans le metadata
   - Affiche : timestamp, status, duration, intent_hash, steps_skipped

4. Tests : AC-K12-2, AC-K12-4, AC-K12-5

---

### S3 — Drift + Orphan detection

**Durée estimée** : 1 session  
**Livrables** :

1. Signal `pipeline_drift` dans `nexus drift check` :
   - Compare `schema_hash` du YAML courant vs `schema_hash` du dernier run SUCCESS
   - Si différent → affiche `[DRIFT] <name> schema modifié depuis last_success`
   - Peut être supprimé avec `--ignore-schema-drift`

2. `kiva nexus pipeline list --orphan`
   - Critères orphelin :
     a. `total_runs == 0` (jamais exécuté)
     b. `operational_owner` absent ou vide
     c. Aucun run WAL dans les 30 derniers jours

3. Enrichissement `kiva nexus drift check` : nouvelle section `--- Pipelines ---`
   affichant le résumé schema_drift + orphan count

4. Tests : AC-K12-6, AC-K12-7, AC-K12-9 final

---

## 6. Architecture cible

```
kiva_cli/
  core/
    pipeline_registry.py        ← NOUVEAU (S1)
    pipeline_runner.py          ← modifié S2 (hook post-run)
  commands/
    nexus_commands.py           ← modifié S1+S3 (nexus pipeline + drift signal)

~/.kiva/
  global_wal.db                 ← existant
  pipeline_registry.json        ← NOUVEAU (S1) — store JSON local

.kiva/pipelines/
  build.yaml                    ← existant
  blo-validate.yaml             ← existant
```

---

## 7. Dépendances techniques

| Module | Usage |
|--------|-------|
| `pipeline_loader.load_pipeline()` | Chargement + schema_hash |
| `GlobalWALManager.query_events()` | history + drift |
| `pipeline_runner.run_pipeline()` | Hook post-run |
| `nexus_commands.drift_check` | Signal pipeline_drift |
| `json` + `pathlib` | Store JSON atomic write |

---

## 8. Risques

| Risque | Probabilité | Mitigation |
|--------|-------------|------------|
| `pipeline_registry.json` corrompu (crash mid-write) | Faible | Write-then-rename atomique |
| Hook post-run bloque le runner | Faible | Try/except + log, jamais re-raise |
| `schema_hash` false-positive (whitespace YAML) | Moyen | Normaliser le YAML avant hash (strip + sort keys) |
| Performance `list` avec beaucoup de YAMLs | Faible | Lazy load : ne parse que si pas en cache |

---

## 9. Definition of Done

- [ ] Tous les AC (AC-K12-1 à AC-K12-9) validés
- [ ] `kiva nexus pipeline list` fonctionne sur `build.yaml` + `blo-validate.yaml`
- [ ] `kiva pipeline run build --dry-run` met à jour le registry (total_runs++)
- [ ] `kiva nexus drift check` affiche la section `--- Pipelines ---`
- [ ] Tests : ≥ 80% coverage sur `pipeline_registry.py`
- [ ] PRD mis à jour : `Status: DONE`, `Nexus_Status: CONFORME_NEXUS`

---

*Ce PRD est gouverné par NEXUS (gerivdb/NEXUS). SOT: ECOS_ROOT.json.*
