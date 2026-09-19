# Runbook - Contournement ALFRED pour push urgent

## Contexte
ALFRED peut bloquer un push direct sur `master` ou `main` lorsque la branche de feature ne respecte pas la taxonomie unifiée `type/jurisdiction-slug-id`.

## Cas d'usage
- Merge local validé d'une branche de feature non conforme
- Urgence de libération d'un stash massif
- Correction critique nécessitant un push direct

## Procédure

### 1. Vérifier l'état du repo
```bash
git status
git log --oneline -5
```

### 2. Effectuer le merge local (si applicable)
```bash
git checkout master
git merge --no-ff feat/<branch-name>
```

### 3. Push avec contournement
```bash
git push --no-verify origin master
```

### 4. Documenter le contournement
Créer un fichier `BACKPORT_ALFRED_BYPASS.md` ou `REPORTS/stash-recovery-report.md` dans le repo concerné avec :
- Contexte du contournement
- Justification
- Preuve d'exécution (commit, date, branche)

### 5. Reconstituer la trace BRGS
- Créer une branche `docs/alfred-bypass-<repo>` depuis `master`
- Ajouter le document de justification
- Pousser la branche
- Ouvrir une PR vers `master` (si la politique du repo l'exige)

## Prévention
- Toujours utiliser des noms de branches conformes à la taxonomie
- Éviter les commits massifs (>100 fichiers)
- Préférer les merges via KIVA-CLI/ECOS-CLI plutôt que `git merge` direct

## Références
- ADR-2026-06-07-001-ADR-GOVERNANCE-GATE
- Règle `bdcp-kiva-workflow.md`
