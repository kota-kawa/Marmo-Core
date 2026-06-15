---
name: "newbranche"
description: "Use when the user asks to create/open a new working branch from main with a unique name, without reusing old branch names."
---

# newbranche

Objectif: creer une branche de travail neuve depuis `main` avec un nom unique, puis basculer dessus.

Regles:
- Toujours partir de `main` a jour localement.
- Ne jamais re-utiliser un ancien nom de branche si l'utilisateur demande une branche "nouvelle".
- Utiliser un suffixe horodate pour garantir l'unicite.
- Verifier la branche finale et afficher son nom.

Workflow standard:
1. Verifier la branche courante et l'etat du repo.
2. Basculer sur `main`.
3. Creer un nom unique, format recommande: `wip-YYYYMMDD-HHMM`.
4. Creer et basculer: `git switch -c <nom_unique>`.
5. Verifier: `git branch --show-current` et `git status --short --branch`.

Commande PowerShell recommandee (atomique):

```powershell
git switch main;
$stamp = Get-Date -Format "yyyyMMdd-HHmm";
$branch = "wip-$stamp";
git switch -c $branch;
git branch --show-current;
git status --short --branch
```

Si la branche existe deja (rare):
- Regenerer un nom avec secondes: `wip-YYYYMMDD-HHMMss`.
- Reessayer la creation.

Option sauvegarde distante (si demandee):

```powershell
git push -u origin <nom_unique>
```
