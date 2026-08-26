---
id: PRD-006
title: PRD-KIVA-006 — NEXUS Sync Governance Layer (KIVA-CLI)
repo: unknown
status: draft
created: '2026-06-11'
author: gerivdb
type: '"PRD"'
version: '"1.0"'
date: '2026-06-11'
intent_hash: 0xPRD_PRD_006_KIVA_006_NEXUS_SYNC_GO_20260611
---

# PRD-KIVA-006 — NEXUS Sync Governance Layer (KIVA-CLI)

**Scope** : `KIVA-CLI` (mono-repo)  
**Statut** : `ACTIVE`  
**Priorité** : P1  
**Date** : 2026-05-21  
**Dépendance** : [PRD-XECO-001](../../ECOYSTEM/PRD/PRD-XECO-001-nexus-sync-agent-v2.md) — DONE ✅  
**Chemin dans INDEX** : `KIVA-CLI/PRD/PRD-KIVA-006-nexus-sync-governance.md`

---

## Contexte

Le NEXUS Sync Agent v2 (XECO-001) est implémenté dans `gerivdb/NEXUS` avec son moteur Python et son wrapper PowerShell. Ce PRD décrit la **couche d'intégration KIVA-CLI** : exposer cet agent via le CLI (`kiva cicd nexus-sync`) et le CI (`ecosystem_sync.yml`) de façon uniforme, en partageant le même moteur.

---

## Features

### F1 — `nexus_sync_orchestrator.py`

**Fichier** : `kiva_cli/core/nexus_sync_orchestrator.py`

Orchestrator Python qui :
- Localise le checkout NEXUS local via le registre ECOS (`repos.json`) ou le path par défaut (`D:/DO/WEB/L0-CANON/NEXUS`)
- Invoque `tools/sync_agent_v2.py reconcile [--dry-run] [--repo X]`
- Retourne un `NexusSyncResult` structuré (success, report_path, stdout, stderr, returncode)

### F2 — Commande `kiva cicd nexus-sync`

**Fichier** : `kiva_cli/commands/cicd_commands.py`

Commande Click ajoutée au groupe `cicd` :
```
kiva cicd nexus-sync [--dry-run] [--repo <NOM>]
```
- `--dry-run` activé par défaut
- Affiche le chemin du rapport généré si présent
- Exit code 1 si échec

### F3 — Step CI dans `ecosystem_sync.yml`

**Fichier** : `.github/workflows/ecosystem_sync.yml`

Step `NEXUS Sync v2 — Reconcile (dry-run)` ajouté après le commit ECOYSTEM :
- Appelle `python -m kiva_cli.commands.cicd_commands nexus-sync --dry-run`
- `continue-on-error: true` (ne bloque pas le CI si NEXUS absent du runner)
- Upload de l'artifact `nexus-reconciliation-{run_id}`
- Utilise `vars.ECOS_ROOT` pour le path (configurable en Settings GitHub)

---

## Critères d'acceptation

- [ ] `kiva cicd nexus-sync --dry-run` s'exécute sans erreur quand NEXUS est présent localement
- [ ] `kiva cicd nexus-sync --dry-run` retourne un message d'erreur clair (pas une exception) quand NEXUS est absent
- [ ] Le rapport `reports/reconciliation_*.md` est bien détecté et affiché
- [ ] Le step CI `nexus_sync` ne bloque pas le workflow si NEXUS est absent du runner
- [ ] Tests unitaires couvrent : path resolution, dry-run, repo_filter, NEXUS absent, script absent

---

## Plan d'implémentation

| Phase | Feature | Statut |
|---|---|---|
| 1 | F1 — NexusSyncOrchestrator | ✅ DONE |
| 2 | F2 — `kiva cicd nexus-sync` | ✅ DONE |
| 3 | F3 — ecosystem_sync.yml step | ✅ DONE |
| 4 | Tests unitaires | 🔄 EN COURS |

---

## Historique

| Date | Changement |
|---|---|
| 2026-05-21 | PRD créé, scope défini, dépendance XECO-001 établie |
| 2026-05-21 | F1 implémenté — `nexus_sync_orchestrator.py` pushé sur main (`f43418b`) |
| 2026-05-21 | F3 implémenté — step CI pushé sur main (`23139ff`) |
| 2026-05-22 | PRD pushé dans KIVA-CLI/PRD/ |
