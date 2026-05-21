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
| **Statut** | DRAFT |
| **Auteur** | @gerivdb |
| **Date création** | 2026-05-22 |
| **Dernière mise à jour** | 2026-05-22 |

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

Actuellement, `NexusSyncOrchestrator` fait un `subprocess.run` basique vers le script NEXUS. Il ne peut pas :

1. **Importer les classes AutoChain de NEXUS** directement (pas de `sys.path` cross-repo)
2. **Chaîner des étapes déclarativement** (resolve → reconcile → audit → report)
3. **Gérer les erreurs de façon granulaire** (retry, fallback, skip non-critique)
4. **Adapter le comportement CLI vs CI** (NEXUS présent localement vs absent du runner)

### Objectif de KIVA-007

Créer une **couche d'intégration AutoChain** dans KIVA-CLI qui :

- Importe dynamiquement `AutoChainManager` depuis le checkout NEXUS local
- Utilise un guard `HAS_AUTOCHAIN` pour fonctionner en mode dégradé (CLI local vs CI)
- Expose des chaînes déclaratives pour `nexus-sync` et `kiva cicd run`
- Garantit que CLI et CI partagent le **même moteur** (pattern KIVA-006)

---

## Architecture

### Pattern d'import dynamique (B modifié)

```python
# kiva_cli/core/nexus_sync_orchestrator.py

HAS_AUTOCHAIN = False
AutoChainManager = None

try:
    nexus_path = self._resolve_nexus_path()
    if nexus_path:
        sys.path.insert(0, str(nexus_path))
        from entities.auto_chain_manager import AutoChainManager
        HAS_AUTOCHAIN = True
except (ImportError, TypeError, OSError):
    pass  # Fallback: subprocess.run (mode KIVA-006)
```

| Environnement | `HAS_AUTOCHAIN` | Comportement |
|---|---|---|
| CLI local (NEXUS présent) | `True` | Import direct, chaînes déclaratives |
| CLI local (NEXUS absent) | `False` | Fallback `subprocess.run` |
| CI runner (NEXUS absent) | `False` | Fallback `subprocess.run` + `continue-on-error` |

---

## Features

### F1 — Import dynamique + guard `HAS_AUTOCHAIN`

**Fichier** : `kiva_cli/core/nexus_sync_orchestrator.py` (modification)

Ajouter au module level :

```python
import sys

HAS_AUTOCHAIN = False
AutoChainManager = None

def _try_import_autochain(nexus_path: Path) -> bool:
    """Tente d'importer AutoChainManager depuis NEXUS local."""
    global HAS_AUTOCHAIN, AutoChainManager
    try:
        sys.path.insert(0, str(nexus_path))
        from entities.auto_chain_manager import AutoChainManager
        HAS_AUTOCHAIN = True
        return True
    except (ImportError, TypeError, OSError):
        return False
```

Cette fonction est appelée dans `__init__` après `_resolve_nexus_path()`.

### F2 — Chaîne déclarative `nexus-sync`

**Fichier** : `kiva_cli/core/nexus_sync_orchestrator.py` (nouvelle méthode)

```python
def run_chain(
    self,
    dry_run: bool = True,
    repo_filter: Optional[str] = None,
) -> NexusSyncResult:
    """
    Exécute la chaîne nexus-sync via AutoChainManager si disponible,
    sinon fallback sur run() classique.
    """
    if not HAS_AUTOCHAIN:
        # Fallback KIVA-006
        return self.run(dry_run=dry_run, repo_filter=repo_filter)

    manager = AutoChainManager()

    # Définition de la chaîne
    manager.create_chain(
        chain_id="nexus-sync",
        name="NEXUS Sync Governance",
        steps=[
            {"name": "resolve", "type": "tool", "target": "resolve_nexus_path"},
            {"name": "reconcile", "type": "tool", "target": "run_reconcile"},
            {"name": "report", "type": "tool", "target": "generate_report"},
        ],
        error_handling="stop_on_error",
    )

    success = manager.execute_chain("nexus-sync", context={
        "dry_run": dry_run,
        "repo_filter": repo_filter,
    })

    return NexusSyncResult(
        success=success,
        dry_run=dry_run,
        repo_filter=repo_filter,
        report_path=self._find_latest_report(),
    )
```

### F3 — Commande `kiva cicd nexus-sync --chain`

**Fichier** : `kiva_cli/commands/cicd_commands.py` (ajout)

```python
@cicd_cli.command(name='nexus-sync')
@click.option("--dry-run", is_flag=True, default=True, show_default=True)
@click.option("--repo", default=None, metavar="REPO")
@click.option("--chain", is_flag=True, default=False,
              help="Use AutoChain (requires NEXUS local)")
@click.pass_context
def nexus_sync(ctx, dry_run: bool, repo: str | None, chain: bool):
    """Lance le NEXUS Sync Agent v2 (PRD-KIVA-006/007)."""
    from kiva_cli.core.nexus_sync_orchestrator import NexusSyncOrchestrator, HAS_AUTOCHAIN

    orch = NexusSyncOrchestrator()

    if chain and HAS_AUTOCHAIN:
        result = orch.run_chain(dry_run=dry_run, repo_filter=repo)
    elif chain and not HAS_AUTOCHAIN:
        click.echo(click.style(
            "⚠️ AutoChain non disponible (NEXUS absent). Fallback sur run().", fg="yellow"
        ))
        result = orch.run(dry_run=dry_run, repo_filter=repo)
    else:
        result = orch.run(dry_run=dry_run, repo_filter=repo)

    if result.success:
        prefix = "(chain) " if chain else ""
        click.echo(click.style(f"✅ Sync {prefix}terminé", fg="green"))
        if result.report_path:
            click.echo(f"📄 Rapport : {result.report_path}")
    else:
        click.echo(click.style(f"❌ Échec : {result.stderr}", fg="red"), err=True)
        ctx.exit(1)
```

### F4 — Step CI mis à jour dans `ecosystem_sync.yml`

**Fichier** : `.github/workflows/ecosystem_sync.yml` (modification du step F3 existant)

```yaml
- name: NEXUS Sync v2 — Reconcile (auto-detect)
  id: nexus_sync
  run: |
    python -m kiva_cli.commands.cicd_commands nexus-sync --dry-run || \
    python -m kiva_cli.commands.cicd_commands nexus-sync --dry-run --no-chain
  env:
    ECOS_ROOT: ${{ vars.ECOS_ROOT || 'D:/DO/WEB' }}
  continue-on-error: true
```

Le `--no-chain` (ou l'absence de `--chain`) garantit que le CI utilise toujours le mode `subprocess.run` classique, sans tenter d'importer AutoChain.

---

## Chaînes déclaratives définies

### Chaîne 1 : `nexus-sync` (obligatoire)

| Étape | Type | Cible | Description |
|---|---|---|---|
| `resolve` | tool | `_resolve_nexus_path()` | Localise le checkout NEXUS |
| `reconcile` | tool | `run()` | Exécute `sync_agent_v2.py reconcile` |
| `report` | tool | `_find_latest_report()` | Récupère le rapport généré |

**Error handling** : `stop_on_error` (toute erreur arrête la chaîne)

### Chaîne 2 : `kiva-pipeline` (optionnelle, `critical=False`)

| Étape | Type | Cible | Description |
|---|---|---|---|
| `windows_audit` | skill | `WindowsAuditor.check()` | Compatibilité Windows |
| `stub_generate` | skill | `StubGenerator.generate()` | Génération de stubs |
| `test_repair` | skill | `TestRepairAgent.run()` | Réparation des tests |
| `subprocess_validate` | skill | `SubprocessOrchestrator.run()` | Validation subprocess |

**Error handling** : `continue_on_error` (une étape échouée n'arrête pas la chaîne)

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
Then un avertissement "AutoChain non disponible" est affiché
And le fallback run() classique est utilisé
And le sync fonctionne quand même

Given NEXUS est absent
When l'utilisateur exécute "kiva cicd nexus-sync --dry-run" (sans --chain)
Then aucun import AutoChain n'est tenté
Le mode subprocess.run classique est utilisé directement

Given le workflow ecosystem_sync.yml est déclenché
When le step "NEXUS Sync v2" s'exécute
Then le mode --no-chain est utilisé (pas d'import AutoChain)
And continue-on-error protège le workflow
```

---

## Risques & Mitigation

| Risque | Impact | Mitigation |
|---|---|---|
| `sys.path.insert` pollue le path global | Moyen | Insert uniquement dans le scope de `_try_import_autochain`, cleanup après |
| `AutoChainManager` NEXUS change d'API | Moyen | Guard `try/except ImportError` + version check si nécessaire |
| Double maintenance NEXUS ↔ KIVA-CLI | Faible | KIVA-CLI n'importe pas le code, il l'utilise via `subprocess` ou import dynamique — pas de copie |
| CI runner : `ECOS_ROOT` non configuré | Faible | Fallback `D:/DO/WEB` + `continue-on-error: true` |

---

## Plan d'implémentation

| Phase | Tâche | Fichier | Effort |
|---|---|---|---|
| 1 | Import dynamique + guard `HAS_AUTOCHAIN` | `nexus_sync_orchestrator.py` | 1h |
| 2 | Méthode `run_chain()` | `nexus_sync_orchestrator.py` | 1h |
| 3 | Commande `--chain` dans CLI | `cicd_commands.py` | 30min |
| 4 | Mise à jour `ecosystem_sync.yml` | `.github/workflows/ecosystem_sync.yml` | 30min |
| 5 | Tests unitaires | `tests/test_nexus_sync_orchestrator.py` | 1h |

**Total estimé** : 4h

---

## Références

- PRD-KIVA-006 — NEXUS Sync Governance Layer (DONE)
- PRD-XECO-001 — NEXUS Sync Agent v2 (DONE)
- `gerivdb/NEXUS` `entities/auto_chain_manager.py` — `AutoChainManager`
- `gerivdb/NEXUS` `auto_chain_executor.py` — `AutoChainExecutor`

---

**Fin du PRD-KIVA-007**
