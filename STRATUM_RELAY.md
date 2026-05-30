# STRATUM RELAY — KIVA-CLI (L3)

**VAGUE**: 4 | **Synchro**: 2026-05-30 | **Hub**: gerivdb/LLM-REPO

- **Strate** : `L3` — Systeme moteur CLI
- **Role canonique** : CLI orchestrateur projets/apps — scaffolding KIVA
- **Parent** : L2 (KIVA)
- **Enfants** : L4 (KIVA execute les deploiements)

## Regles locales
- R1 — KIVA-CLI orchestre les projets/apps — tout scaffolding passe par KIVA-CLI.
- R2 — KIVA execute, KIVA-CLI definit — ne pas inverser.
- Anti-pattern: deployer un projet sans passer par KIVA-CLI.

## Karpathy-Recall local (Vague 3 — 10Q)
1. Apres migration v1.1.0, que contient ECOS-CLI et que NE contient-il PLUS ?
2. Qu'est-ce que BLO et quel format de base de donnees utilise-t-il ?
3. Quelle commande ecos * est la plus critique a tester ?
4. Quelle est la frontiere entre KIVA-CLI (L3) et ECOS-CLI (L3) ?
5. Pourquoi KIVA-CLI ne doit-il pas executer directement les deploiements ?
6. Quels types de projets/apps KIVA-CLI peut-il scaffolder et comment KIVA les execute-t-il ?
7. Quel est le format de sortie du scaffolding KIVA-CLI et ou est-il stocke ?
8. Comment KIVA-CLI verifie-t-il qu'un projet est conforme avant de le deleguer a KIVA ?
9. Quelles sont les differences entre le mode 'create' et le mode 'deploy' dans KIVA-CLI ?
10. Comment KIVA-CLI integre-t-il le registre ECOS pour les dependances multi-repo ?

## Dependances directes

- **Parent (amont)** : KIVA (L2) — KIVA-CLI recoit les directives de scaffolding de KIVA.
- **Enfants (aval)** : Aucun — KIVA-CLI est une feuille de la chaine; il delegue l'execution a KIVA (L4).

## Agents locaux (Vague 4)

```yaml
# .roomodes — profil agent KIVA-CLI
agent: kiva-scaffolder
strate: L3
role: Project scaffolding CLI
rules: KIVA-CLI/rules/scaffold_rules.yaml
hub_ref: KIVA
```

L'agent `kiva-scaffolder` definit la structure de chaque projet/app, valide la conformite avant delegation, et ne modifie jamais l'execution.

## Auto-conformite (Vague 4)

- **Guard 1 — Define, don't execute** : KIVA-CLI definit la structure, KIVA execute. Toute inversion est bloquee.
- **Guard 2 — Conformance check** : Tout projet doit passer la validation de conformite avant delegation a KIVA.
- **Guard 3 — No direct deploy** : KIVA-CLI ne deploie jamais directly. Tout passe par KIVA.

## Vague de mise a jour

| Vague | Contenu | Statut |
|-------|---------|--------|
| 2 | Identite + regles + Karpathy-Recall 5Q | Deploye |
| 3 | Recall etendu a 10Q + section Dependances | Deploye |
| **4 (courante)** | Agents locaux + auto-conformite | Deploye |

---

*Genere par `VERSUS/urban_ontology_verse/TOOLS/relay_propagator.py` v4.0*
*UrbanVerse v4.0.0 — gerivdb/VERSUS (L8)*
*IntentHash: 0xPHASE8_KIVA_CLI_V4_PHASE8_20260530*