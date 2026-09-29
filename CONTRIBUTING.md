# Contribuer à Morpheus AI Agent

Merci de ton intérêt ! Quelques principes font l'identité du projet : merci de les respecter.

## Principes

- **Un seul fichier** : tout le programme est dans `morpheus.py` (on l'installe en copiant un fichier).
  Pas de découpage en modules.
- **Bibliothèque standard uniquement** : aucune dépendance pip (urllib, json, re, subprocess…).
- **En français** : textes affichés, commentaires, consignes au modèle, messages de commit.
- **Compenser dans le code** les faiblesses des modèles locaux (noms d'outils inventés, paramètres
  oubliés, appels écrits en texte, « c'est fait » sans l'avoir fait) plutôt que compter sur le prompt.
- **Linux**, Python 3.10 ou plus.

## Règles de sécurité à ne jamais affaiblir

- Toute écriture de fichier et toute commande bash qui n'est pas en lecture seule demande une
  validation (seule exception : le mode auto, activé explicitement par l'utilisateur, limité au
  projet et aux commandes jugées sûres).
- `sudo`, `su`, `pkexec`, `mkfs`, `dd of=/dev`, `rm -rf /`, `reboot`… restent toujours refusés, et
  chaque segment d'une commande enchaînée est vérifié séparément.
- Écrire un fichier via bash (`cat >`, `echo >`, heredoc, `sed -i`) est refusé : le modèle passe par
  ses outils d'écriture (aperçu + `/annuler`).
- Une commande « lecture seule » est vérifiée option par option (`git branch -D`, `sort -o`,
  `find -delete`… demandent une validation).
- Une commande arrêtée l'est avec tous les programmes qu'elle a lancés.
- Lectures hors du projet : autorisation demandée. Mode `-p` : toute action à valider est refusée.
- Interface web : jeton obligatoire, en-tête anti-CSRF sur chaque POST, fichiers et dossiers
  accessibles limités, invités cantonnés à leur espace, fichiers de jetons en mode 600.
- Telegram : le bot n'obéit qu'au compte enregistré.

Le détail de l'architecture du fichier et de ces règles est dans `CLAUDE.md` (consignes également
utilisées par Claude Code quand il travaille sur le projet).

## Tests

```bash
bash tests/lance_tests.sh
```

Chaque `tests/testNN.py` lance `morpheus.py` dans un dossier temporaire face à un faux serveur de
modèle (`tests/faux.py`) qui rejoue des réponses scriptées : aucun vrai modèle n'est appelé. Claude
Code est simulé par `tests/faux_claude.py`, Telegram par un faux serveur local.

- **Toute correction ou fonctionnalité doit avoir son test** (sur le modèle des existants : liste
  `faux.SCRIPT` de réponses, puis saisies clavier via `input=`).
- Une modification n'est terminée que si **tous** les tests passent.
- Mets à jour `DOCUMENTATION.md` si le comportement visible change.

## Déboguer

Chaque session est enregistrée dans `~/.local/share/morpheus/sessions/*.jsonl` ; le champ `brut`
contient la réponse exacte du modèle avant traitement.
