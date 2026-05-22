# PRD KIVA-012 — Pipelines as First-Class Nexus Citizens

**Status** : DONE  
**Version** : 1.0  
**Date** : 2026-05-22  
**Owner** : gerivdb  
**Nexus_Status** : CONFORME_NEXUS  
**Depends on** : KIVA-008, KIVA-009, KIVA-010, KIVA-011  
**Closed** : 2026-05-22T07:04Z  
**Commits** : 750bdfe (S1) → a6f3861 (S2) → 2a57f1d (S3) → S4  

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
- Commandes `kiva nexus pipeline list|show|validate|history|drift|prune`
- Intégration `nexus drift check` : nouveau signal `pipeline_drift` (schema_hash changé
  depuis last_success)
- Détection et nettoyage de pipelines orphelins (aucun run en WAL, ou `operational_owner` absent)

### Out of scope (KIVA-013+)

- Scheduling / cron
- Templates de pipelines
- Marketplace / sharing
- Notifications externes (Slack, webhook)

---

## 4. Acceptance Criteria

| ID | Critère | Sprint | Statut |
|----|---------|--------|--------|
| AC-K12-1 | `kiva nexus pipeline list` liste tous les `.yaml` de `.kiva/pipelines/` avec `name`, `version`, `nexus_status`, `step_count`, `last_run` | S1 | ✅ |
| AC-K12-2 | `kiva nexus pipeline show <name>` affiche les métadonnées complètes d'un pipeline (dont `success_rate`, `avg_duration_s`, `last_intent_hash`, `last_success_at`) | S2 | ✅ |
| AC-K12-3 | `kiva nexus pipeline validate <name>` retourne exit 0 si DAG valide + schéma conforme, exit 1 sinon, exit 2 si fichier absent | S1 | ✅ |
| AC-K12-4 | `kiva nexus pipeline history <name>` affiche les N derniers runs WAL filtrés par pipeline name | S2 | ✅ |
| AC-K12-5 | Chaque `kiva pipeline run <name>` enregistre un `PIPELINE_RUN` enrichi dans le registry (last_run, last_status, duration, last_success_at) | S2 | ✅ |
| AC-K12-6 | `kiva nexus drift check` détecte le signal `pipeline_drift` si le `schema_hash` du YAML a changé depuis le `last_success` | S3 | ✅ |
| AC-K12-7 | `kiva nexus pipeline prune [--dry-run] [--force] [--name N]` liste et supprime les pipelines orphelins (jamais exécutés, sans owner, ou inactifs > 30j) | S4 | ✅ |
| AC-K12-8 | `PipelineRecord` est sérialisable en JSON et rechargeable sans perte (round-trip) | S1 | ✅ |
| AC-K12-9 | Tous les chemins couverts par des tests unitaires (≥ 80% coverage sur les nouveaux modules) — 44/44 verts | S1–S4 | ✅ |

---

## 5. Découpage en Sprints

### S1 — Foundation : PipelineRecord + Registry store + pipeline list/validate ✅

**Commit** : `750bdfe`  
**Tests** : 29/29  
**Livrables** :

1. `kiva_cli/core/pipeline_registry.py`
   - `PipelineRecord` dataclass (tous les champs y compris `last_success_at`)
   - `PipelineRegistryStore` : lecture/écriture atomique JSON (write-then-rename)
   - `upsert_record` + `get_record` + `list_records` + `find_orphans` + `delete_record`
   - `compute_schema_hash(yaml_path)` avec fallback si PyYAML absent
   - `discover_pipelines(root)` — scanne `.kiva/pipelines/*.yaml`, retour trié

2. `kiva nexus pipeline list [--pipelines-dir PATH] [--json]`
3. `kiva nexus pipeline validate <name>` — exit 0/1/2
4. `tests/test_pipeline_registry.py` — AC-K12-8 + AC-K12-9 partiel

---

### S2 — Runtime integration : enregistrement post-run + show + history ✅

**Commit** : `a6f3861`  
**Tests** : 33/33  
**Livrables** :

1. `PipelineRegistryStore.record_run(name, status, duration_s, intent_hash)`
   - Rolling average `avg_duration_s`
   - `last_success_at` mis à jour uniquement sur `SUCCESS`
   - Auto-create si pipeline inconnu
   - Non bloquant dans `pipeline_runner.py` (try/except → warn)

2. `kiva nexus pipeline show <name>` — métadonnées complètes + success_rate
3. `kiva nexus pipeline history <name> [--limit N]` — filtre WAL client-side
4. Tests `TestRecordRun` : 4 cas (success, failure, rolling avg, auto-create)

---

### S3 — Drift detection : schema_hash + `pipeline drift` command ✅

**Commit** : `2a57f1d`  
**Tests** : 39/39  
**Livrables** :

1. `PipelineRegistryStore.compute_drift_report(pipelines_root)` :
   - YAML courant vs `schema_hash` du dernier SUCCESS
   - Cas : stable, drifted, MISSING (YAML supprimé), UNREGISTERED (jamais exécuté)
   - Tri : driftés en premier

2. `kiva nexus pipeline drift [--pipelines-dir PATH] [--json] [--fail-on-drift]`
   - Exit 0 / 1 (drift) / 2 (store inaccessible)
   - Sortie riche : tableau stable vs drift avec `last_success_at`

3. Section `--- Pipeline schema drift ---` intégrée dans `kiva nexus drift check`
4. Tests `TestComputeDriftReport` : 6 cas

---

### S4 — Orphan cleanup : `pipeline prune` ✅

**Tests** : 44/44  
**Livrables** :

1. `kiva nexus pipeline prune [--dry-run] [--force] [--name N] [--json]`
   - Cible auto : `find_orphans()` (total_runs=0, no owner, inactif >30j)
   - Cible manuelle : `--name` (répétable, cible même les non-orphelins)
   - Raison inline dans le tableau d'affichage (`_orphan_reason()`)
   - Confirmation interactive sauf `--force`
   - Exit 0 / 1 (annulé) / 2 (store inaccessible)

2. Helpers : `_orphan_reason(rec)`, `_confirm_prune(targets)`
3. Tests `TestPipelinePruneCLI` : 5 cas CliRunner (dry-run, force, clean, name filter, json)

---

## 6. Architecture finale livrée

```
kiva_cli/
  core/
    pipeline_registry.py        ← NOUVEAU S1 (PipelineRecord, Store, helpers)
    pipeline_runner.py          ← modifié S2 (hook post-run non-bloquant)
  commands/
    nexus_commands.py           ← modifié S1–S4 (nexus pipeline subgroup complet)

~/.kiva/
  global_wal.db                 ← existant
  pipeline_registry.json        ← NOUVEAU S1 — store JSON atomique

.kiva/pipelines/
  build.yaml                    ← existant
  blo-validate.yaml             ← existant

tests/
  test_pipeline_registry.py     ← NOUVEAU S1 — 44 tests (S1–S4)
```

**Surface CLI complète** :
```
kiva nexus pipeline list        [--pipelines-dir] [--json]
kiva nexus pipeline show        <name>
kiva nexus pipeline validate    <name>
kiva nexus pipeline history     <name> [--limit N]
kiva nexus pipeline drift       [--pipelines-dir] [--json] [--fail-on-drift]
kiva nexus pipeline prune       [--dry-run] [--force] [--name N] [--json]
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
| `click.testing.CliRunner` | Tests CLI S4 |

---

## 8. Risques (bilan)

| Risque | Probabilité | Mitigation | Statut |
|--------|-------------|------------|--------|
| `pipeline_registry.json` corrompu (crash mid-write) | Faible | Write-then-rename atomique | ✅ implémenté |
| Hook post-run bloque le runner | Faible | Try/except + log, jamais re-raise | ✅ implémenté |
| `schema_hash` false-positive (whitespace YAML) | Moyen | Normaliser le YAML avant hash (strip + sort keys) | ✅ implémenté |
| Performance `list` avec beaucoup de YAMLs | Faible | Lazy load : ne parse que si pas en cache | ✅ acceptable en V1 |

---

## 9. Definition of Done

- [x] Tous les AC (AC-K12-1 à AC-K12-9) validés
- [x] `kiva nexus pipeline list` fonctionne sur `build.yaml` + `blo-validate.yaml`
- [x] `kiva pipeline run build --dry-run` met à jour le registry (total_runs++)
- [x] `kiva nexus drift check` affiche la section `--- Pipeline schema drift ---`
- [x] Tests : ≥ 80% coverage sur `pipeline_registry.py` (88% mesuré)
- [x] PRD mis à jour : `Status: DONE`, `Nexus_Status: CONFORME_NEXUS`
- [x] `kiva nexus pipeline prune` opérationnel (S4, hors scope PRD initial — livré en bonus)

---

*Ce PRD est gouverné par NEXUS (gerivdb/NEXUS). SOT: ECOS_ROOT.json.*
