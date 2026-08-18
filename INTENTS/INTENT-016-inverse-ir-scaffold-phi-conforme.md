---
type: INTENT
id: INTENT-016
title: "INVERSE-IR -- Reconstruction d'un repo scaffold phi-conforme depuis un IRNode-seed"
repo: gerivdb/KIVA-CLI
status: draft
created: 2026-06-20
author: gerivdb
priority: P2
phi_cps_target: 6.2
intent_hash: 0xINTENT016_INVERSE_IR_SCAFFOLD_PHI_20260620
---

# INTENT-016 -- INVERSE-IR : Scaffold holographique inverse

## Vision

Inverser le flux IR. Donner un `IRNode` seed (avec phi, trit, intent_hash)
et demander a `InverseIR` de **reconstruire le scaffold d'un repo conforme**
en deduisant par propagation causale inverse la structure attendue :
dossiers, fichiers, EPICs, ADRs, tests.

C'est la **generation de repo par contrainte holographique** plutot
que par template. Chaque repo genere est phi-conforme des le premier commit.

## Principe technique

```
IRNode seed {id, phi, trit, intent_hash, ternary_role}
       |
       v
InverseIR.propagate_backward()
       |
       v
Scaffold plan:
  src/<name>/__init__.py  (T1=present, T2=valide)
  INTENTS/INTENT-XXX.md   (T4=cause, T5=canonique)
  tests/test_<name>.py    (T2=valide)
  PRD-XXX.md              (T3=hierarchique)
  ADR-XXX.md              (T5=canonique, si phi > 4.559)
       |
       v
KIVA-CLI.scaffold() -- genere les fichiers
```

## Ancrage ecosysteme

- **Strate** : L2_COMPOSITION (KIVA-CLI -- scaffolding)
- **Consomme** : keel_core.AnywhereIR, INTENT-010 BASE243-ENCODER
- **Produit vers** : nouveau repo via KIVA-CLI scaffold
- **Ternary role** : E (execution scaffold)
- **Complementaire** : GENOME-IR (INTENT-014) fournit le genome-cible
- **HITL** : review obligatoire avant git push du scaffold genere

## Differences avec scaffold classique

| Classique (template) | InverseIR (holographique) |
|---------------------|---------------------------|
| Structure fixe | Structure deduite du phi |
| Identique pour tous | Unique par IRNode seed |
| Template statique | Propagation causale dynamique |
| Pas de validation | phi-CPS >= 4.559 garanti |

## Acceptance Criteria

1. `kiva scaffold --seed intent_hash:0xXXX` genere un repo structure valide
2. phi-CPS du scaffold genere >= 4.559 avant le premier commit
3. Structure deduite de l'IRNode seed (pas d'un template fixe)
4. HITL obligatoire avant push (0 push automatique)
5. Compatible avec GENOME-IR pour validation genome L0

---

*INTENT-016 -- INVERSE-IR -- 2026-06-20 | proposed*
*IntentHash : 0xINTENT016_INVERSE_IR_SCAFFOLD_PHI_20260620*
*Repo cible implementation : gerivdb/KIVA-CLI (L2_COMPOSITION)*
