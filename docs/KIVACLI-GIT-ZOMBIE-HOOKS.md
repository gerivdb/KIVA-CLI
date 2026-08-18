# KIVA-CLI -- Git Zombie Hooks

**IntentHash** : `0xPRD_MOC_PROCESS_ZOMBIE_HYGIENE_DEVTOOLS_20260809`
**Depot** : gerivdb/KIVA-CLI
**CI** : KIVA-CLI locale souveraine (interdiction GitHub Actions -- ADR-024)

---

## 1. Contexte

KIVA-CLI est la CI locale souveraine de l'ecosysteme gerivdb. Les sessions KiloCode, les worktrees temporaires et les isolations TRIX laissent des processus zombies qui peuvent perturber les executions CI suivantes.

Ce document decrit les hooks **pre-CI** et **post-CI** pour garantir un environnement propre avant/apres chaque execution KIVA-CLI.

---

## 2. Hook pre-CI -- `pre-ci`

### Declenchement

Avant toute execution de CI locale KIVA-CLI.

### Actions

1. **Verifier l'absence de processus zombies**
   ```powershell
   powershell -File "D:\DO\WEB\TOOLS\L2-PLATFORM\GeriCode\scripts\verify-agent-manager-env.ps1"
   ```

2. **Purge automatique des zombies legers**
   - Types cibles : `git.exe`, `node.exe`, `python.exe`, `zig.exe`, `cargo.exe`, `bun.exe`, `pwsh.exe`
   - Exclusion : `trixd.exe`, `kix.exe` (verification manuelle requise)

3. **Verifier les worktrees orphelins**
   ```powershell
   git worktree list
   # Signaler tout worktree dont la branche n'existe plus
   ```

4. **Verifier les stashes temporaires**
   ```powershell
   git stash list
   # Signaler tout stash "temp" / "WIP" / "before switch"
   ```

### Sortie attendue

```yaml
pre_ci_status: PASS | WARN | FAIL
process_zombies: []
worktree_zombies: []
stash_zombies: []
recommendation: "proceed" | "purge_and_proceed" | "abort"
```

---

## 3. Hook post-CI -- `post-ci`

### Declenchement

Apres toute execution de CI locale KIVA-CLI (succes ou echec).

### Actions

1. **Audit post-CI**
   - Comparer l'etat des worktrees avant/apres CI
   - Detecter les nouveaux processus zombies crees pendant la CI

2. **Purge des worktrees temporaires CI**
   ```powershell
   # Supprimer les worktrees temporaires crees par la CI
   git worktree remove <worktree-path>
   git worktree prune
   ```

3. **Purge des stashes temporaires CI**
   ```powershell
   # Supprimer les stashes crees pendant la CI
   git stash drop stash@{n}
   ```

4. **Logger dans NEXUS/WAL**
   ```json
   {
     "timestamp": "2026-08-09T20:00:00Z",
     "event_type": "post_ci_audit",
     "intent_hash": "0xPRD_MOC_PROCESS_ZOMBIE_HYGIENE_DEVTOOLS_20260809",
     "data": {
       "ci_run_id": "<id>",
       "worktrees_created": 0,
       "worktrees_removed": 0,
       "stashes_created": 0,
       "stashes_removed": 0,
       "process_zombies_detected": 0
     }
   }
   ```

---

## 4. Integration avec KIX

KIVA-CLI peut interroger KIX pour obtenir l'etat des zombies :

```bash
# Inventaire
curl http://localhost:8800/health/zombies

# Purge (dry-run)
curl -X POST http://localhost:8800/health/zombies/purge \
  -H "Content-Type: application/json" \
  -d '{"types": ["git", "node", "python"], "dry_run": true}'

# Purge (live)
curl -X POST http://localhost:8800/health/zombies/purge \
  -H "Content-Type: application/json" \
  -d '{"types": ["git", "node", "python"], "dry_run": false}'
```

---

## 5. Integration avec TRIX

Avant toute isolation TRIX, executer le preflight etendu :

```powershell
.\trix.exe preflight
```

Le check `child_zombies` avertit si des processus enfants zombies de `trixd.exe` sont detectes.

---

## 6. Integration avec GeriCode

Le script `scripts/verify-agent-manager-env.ps1` inclut desormais le CHECK-8 `process_zombies`.

```powershell
powershell -File "D:\DO\WEB\TOOLS\L2-PLATFORM\GeriCode\scripts\verify-agent-manager-env.ps1"
```

---

## 7. Regles

1. **pre-CI est obligatoire** avant toute execution KIVA-CLI
2. **post-CI est obligatoire** apres toute execution KIVA-CLI
3. **Ne JAMAIS** purger `trixd.exe` ou `kix.exe` sans verification manuelle
4. **Ne JAMAIS** supprimer un worktree sans verifier que la branche existe
5. **Logger chaque purge** dans NEXUS/WAL pour tracabilite
6. **ADR-024** : GitHub Actions est interdit -- KIVA-CLI est la CI souveraine exclusive

---

## 8. Reference

- **PRD MOC** : `act-protocol/PRD/PRD-MOC-ACTPROTOCOL/fractal/architecture/PRD-MOC-PROCESS-ZOMBIE-HYGIENE-DEVTOOLS-2026-08-09.md`
- **Skill** : `.kilo/skills/process-hygiene/SKILL.md` (GeriCode)
- **Commande** : `.kilo/commands/git-hygiene.md` (GeriCode)
- **KIX** : `src/zombie_monitor.py` (endpoints `/health/zombies`, `/health/zombies/purge`)
- **TRIX** : `tools/trix_preflight.zig` (commande `trix preflight`)
- **ADR** : ADR-2026-08-09-001-GIT_HYGIENE_MECHANISMS
- **IntentHash** : `0xGIT_HYGIENE_RULES_20260809`
