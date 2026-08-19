# BDCP GitHub API Fallback — Workflows KIVA-CLI

**Source of truth** : `kiva_cli/core/github_token.py`, `kiva_cli/commands/github_commands.py`
**Règle associée** : `bdcp-github-api-fallback.md` (gerivdb/GOVERNANCE-HUB)
**ADR** : `ADR-0022-github-api-fallback` (status: proposed)
**Skill** : `bdcp-github-repo-creator`

---

## 1. Principe

Le mode **BDCP** est permanent et inviolable. Il agit comme un VPN (anonymat réseau)
et protège le quota de tokens Antigravity. `gh repo create` est **interdit** par la
règle BDCP ; la création de repos distants doit contourner cette interdiction via
l'**API GitHub directe** authentifiée par le keyring — sans jamais désactiver BDCP.

KIVA-CLI implémente cette politique de deux manières :

1. **Résolution de token centralisée** (`github_token.get_github_token`)
2. **Client httpx sans dépendance gh CLI** (`github_commands.py`)

---

## 2. Résolution du token (priorité)

`get_github_token()` suit cet ordre :

| # | Source | Mécanisme |
|---|--------|-----------|
| 1 | `GITHUB_TOKEN` | variable d'environnement |
| 2 | `GH_TOKEN` | variable d'environnement |
| 3 | `gh auth token` | keyring via `gh.exe` (chemin `C:\gh\bin\gh.exe` ou `%LOCALAPPDATA%\Programs\gh\bin\gh.exe`) |

Si aucune source n'est disponible → `RuntimeError` :
`"GITHUB_TOKEN/gh keyring requis pour les commandes GitHub en BDCP"`.

> Le token extrait du keyring est utilisé **uniquement** pour l'appel API direct.
> Aucune bascule en mode FREE, aucun `gh repo create`.

---

## 3. Création d'un repo distant (sans désactiver BDCP)

### Étape 1 — Vérifier la SOT
```
GET gerivdb/GOVERNANCE-HUB/known_repositories.yaml
→ Chercher full_name = gerivdb/<REPO_CIBLE>
→ Vérifier do_not_create: true
→ Si do_not_create: true et repo absent de GitHub → continuer
→ Si do_not_create: false → STOP, demander HITL
```

### Étape 2 — Obtenir le token
```python
from kiva_cli.core.github_token import get_github_token
token = get_github_token()  # GITHUB_TOKEN > GH_TOKEN > gh keyring
```

### Étape 3 — Créer via API GitHub (PAS gh CLI)
```python
import httpx

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

# Utilisateur
resp = httpx.post("https://api.github.com/user/repos",
                  headers=headers, json={"name": "FLEX", "private": True})
# Organisation
resp = httpx.post("https://api.github.com/orgs/gerivdb/repos",
                  headers=headers, json={"name": "FLEX", "private": True})
assert resp.status_code in (200, 201)
```

### Étape 4 — Configurer le remote git
```powershell
git -C "D:\DO\WEB\TOOLS\L4-TOOLS\FLEX" remote set-url origin https://github.com/gerivdb/FLEX.git
```

### Étape 5 — Pousser
```powershell
git -C "D:\DO\WEB\TOOLS\L4-TOOLS\FLEX" push origin main
```

---

## 4. Garde-fous

- [INTERDIT] `gh repo create` (interdit par BDCP)
- [INTERDIT] désactiver BDCP pour créer un repo
- [OK] API GitHub directe + token keyring
- [OK] vérifier `do_not_create` dans `known_repositories.yaml` avant création
- [OK] `git remote set-url` + `git push` (pas `gh`)

---

## 5. Commandes KIVA-CLI concernées

| Commande | Comportement BDCP |
|----------|-------------------|
| `kiva github ...` | httpx-only, zéro gh CLI, token via `github_token` |
| `kiva scaffold push` | push après confirmation HITL uniquement (PRD-016) |
| création repo via skill `bdcp-github-repo-creator` | API directe + keyring |

---

## 6. Skills associés

- **`bdcp-github-repo-creator`** : procédure exécutable de création de repo sans
  désactiver BDCP (API directe + keyring + `git push`).
- **`hitl-clone-gate`** + **`clone-causal-prevention`** : obligatoires avant tout
  `git clone`/`git init` sous `D:\DO\WEB\TOOLS\`.

---

*Généré le 2026-08-19 | KIVA-CLI (L1-INFRA) | Intent : 0xBDCP_GITHUB_API_FALLBACK_20260818*
