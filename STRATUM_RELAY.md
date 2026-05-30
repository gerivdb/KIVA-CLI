---
relay_version: 5
repo: gerivdb/KIVA-CLI
strate: L3
lifecycle: ACTIVE
vague: 5
synchro: '2026-05-30'
hub: gerivdb/GOVERNANCE-HUB
intent_hash: '0xE8ED2CCEB9C4DDF4'
phi_cps:
  value: null
  source: NOT_MEASURED
  valid: false
  note: 3.697 was a mass placeholder — replaced by null
rules:
- id: R1
  assertion: ECOS-CLI est un executable pur — zero regle LLM.
  eval_cmd: null
  status: UNVERIFIED
  severity: CRITICAL
- id: R2
  assertion: Chaque commande ecos * a un test dans DevTools-CLI.
  eval_cmd: null
  status: UNVERIFIED
  severity: HIGH
- id: R3
  assertion: BLO utilise bloom.db + WAL — acces direct interdit.
  eval_cmd: null
  status: UNVERIFIED
  severity: HIGH
---

# STRATUM RELAY — KIVA-CLI (L3)

**VAGUE**: 5 | **Synchro**: 2026-05-30 | **Hub**: gerivdb/GOVERNANCE-HUB

---

## Identite stratique

- **Strate** : `L3` — Systeme moteur CLI
- **Role canonique** : CLI orchestrateur projets/apps Ã”Ã‡Ã¶ scaffolding KIVA
- **Parent** : L2
- **Enfants** : L4
- **phi-CPS** : null (NOT_MEASURED)

## Navigation rapide

- PRD canonique : `GOVERNANCE-HUB/PRD/PRD_ECOSYSTEM_SUPERSTRUCTURE_L0-L9_V1.md`
- Substrat cognitif : `gerivdb/LLM-REPO` (L1b — prive)
- Standards repo : `REPO-STANDARDS` (RSS-v1)
- Transit map : `VERSUS/urban_ontology_verse/TRANSIT/transit_map.yaml`
- Cadastre : `VERSUS/urban_ontology_verse/CADASTRE/cadastre_full.yaml`

## Regles locales

- **R1** — ECOS-CLI est un executable pur — zero regle LLM.  [UNVERIFIED]
- **R2** — Chaque commande ecos * a un test dans DevTools-CLI.  [UNVERIFIED]
- **R3** — BLO utilise bloom.db + WAL — acces direct interdit.  [UNVERIFIED]

## Karpathy-Recall etendu (Vague 5 — 10Q)

> Reponds mentalement a ces questions avant d'agir dans ce repo.

1. Q: Apres migration v1.1.0, que contient ECOS-CLI et que NE contient-il PLUS ?
2. Q: Quelle est la frontiere de responsabilite entre ECOS-CLI et DevTools ?
3. Q: Qu'est-ce que BLO et quel format de base de donnees utilise-t-il ?
4. Q: OPENCLAW-CLI est decrit comme 'Intent Normalization Gateway' — qu'est-ce que cela veut dire ?
5. Q: FLUENCE-CLI delegue a ECOS-CLI — quelle est la regle de delegation ?
6. Q: Quels repos dependent directement de L3 (ECOS-CLI, CLIs) ?
7. Q: Quel est le role de L3 dans la boot sequence ?
8. Q: Pourquoi les regles LLM ne doivent pas resider dans ECOS-CLI ?
9. Q: Quelle commande ecos * est la plus critique a tester ?
10. Q: Dans quelle phase UrbanVerse le STRATUM_RELAY de ce repo a-t-il ete deploye ?

## Dependances directes

**Parents (amont) :**
- BRAIN
- FLUENCE
- VDB
- DATA-MINER
- TINA

**Enfants (aval) :**
- ECOS-CLI
- DevTools
- FLUENCE-CLI
- DevTools-CLI
- FORGE
- OPENCLAW-CLI
- BRAIN-CLI
- GOST
- ecos-plugin-perplexity
- BatMCP

## Vague de mise a jour

| Vague | Contenu | Statut |
|-------|---------|--------|
| **5 (courante)** | Frontmatter YAML + regles structurees + phi_cps null honnete | Deploye |
| 6 (suivante) | Eval cmd sandbox + HMAC + hardware constraints | Planifie |

---

*Genere par `VERSUS/urban_ontology_verse/TOOLS/relay_propagator.py` v4.0*
*UrbanVerse v1.0.0 — gerivdb/VERSUS (L8)*
