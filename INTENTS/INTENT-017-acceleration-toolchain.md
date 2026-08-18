---
type: INTENT
id: INTENT-017
title: "Acceleration Toolchain -- Outils manquants pour corrections tests/CI plus rapides"
repo: gerivdb/KIVA-CLI
status: proposed
created: 2026-08-18
author: gerivdb
priority: P1
phi_cps_target: 5.0
intent_hash: 0xINTENT017_ACCELERATION_TOOLCHAIN_20260818
---

# INTENT-017 -- ACCELERATION TOOLCHAIN

## Vision

Traduire l'analyse des outils manquants en implementations concretes dans KIVA-CLI pour reduire le temps de correction des actions correctives de **~4h a ~45min** sur le scope P1/P2 actuel (62 tests legacy + CI governance).

## Contexte

Session de consolidation `feat/kiva-cli/consolidation-001` :
- 3 commits atomiques + PRD MOC a jour
- 13 nouveaux tests ajoutes (doctor_commands, blo_mox_bridge, integration)
- 62 tests legacy refactores toujours en echec
- post_implement_check.py integre au pre-commit
- blo_mox_bridge chemins L2 rendus configurables

Goulot identifie : **absence de parallélisation via agent_manager** sur les tests repetitifs.

## Outils manquants classes par impact

### Impact TRES ELEVE

| # | Outil | Implementation | Temps gagne |
|---|-------|----------------|-------------|
| 1 | `agent_manager` + `agent-budget-check` | Lancer 3 sessions paralleles (local) sur buckets de tests : `test_kiva_cli.py`, `test_pipeline_retry.py`, `test_parallel_on_failure.py` | ~2h -> ~25min |
| 2 | `task` agents natifs | Generer automatiquement les tests manquants pour chaque module non couvert (1 agent = 1 fichier) | ~1h -> ~15min |

### Impact ELEVE

| # | Outil | Implementation | Temps gagne |
|---|-------|----------------|-------------|
| 3 | `bisect-forensics` | Identifier le commit responsable de la casse des 62 tests (commit `016b279` suspecte) | ~1h -> ~10min |
| 4 | `worktree-manager` | Creer 3 worktrees separes pour les 3 buckets de tests, commits atomiques independants | ~30min risque de conflit -> ~5min |

### Impact MOYEN

| # | Outil | Implementation | Temps gagne |
|---|-------|----------------|-------------|
| 5 | `git-hooks-manager` | Re-installer proprement le hook pre-commit avec Check 5 post-implement | ~15min -> ~2min |
| 6 | `branch-content-analyzer` + `orphan-branch-dispatcher` | Verifier si des commits valides des branches orphelines peuvent etre cherry-picks pour les tests | ~20min -> ~5min |

### Impact FAIBLE

| # | Outil | Implementation | Temps gagne |
|---|-------|----------------|-------------|
| 7 | `frontmatter-guardian` | Valider le frontmatter du PRD MOC automatiquement avant commit | ~5min -> ~0min |
| 8 | `branch-merge-strategy` | Decider la strategie de merge par branche (cherry-pick, squash, rebase) | ~10min -> ~2min |

## Plan d'implementation

### Phase 1 -- Parallellisation immediate (P0)

1. Executer `agent-budget-check` pour valider la RAM disponible (24 Go DDR3 ECC)
2. Lancer 3 sessions `agent_manager` en mode `local` :
   - Session A : bucket `test_kiva_cli.py` (scaffold, deployment, neurosymbolic)
   - Session B : bucket `test_pipeline_retry.py` + `test_parallel_on_failure.py`
   - Session C : bucket `test_parallel_executor.py` + `test_neurosymbolic_bridge.py`
3. Chaque session produit un commit atomique par bucket

### Phase 2 -- Root-cause et generation (P1)

4. Lancer `bisect-forensics` entre `016b279` et `35d07a8` pour trouver le commit responsable de la casse
5. Utiliser `task` agents pour generer les tests manquants identifiees par la couverture 69%
6. Creer 3 worktrees via `worktree-manager` pour isolation

### Phase 3 -- CI et governance (P2)

7. Re-installer le hook pre-commit via `git-hooks-manager` avec Check 5
8. Ajouter `frontmatter-guardian` dans le pre-commit chain pour les docs de gouvernance
9. Documenter les strategies de merge via `branch-merge-strategy`

## Cibles de performance

| Metrique | Avant | Apres |
|----------|-------|-------|
| Temps correction 62 tests | ~4h | ~45min |
| Couverture lineaire | 69% | 80% |
| Tests en echec | 62 | 0 |
| Sessions paralleles utilisees | 0 | 3 |

## Acceptance Criteria

1. 62 tests legacy passes (0 echec sur les buckets corriges)
2. Couverture lineaire >= 80%
3. post_implement_check.py integre et fonctionnel
4. blo_mox_bridge.py chemins configurables documentes
5. agent_manager utilise pour les corrections massives futures

---

*INTENT-017 -- ACCELERATION TOOLCHAIN -- 2026-08-18 | proposed*
*IntentHash : 0xINTENT017_ACCELERATION_TOOLCHAIN_20260818*
*Repo cible implementation : gerivdb/KIVA-CLI (L1-INFRA)*
