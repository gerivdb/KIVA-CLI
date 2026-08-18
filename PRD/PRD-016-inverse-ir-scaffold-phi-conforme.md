---
id: PRD-016
title: "INVERSE-IR -- Reconstruction d'un repo scaffold phi-conforme depuis un IRNode-seed"
repo: gerivdb/KIVA-CLI
intent: INTENT-016
status: draft
created: 2026-06-20
author: gerivdb
strate: L2_COMPOSITION
phi_cps_target: 6.2
intent_hash: 0xINTENT016_INVERSE_IR_SCAFFOLD_PHI_20260620
---

# PRD-016 -- INVERSE-IR
## Scaffold holographique inverse depuis un IRNode-seed

---

## Contexte

KIVA-CLI scaffold genere aujourd'hui des repos depuis des templates
fixes. Le resultat est identique pour tous les repos d'un meme type,
ce qui ne garantit pas la conformite phi-CPS.

`INVERSE-IR` inverse le flux : donner un `IRNode` seed et laisser
la propagation causale inverse deduire la structure attendue.
Chaque repo genere est unique, adapte a son seed, et phi-conforme
des le premier commit.

---

## Perimetre fonctionnel

### F1 -- Propagation causale inverse
A partir d'un IRNode seed :
- T1=present -> `src/<name>/` requis
- T2=valide -> `tests/test_<name>.py` requis
- T4=cause -> `INTENTS/INTENT-XXX.md` requis
- T5=canonique -> `ADR/ADR-XXX.md` requis si phi > 4.559
- T3=hierarchique -> `PRD/PRD-XXX.md` requis
Deduire par propagation tous les fichiers et dossiers attendus.

### F2 -- Scaffold generation
Generer les fichiers deduits via KIVA-CLI existant.
Chaque fichier genere contient le minimum necessaire
pour etre phi-conforme (header frontmatter, intent_hash, strate).

### F3 -- Validation phi pre-commit
Calculer le phi-CPS du scaffold avant tout git push.
Garantir phi >= 4.559 avant de proposer le push.

### F4 -- HITL gate
Presentez le scaffold genere pour review humaine.
0 push automatique. Le scaffold est une proposition.

---

## Interface

```bash
kiva scaffold \
  --seed intent_hash:0xINTENT019_METACLUSTER_PROPAGATION_SOUVERAINE_20260620 \
  --ternary-role E+Obs \
  --strate L1_CAUSALITY \
  --output ./scaffold-preview/
  # -> genere structure sans push
  # -> affiche phi-CPS calcule
  # -> attend confirmation HITL avant push

kiva scaffold validate --dir ./scaffold-preview/
  # -> phi-CPS: 5.2 [CONFORME]
  # -> missing: tests/ [ALERTE]

kiva scaffold push --dir ./scaffold-preview/ --repo gerivdb/NEW-REPO
  # -> push uniquement apres validation humaine
```

---

## Architecture

```
IRNode seed
  {id, phi, trit, intent_hash, ternary_role, strate}
        |
        v
InverseIR.propagate_backward()
  |- AxisMapper (T1->T5 -> requis/optionnel/absent)
  |- DependencyInferrer (relations DAG -> fichiers dependants)
  |- PhiPredictor (phi attendu du scaffold deduit)
        |
        v
ScaffoldPlan
  [FileSpec(path, content_template, phi_contribution)]
        |
        v
PhiValidator (phi >= 4.559 ?)
        |
        v
HITL Gate (affichage + confirmation)
        |
        v
KIVA-CLI.scaffold() -> fichiers generes
        |
        v
git push (apres confirmation uniquement)
```

---

## Differences avec scaffold classique

| Classique (template) | InverseIR (holographique) |
|---------------------|---------------------------|
| Structure fixe pour tous | Structure unique par IRNode seed |
| Template statique | Propagation causale dynamique |
| Pas de validation phi | phi >= 4.559 garanti avant push |
| Tous repos identiques | Chaque repo adapte a son contexte |
| Push immediat possible | HITL obligatoire |

---

## Contraintes

- phi-CPS scaffold genere >= 4.559 avant push
- 0 push sans confirmation humaine
- Compatible avec GENOME-IR (INTENT-014) pour validation genome L0
- Scaffold preview en < 3s
- Fichiers generes : contenu minimum valide (pas de placeholder vide)

---

## Acceptance Criteria

| # | Critere | Mesurable |
|---|---------|----------|
| AC1 | `kiva scaffold --seed intent_hash:0xXXX` genere structure valide | assert |
| AC2 | phi-CPS scaffold >= 4.559 avant push | assert |
| AC3 | Structure deduite du IRNode seed (pas template fixe) | diff vs template |
| AC4 | 0 push sans confirmation humaine | test negatif |
| AC5 | Compatible GENOME-IR validation L0 | integration |

---

## Dependances

- **KEEL-CORE** IRNode, ir_types (prerequis)
- **BASE243-ENCODER** INTENT-010 (fingerprint seed)
- **GENOME-IR** INTENT-014 (validation genome L0 post-scaffold)
- **KIVA-CLI** scaffold commands existants (extension)
- **HITL** gate D4 (valve avant push)

---

## Roadmap

| Phase | Livrable | Deadline |
|-------|----------|---------|
| R1 | AxisMapper T1->T5 -> requis/optionnel | S1 |
| R2 | DependencyInferrer DAG -> fichiers | S2-S3 |
| R3 | PhiPredictor + PhiValidator | S4 |
| R4 | ScaffoldPlan -> KIVA-CLI generation | S5 |
| R5 | HITL gate + git push integration | S6 |
| R6 | GENOME-IR validation post-scaffold | S7 |

---

*PRD-016 -- INVERSE-IR -- 2026-06-20 | proposed*
*Repo : gerivdb/KIVA-CLI (L2_COMPOSITION) | Intent : INTENT-016*
