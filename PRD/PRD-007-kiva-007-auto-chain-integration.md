---
id: PRD-007
title: "PRD-KIVA-007 — AutoChain Integration Layer (KIVA-CLI)"
repo: unknown
status: draft
created: "2026-06-11"
author: gerivdb
---
# PRD-KIVA-007 — AutoChain Integration Layer (KIVA-CLI)

## Métadonnées

| Champ | Valeur |
|---|---|
| **Repo cible** | `KIVA-CLI` |
| **Destination** | `KIVA-CLI/PRD/` |
| **Transversalité** | NON (mono-repo) |
| **Repos impactés** | KIVA-CLI |
| **Priorité** | P1 |
| **Epic parent** | N/A |
| **Dépend de** | PRD-KIVA-006 (NEXUS Sync Governance) — DONE ✅ |
| **Dépend de** | PRD-XECO-001 (NEXUS Sync Agent v2) — DONE ✅ |
| **Statut** | **DONE** |
| **Auteur** | @gerivdb |
| **Date création** | 2026-05-22 |
| **Dernière mise à jour** | 2026-05-22 |

---

## Implémentation (DONE)

| Feature | Fichier | Commit | SHA fichier |
|---|---|---|---|
| F1 — Guard `HAS_AUTOCHAIN` + `_try_import_autochain()` | `kiva_cli/core/nexus_sync_orchestrator.py` | `e21e443` | `35e4f126` |
| F2 — Méthode `run_chain()` + `_find_latest_report()` | `kiva_cli/core/nexus_sync_orchestrator.py` | `e21e443` | `35e4f126` |
| F3 — Flag `--chain` + routing + warning CLI | `kiva_cli/commands/cicd_commands.py` | `640eac6` | `48ef2274` |
| F4 — Step CI renommé + commentaire CI-safe + fix report path | `.github/workflows/ecosystem_sync.yml` | `5f09ff9` | `47bc7d7c` |

---

## Contexte et problème

### Ce qui existe (dépendances satisfaites)

**PRD-XECO-001 (DONE)** — NEXUS contient deux composants AutoChain :

| Fichier NEXUS | Classe | Rôle |
|---|---|---|
| `entities/auto_chain_manager.py` | `AutoChainManager` | Gestionnaire de chaînes déclaratives (create, execute, trigger) |
| `auto_chain_executor.py` | `AutoChainExecutor` | Exécuteur async de phases EPIC (Foundation → Convergence → Citizenship → Optimization) |

**PRD-KIVA-006 (DONE)** — KIVA-CLI expose :
- `kiva_cli/core/nexus_sync_orchestrator.py` — orchestre le sync via `subprocess.run` vers NEXUS
- `kiva cicd nexus-sync [--dry-run]` — commande CLI
- `ecosystem_sync.yml` — step CI avec `continue-on-error: true`

### Le problème

Actuellement, `NexusSyncOrchestrator` faisait un `subprocess.run` basique vers le script NEXUS. Il ne pouvait pas :

1. **Importer les classes AutoChain de NEXUS** directement (pas de `sys.path` cross-repo)
2. **Chaîner des étapes déclarativement** (resolve → reconcile → audit → report)
3. **Gérer les erreurs de façon granulaire** (retry, fallback, skip non-critique)
4. **Adapter le comportement CLI vs CI** (NEXUS présent localement vs absent du runner)

---

## Architecture implémentée

### Pattern d'import dynamique (B modifié)

```python
# kiva_cli/core/nexus_sync_orchestrator.py

HAS_AUTOCHAIN: bool = False
AutoChainManager = None

def _try_import_autochain(nexus_path: Optional[Path]) -> bool:
    global HAS_AUTOCHAIN, AutoChainManager
    original_sys_path = list(sys.path)
    try:
        sys.path.insert(0, str(nexus_path))
        from entities.auto_chain_manager import AutoChainManager as _ACM
        AutoChainManager = _ACM
        HAS_AUTOCHAIN = True
        return True
    except Exception:
        return False
    finally:
        sys.path[:] = original_sys_path  # restauration propre
```

| Environnement | `HAS_AUTOCHAIN` | Comportement |
|---|---|---|
| CLI local (NEXUS présent) | `True` | Import direct, chaînes déclaratives |
| CLI local (NEXUS absent) | `False` | Fallback `subprocess.run` |
| CI runner (NEXUS absent) | `False` | Fallback `subprocess.run` + `continue-on-error` |

---

## Chaînes déclaratives implémentées

### Chaîne 1 : `nexus-sync` (obligatoire)

| Étape | Type | Cible | Description |
|---|---|---|---|
| `resolve` | tool | `_resolve_nexus_path()` | Localise le checkout NEXUS |
| `reconcile` | tool | `run_reconcile` | Exécute `sync_agent_v2.py reconcile` |
| `report` | tool | `generate_report` | Récupère le rapport généré |

**Error handling** : `stop_on_error`

### Chaîne 2 : `kiva-pipeline` (optionnelle, `critical=False`) — hors scope KIVA-007

Réservée pour KIVA-008 si nécessaire.

---

## Critères d'acceptation

```gherkin
Given NEXUS est présent localement
When l'utilisateur exécute "kiva cicd nexus-sync --chain --dry-run"
Then AutoChainManager est importé avec succès
And la chaîne "nexus-sync" est exécutée (resolve → reconcile → report)
And le rapport est affiché

Given NEXUS est absent (ou CI runner)
When l'utilisateur exécute "kiva cicd nexus-sync --chain --dry-run"
Then un avertissement "⚠️ AutoChain non disponible" est affiché
And le fallback run() classique est utilisé
And le sync fonctionne quand même

Given NEXUS est absent
When l'utilisateur exécute "kiva cicd nexus-sync --dry-run" (sans --chain)
Then aucun import AutoChain n'est tenté
And le mode subprocess.run classique est utilisé directement

Given le workflow ecosystem_sync.yml est déclenché
When le step "NEXUS Sync v2" s'exécute
Then le mode sans --chain est utilisé (pas d'import AutoChain)
And continue-on-error protège le workflow
```

---

## Références

- PRD-KIVA-006 — NEXUS Sync Governance Layer (DONE)
- PRD-XECO-001 — NEXUS Sync Agent v2 (DONE)
- `gerivdb/NEXUS` `entities/auto_chain_manager.py` — `AutoChainManager`
- `gerivdb/NEXUS` `auto_chain_executor.py` — `AutoChainExecutor`

---

**Fin du PRD-KIVA-007**
