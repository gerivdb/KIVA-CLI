---
type: GUI
version: 1.0.0
intent_hash: 0xBDCP_GITHUB_API_FALLBACK_20260818
---

# BDCP GitHub API Fallback -- Regle KiloCode

## Objectif
Permettre la creation de repos GitHub distants sans desactiver le mode BDCP, en contournant l'interdiction de `gh repo create` par un appel API direct authentifie via keyring.

## Declencheur
Toute action necessitant la creation d'un repo GitHub distant alors que :
- `gh repo create` est interdit par la regle BDCP
- Le repo n'existe pas encore sur GitHub
- Un token GitHub est disponible via le keyring systeme

## Protocole obligatoire

### Etape 1 -- Verifier la SOT
```
GET gerivdb/GOVERNANCE-HUB/known_repositories.yaml
-> Chercher full_name = gerivdb/<REPO_CIBLE>
-> Verifier do_not_create: true
-> Si do_not_create: true et repo n'existe pas sur GitHub -> continuer
-> Si do_not_create: false -> STOP, demander HITL
```

### Etape 2 -- Extraire le token du keyring
```powershell
# Option A: via gh CLI (recommande)
cmd /c "C:\gh\bin\gh.exe auth token"

# Option B: via Python keyring
python -c "import keyring; print(keyring.get_password('gh:github.com', 'user'))"
```

### Etape 3 -- Creer le repo via API GitHub (PAS gh CLI)
```python
import requests

token = "<TOKEN_EXTRAIT>"
headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github.v3+json"
}

# Pour un utilisateur
resp = requests.post("https://api.github.com/user/repos",
                     headers=headers,
                     json={"name": "FLEX", "private": True})

# Pour une organisation
resp = requests.post("https://api.github.com/orgs/gerivdb/repos",
                     headers=headers,
                     json={"name": "FLEX", "private": True})
```

### Etape 4 -- Configurer le remote git
```powershell
git -C "D:\DO\WEB\TOOLS\L4-TOOLS\FLEX" remote set-url origin https://github.com/gerivdb/FLEX.git
```

### Etape 5 -- Pousser les commits
```powershell
git -C "D:\DO\WEB\TOOLS\L4-TOOLS\FLEX" push origin main
```

## Garde-fous

- [INTERDIT] JAMAIS utiliser `gh repo create` (interdit par BDCP)
- [INTERDIT] JAMAIS desactiver le mode BDCP pour creer un repo
- [OK] TOUJOURS utiliser l'API GitHub directe avec token keyring
- [OK] TOUJOURS verifier `do_not_create` dans known_repositories.yaml avant creation
- [OK] TOUJOURS utiliser `git remote set-url` + `git push` (pas `gh`)

## Cas d'usage

| Situation | Action |
|-----------|--------|
| Repo reference dans SOT mais absent de GitHub | Creer via API + keyring |
| Repo non reference dans SOT | STOP -- demander HITL + ADR |
| Token absent du keyring | STOP -- demander authentification manuelle |

## Reference ADR
- **ADR** : ADR-0022-github-api-fallback
- **IntentHash** : 0xADR_0022_GITHUB_API_FALLBACK_20260818
- **Depot** : gerivdb/GOVERNANCE-HUB
- **Statut ADR** : proposed
- **Maj requise si** : statut ADR -> deprecated ou superseded
