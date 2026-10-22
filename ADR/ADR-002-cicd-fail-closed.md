---
type: ADR
status: proposed
date: "2026-10-22"
intent_hash: 0xADR_2026_10_22_002_CICD_FAIL_CLOSED_20261022
author: gerivdb
created: "2026-10-22"
id: ADR-002
repo: gerivdb/KIVA-CLI
title: Porte CI/merge fail-closed et diagnostic qualifie
canonical_location: gerivdb/GOVERNANCE-HUB/ADR/ADR-2026-10-22-002-cicd-fail-closed.md
---

# ADR-2026-10-22-002: Porte CI/merge fail-closed et diagnostic qualifie

> **Emplacement canonique** :
> `gerivdb/GOVERNANCE-HUB/ADR/ADR-2026-10-22-002-cicd-fail-closed.md`
>
> Ce fichier est la copie locale de depot. En cas de divergence, le registre
> canonique fait foi (meme convention que
> `ADR-2026-10-21-001-notebooklm-mcp-integration` dans RAGX).

## Resume

La porte de securite de la sequence de merge de KIVA-CLI (`kiva merge pr`,
etape 3 sur 5) **ne bloquait rien** : la commande `kiva cicd run` affichait
l'echec du pipeline puis rendait un code de sortie `0`. Le controle
`rc != 0` de `merge_commands.py` ne pouvait donc jamais se declencher.

Deux PR `GOVERNANCE-HUB` ont ete fusionnees avec un CI local en echec
(#385, #387) sans que la porte ne les bloque.

## Decision (resume ; detail dans l'ADR canonique)

1. **D1** : `kiva cicd run` sort en code `1` des que le pipeline n'est pas
   vert. La porte de merge devient fail-closed. La sequence de merge n'est
   pas modifiee : seule l'entree de la porte etait neutralisee.
2. **D2** : L'echec est qualifie : `test_failure`, `timeout`,
   `environment_error`. Les trois sont bloquants ; seule la remediation
   prescrite differe. La sortie de pytest est conservee et restituee.
3. **D3** : `CICDManager.run_ci_pipeline()` conserve sa signature booleenne.
4. **D4** : `tests/test_cicd_commands.py::test_run_failure` affirmait
   `exit_code == 0` pour un pipeline en echec : le suite encodait le defaut
   comme attendu. Ce test est corrige.
5. **D5** : `tests/test_cicd_fail_closed.py` verrouille le contrat, dont la
   propriete de securite bout-en-bout : un CI local en echec **bloque** la
   porte de merge, et la fusion n'est pas tentee.
6. **D6** : Deux tests rendaient la suite non collectible depuis un worktree
   (`tests/commands/test_delivery_commands.py` inscrivait le chemin absolu
   d'un autre clone en tete de `sys.path` ; `tests/scripts/test_python_helper.py`
   importait un paquet namespace dont le `__path__` se fige au premier
   import). Sans cette correction, le present ADR serait invérifiable : la
   suite mesuree serait celle d'un autre depot.
7. **D7** : Le mode `--dry-run` n'exige plus la verification de l'etat reel
   d'une fusion qui n'a pas eu lieu. Il echouait sur toute machine sans
   identifiants (`HTTP Error 401`), y compris en CI.
8. **D8** : Un depot dont le chemin local n'est pas resolvable REFUSE le
   merge. L'ancien repli (`python -m pytest` dans le repertoire courant)
   evaluait la suite d'un **autre** depot : une PR pouvait etre fusionnee sur
   un etat vert qui n'etait pas le sien.

## Fichiers modifies

- `kiva_cli/core/cicd_manager.py` : `CIPipelineResult`,
  `run_ci_pipeline_detailed()`, qualification des causes, conservation de la
  sortie.
- `kiva_cli/commands/cicd_commands.py` : code de sortie non nul, rapport
  d'echec qualifie.
- `kiva_cli/commands/merge_commands.py` : verification de l'etat reel
  inapplicable en dry-run (D7) ; refus du depot non resolvable (D8).
- `tests/test_cicd_commands.py` : assertion fail-open corrigee.
- `tests/test_cicd_fail_closed.py` : contrat fail-closed (nouveau).
- `tests/test_merge_commands.py` : contrat de refus reecrit selon le
  comportement reel.
- `tests/commands/test_delivery_commands.py` : hermeticite du `sys.path`.
- `tests/scripts/test_python_helper.py` : import deterministe du module cible.

## Preuve

| Mesure | Resultat |
|---|---|
| Falsifiabilite (comportement fail-open restaure) | exactement 5 tests en echec, dont `DID NOT RAISE SystemExit` (la porte fusionnait sur un CI rouge) |
| Avec le correctif | `29 passed` sur les deux fichiers de test du contrat, puis `48 passed` sur le perimetre merge inclus |
| Suite complete | `2 failed, 1226 passed, 21 skipped`, **0 erreur de collecte** |
| Echecs restants | 2 `tests/legacy_root_tests/` (detection de derive de registre, dependante de l'etat live du registre TOPOS) : **pre-existants**, hors perimetre de la porte CI |
| Collecte sur `main` | non collectible depuis un worktree (2 `ImportError`) : corrige par D6 |

## References

- `ADR-2026-10-22-001-c1-corridor-worktree-isolation` (GOVERNANCE-HUB) - D4 :
  un invariant annonce doit etre mesure.
- `ADR-001-dag3-merge-integration` (local) - sequence de merge a 5 etapes.
- `PRD-MOC-GEN-012 DESIGN-E` - un test qui affirme le bug n'est pas une preuve.

## Mise a jour requise si

- La sequence de merge de KIVA-CLI change (nombre ou ordre des etapes).
- Une autre porte de securite fait confiance au code de sortie de
  `kiva cicd run`.
- Le budget d'execution du pipeline CI change (constante
  `PIPELINE_TIMEOUT_SECONDS`).
