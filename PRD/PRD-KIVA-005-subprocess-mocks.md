# PRD-KIVA-005 — Subprocess Mock Orchestrator

## Métadonnées

| Champ | Valeur |
|---|---|
| **Repo cible** | `KIVA-CLI` |
| **Destination** | `KIVA-CLI/PRD/` |
| **Transversalité** | NON |
| **Repos impactés** | KIVA-CLI (forte utilisation interne de subprocess pour Docker, K8s, LXC, git, ECOS, etc.) |
| **Priorité** | P2 |
| **Epic parent** | N/A |
| **Statut** | DRAFT |
| **Auteur** | @gerivdb |
| **Date création** | 2026-05-21 |
| **Dernière mise à jour** | 2026-05-21 |
| **Référence standard** | PRD-ROUTING-STANDARD |

---

## Contexte et problème

KIVA-CLI exécute de nombreux outils externes via `subprocess` :

- Docker (`docker build`, `docker run`)
- Kubernetes (`kubectl apply`)
- LXC (`lxc-create`, `lxc-start`)
- Git, ECOS CLI, PowerShell wrappers, etc.

Actuellement les mocks sont **dupliqués et fragiles** dans les tests (`test_*.py`, `conftest.py`).

Il n'existe pas de couche centralisée pour :
- Enregistrer les appels réels une fois
- Rejouer les mocks de manière déterministe
- Gérer les différents "modes" (record / replay / passthrough / failure injection)
- Intégrer proprement avec les états Base-3 (ValidationState) et le WAL

Cela rend les tests lents, non reproductibles, et complique le travail du Test-Repair Agent et du Stub Generator.

---

## Objectifs

Créer un **Subprocess Mock Orchestrator** centralisé qui permet à tous les composants KIVA (managers, skills, tests, agents) d'utiliser des mocks subprocess fiables, versionnés et traçables.

**Critères de succès :**
- Un seul point d'entrée `from kiva_cli.core.subprocess_mock import SubprocessMockOrchestrator`
- Support record/replay + failure injection + timeout simulation
- Intégration native avec GlobalWAL (chaque appel mocké = événement WAL)
- Utilisation des types canoniques (PRD-KIVA-004)
- Permet au Test-Repair Agent de "réparer" des mocks cassés
- Réduction significative du temps d'exécution des tests d'intégration

---

## Périmètre

### In Scope

- `kiva_cli/core/subprocess_orchestrator.py` (ou `testing/subprocess_mock_orchestrator.py`)
- `MockedCommand` dataclass (command, args, returncode, stdout, stderr, duration)
- `SubprocessMockOrchestrator` avec modes : RECORD, REPLAY, STRICT, FAILURE
- Enregistrement automatique des appels dans un dossier `tests/fixtures/subprocess/`
- Intégration pytest fixture
- Support des wrappers PowerShell / CMD (spécificité Windows de l'écosystème)

### Out of Scope

- Mock de tous les binaires du monde (priorité : docker, kubectl, lxc, git, ecos, python)
- Remplacement complet de `unittest.mock` (complément, pas remplacement)

---

## Spécifications fonctionnelles

### API principale

```python
orchestrator = SubprocessMockOrchestrator(mode="replay", fixture_dir="tests/fixtures/subprocess")

result = orchestrator.run(["docker", "build", "-t", "demo", "."])
assert result.returncode == 0
```

### Modes

- `RECORD` : exécute vraiment et sauvegarde
- `REPLAY` : lit le mock enregistré (déterministe)
- `FAILURE` : injecte des erreurs contrôlées (pour tester les chemins d'échec)
- `PASSTHROUGH` : exécution réelle (pour debug)

---

## Critères d'acceptation

```gherkin
Given un test d'intégration qui fait docker + kubectl
When on active le Subprocess Mock Orchestrator en mode replay
Then les commandes ne touchent jamais le système réel
And les résultats sont identiques à l'enregistrement
And un événement WAL "subprocess_mock_replayed" est créé avec IntentHash
```

---

## Dépendances

- PRD-KIVA-004 (types canoniques)
- PRD-KIVA-001 (Test-Repair pourra réparer les mocks)
- PRD-KIVA-002 (Stub Generator pourra générer des mocks de subprocess)

---

## Références

- `kiva_cli/core/project_manager.py` (_deploy_docker, _deploy_kubernetes, _deploy_lxc)
- `kiva_cli/core/auto_rollback_pipeline.py`
- `tests/integration/` (beaucoup de mocks subprocess manuels aujourd'hui)
- `tests/test_auto_rollback_pipeline.py`

---

**Fin du PRD-KIVA-005**

> Ce composant est critique pour rendre les tests d'intégration rapides, déterministes et autonomes — condition nécessaire pour le mode H0 à grande échelle.
