---
type: PRD-MOC
status: proposed
date: "2026-09-21"
intent_hash: 0xKIVA_012_SESSION_FRICTIONS_20260921
---

# PRD-MOC-KIVA-012-SESSION-FRICTIONS-20260921

## 1. Contexte
Session TALEX postmortem 2026-09-21 : 7 frictions/erreurs ERR identifiées
et corrigées structurellement via R1-R7.

## 2. Objectif
Garantir que les causes racines sont résolues, tracées, et déployées
dans KIVA-CLI + GOVERNANCE-HUB + HERMES + WAZAA.

## 3. Périmètre
- KIVA-CLI : helpers cross-platform, validation YAML, publication intégrée
- GOVERNANCE-HUB : PRD-MOC memory + postmortem ERR analysis
- HERMES : factual_memory provider (get_tool_schemas ajouté)
- WAZAA : factual_memory bridge citizen

## 4. Livrables
| Livrable | Fichier | Status |
|---|---|---|
| Shell helpers | `kiva_cli/core/shell_helpers.py` | [OK] |
| File helpers | `kiva_cli/core/file_helpers.py` | [OK] |
| Pipeline schema validation | `kiva_cli/core/pipeline_loader.py` | [OK] |
| Publish workflow | `scripts/publish.py` | [OK] |
| Python helper | `scripts/python_helper.py` | [OK] |
| Pre-push sync | `scripts/pre_push_sync_check.py` | [OK] |
| ABC validator | `tests/utils/abc_contract_validator.py` | [OK] |
| Smoke tests | `tests/test_anything_cli.py` | [OK] |

## 5. Implémentation
Voir commits :
- `feat(kiva-012): add cross-platform shell/yaml/python/push guards (R1-R7 core)`
- `test(kiva-012): add unit tests for shell/file/pipeline/python helpers`
- `feat(kiva-012): add smoke test for anything-CLI helpers`

## 6. Validation
- Tests unitaires : 16/16 passent
- Post-implement check : F10 résolu, MOX en attente PRD-MOC.md racine

## 7. Proof-of-Life
| Item | Preuve | Status |
|---|---|---|
| Tests unitaires | `pytest tests/test_anything_cli.py -q` -> 7/7 | [OK] |
| Shell normalization | `normalize_shell_command("git diff | head -20")` | [OK] |
| Pipeline validation | `validate_pipeline_schema()` rejects `stop` | [OK] |
| PRD-MOC racine | `PRD-MOC.md` present | [OK] |

## 8. Glossaire des statuts
- [DOC] Documenté
- [IMP] Implémenté
- [TST] Testé
- [OPS] Opérationnel
- [ACT] Actif
- [PSV] Passif
- [PDN] Pending
- [BLK] Bloqué
