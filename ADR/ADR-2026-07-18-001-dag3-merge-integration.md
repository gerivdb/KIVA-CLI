---
type: ADR
status: proposed
date: "2026-07-18"
intent_hash: 0xADR_DAG3_INTEGRATION_20260718
---

# ADR-2026-07-18-001: DAG-3 Integration for Merge Validation

## Contexte

Le workflow de merge actuel dans KIVA-CLI (IntentHash: 0xKIVA_MERGE_SOVEREIGN_phi4559) effectue les verifications suivantes:
1. CI local (kiva cicd run)
2. Merge atomique (gh pr merge)
3. WAL append
4. Drift check phi-CPS

Cependant, ce workflow ne detecte pas les **cycles atomiques** dans les dependances (ACM) ni les **violations d'adjonction** (ADMR) qui peuvent bloquer la stabilite du systeme.

## Probleme

- **Cycles atomiques (ACM)** : Les cycles dans les dependances peuvent causer des problemes de compilation, des erreurs de circular import, et une complexite non-geree.
- **Violations d'adjonction (ADMR)** : Les merges peuvent introduire des changements d'interface non-compatibles ou des dependances externes non-approuvees.
- **phi-CPS drift** : Le score de performance cognitive n'est pas calcule avant le merge, uniquement apres.

## Solution

Integrer le **DAG-3** (Triadic Graph Engine) dans le workflow de merge:

### Nouvelle sequence (5 etapes):

1. **DAG-3 Validation** (nouveau) - ACM + ADMR avant merge
   - Detection des cycles atomiques (ACM Detector)
   - Validation des adjonctions (ADMR Validator)
   - Calcul du phi-CPS impact
   - Decision: APPROVED / NEEDS_HITL / REJECTED

2. CI local (kiva cicd run)
3. Merge atomique (gh pr merge)
4. WAL append + drift check
5. Citizen promotion

### Composants DAG-3

- **ACMDetector** : Detecte les cycles atomiques dans les graphes de dependances
  - Utilise NetworkX pour l'analyse de graphes
  - Calcule la gravite des cycles (LOW/MEDIUM/HIGH)
  - Estime l'impact phi-CPS

- **ADMRValidator** : Valide les merge requests bases sur des contraintes
  - Cycle constraints (R6)
  - Dependency constraints (R9)
  - Interface constraints
  - Architecture constraints
  - Security constraints
  - Performance constraints

- **DAG3Manager** : Orchestrateur qui combine ACM et ADMR
  - Decide du statut global: approved / needs_hitl / rejected
  - Genere des recommandations appropriees

## Implementation

### Fichiers crees

1. `kiva_cli/core/dag3/acm_detector.py` - Detecteur de cycles atomiques
2. `kiva_cli/core/dag3/admr_validator.py` - Validateur ADMR
3. `kiva_cli/core/dag3/dag3_manager.py` - Orchestrateur DAG-3
4. `kiva_cli/core/dag3/__init__.py` - Exports du module
5. `scripts/acm_detect.py` - Script CLI ACM
6. `scripts/admr_validate.py` - Script CLI ADMR
7. `scripts/dag3_validate.py` - Script CLI DAG3

### Modifications apportees

1. `kiva_cli/commands/merge_commands.py`
   - Ajout de l'etape DAG-3 avant le CI
   - Nouveau parametre `--skip-dag3` pour bypass
   - Nouveau parametre `source_branch` pour specifier la branche
   - WAL events enrichis avec metadonnees DAG-3

## Decision

**Statut : APPROUVE**

L'integration de DAG-3 ameliore significativement la qualite des merges en:
- Prevenant les merges problematiques avant qu'ils ne soient appliques
- Fournissant des recommandations concretes pour la resolution
- Calculant l'impact phi-CPS des le pre-merge

## Consequences

### Positives
- Reduction des erreurs de merge causees par des cycles
- Meilleure visibilite sur les impacts des changements
- Alignement avec les principes de phi-CPS

### Negatives
- Legere augmentation du temps de pre-merge (quelques secondes)
- Necessite l'option `--skip-dag3` pour les hotfixes

## References

- IntentHash: 0xKIVA_MERGE_SOVEREIGN_phi4559
- IntentHash: 0xACM_DETECTOR_20260718
- IntentHash: 0xADMR_VALIDATOR_20260718
- IntentHash: 0xDAG3_MANAGER_20260718
- KEEL Gates: R6 (cycle), R9 (dependency), R10 (HITL)

## Mise a jour requise si

- Ajout de nouveaux types de contraintes dans KEEL
- Modification des seuils phi-CPS
- Ajout de nouveaux patterns de cycle dans ACM

