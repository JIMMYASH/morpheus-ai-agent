# Morpheus AI Agent — consignes pour Claude Code

## Le projet
Morpheus AI Agent (MORPHEUS) est un assistant de programmation, dans le terminal, le navigateur ou
Telegram, qui imite Claude Code. Il pilote un modèle (Ollama par défaut, modèle `qwen3-coder-next`,
modèles cloud d'Ollama, llama-server, ou Claude Code). Linux, Python 3.10 ou plus. Licence MIT.
Il est lancé dans un dossier de projet avec l'alias `morpheus` (`python3 chemin/vers/morpheus.py`).
Documentation utilisateur : `DOCUMENTATION.md` (à tenir à jour avec chaque fonctionnalité).

## Communication avec l'utilisateur
- Réponds en français. L'utilisateur a des notions de Python mais n'est pas expert :
  explique simplement ce que tu changes et pourquoi.
- Avance pas à pas : une modification claire à la fois, puis les tests.
- Donne toujours les commandes exactes à lancer pour vérifier.

## Contraintes techniques (à respecter absolument)
- **Un seul fichier** : `morpheus.py`. Pas de découpage en modules.
- **Bibliothèque standard Python uniquement** (pas de pip) : urllib, json, re, ast, subprocess…
- Textes affichés, commentaires et consignes au modèle **en français**.
- Le modèle local est faible comparé à Claude : il invente des noms d'outils, oublie des
  paramètres, écrit parfois ses appels d'outils en texte, prétend avoir fini sans l'avoir fait.
  MORPHEUS doit **compenser côté code** (alias, vérifications, relances) plutôt que compter
  sur le prompt système.

## Architecture de morpheus.py (dans l'ordre du fichier)
1. CONFIG + `charger_config()` : défauts, puis `~/.config/morpheus/config.json`, puis variables
   d'environnement `MORPHEUS_*`.
2. Affichage : couleurs, diff, `AfficheurFlux` (texte en direct + rendu Markdown léger,
   masque les appels d'outils écrits en texte).
3. Chemins et permissions : `RACINE` (dossier courant), `Permissions` (o / n / t),
   commandes interdites, commandes en lecture seule, instantanés pour `/annuler`.
4. Outils : read_file, write_file, edit_file, replace_lines, bash, glob, grep, list_dir,
   web_fetch, web_search, todo_write. Schémas dans `OUTILS`, fonctions dans `FONCTIONS`,
   exécution centralisée dans `executer_outil()` (alias de noms et de paramètres, mode plan).
5. Communication modèle : `appeler_modele()` (streaming Ollama `/api/chat` ou llama-server
   `/v1/chat/completions`), `extraire_appels_texte()` (appels écrits en XML, JSON ou pseudo-code).
5 bis. Claude Code (modèles `claude-code`, `claude-code:opus`…) : `traiter_demande_claude()` lance `claude -p` en
   « stream-json » (`--permission-prompt-tool stdio`, `--setting-sources ""`, outils limités, `--resume` avec l'identifiant
   `session_claude` gardé dans le message assistant du journal). Chaque demande d'autorisation passe par `decision_claude()`,
   qui applique les règles de MORPHEUS (interdits, écriture par bash, mode Chat/plan, `PERMISSIONS`, instantanés pour
   `/annuler`). Réservé à l'administrateur (`ETAT["invite"]`). Tests : `tests/faux_claude.py` (test48, test49) ;
   `lance_tests.sh` pointe `MORPHEUS_CLAUDE` vers un chemin inexistant pour ne jamais lancer le vrai programme.
6. Conversation : compactage par résumé, prompt système, `MORPHEUS.md` du projet injecté dans
   la première demande, journal des sessions, `traiter_demande()` (boucle agentique avec
   relances, vérification « aucun fichier modifié », blocage des appels répétés).
7. Interface web (`morpheus --web`) : `SessionWeb` (une par personne : projet, conversation,
   autorisations, événements, validations), `ServeurWeb` (les sessions + le moteur qui traite les
   demandes une à une dans une file d'attente ; `activer(session)` fait pointer les variables
   globales RACINE, ETAT, PERMISSIONS, FICHIERS_LUS, TACHES, POINTS_RESTAURATION, STATS vers la
   session servie), `ConsoleWeb` (remplace sys.stdout : chaque ligne affichée devient un
   événement), `GestionnaireWeb` (API HTTP + flux SSE), `PAGE_WEB` (page HTML/CSS/JS). Le code
   exécuté par les requêtes HTTP ne doit jamais lire ces variables globales (elles appartiennent à
   la personne servie par le moteur) : il passe par la session. Les points d'accroche
   `if WEB is not None` n'ont aucun effet dans le terminal.
8. Telegram (`morpheus --telegram` configure, puis le bot tourne dans `--web`) : `BotTelegram` a sa propre
   session (droits de l'administrateur) qui démarre dans les Discussions, hors projet (`/start` y revient,
   `/projets` ouvre un projet, `/nouveauprojet Nom` en crée un et l'ouvre) ; ses conversations sont visibles dans le navigateur. Il lit les messages
   par `getUpdates` (aucun port ouvert), renvoie les événements de la session (texte, outils, diff,
   questions avec boutons). Réglages dans `~/.config/morpheus/telegram.json` (mode 600) ;
   `MORPHEUS_URL_TELEGRAM` redirige l'API (les tests utilisent un faux serveur sur le port 18091).
9. `main()` : arguments `-c` (reprise), `-p` (mode script), `--web`, `--telegram`, commandes `/aide`, `/annuler`,
   `/chat`, `/dev`, `/mode`, `/plan`, `/taches`, `/init`, `/compacter`, `/reset`, `/contexte`, `/config`, `/quitter`
   (logique partagée avec le web : `envoyer_demande()`, `commande_annuler()`, `basculer_mode_plan()`, `changer_mode()`).
   Modes : « Chat » (par défaut, `CONFIG["mode"]` / `MORPHEUS_MODE`) = lecture, bash en lecture seule et web ;
   outils d'écriture retirés (`outils_actifs()`) et refusés dans `executer_outil()`. « dev » = modifications
   (toujours avec validation). Les tests tournent en `MORPHEUS_MODE=dev` sauf test42/test43.
   Modes de conversation (ton des réponses, indépendant de Chat/dev) : `STYLES` (10 modes intégrés) + modes
   personnels de `~/.config/morpheus/modes.json` (`styles_disponibles()`, relu à chaque usage) + `REGLES_COMMUNES`,
   section « Style de réponse » du prompt système (`texte_style()`), changés par `/style nom`, le menu de la
   ligne de saisie (`/api/style`) ou les boutons Telegram ; `appliquer_style()`
   réécrit le prompt système et joint un rappel à la demande suivante ; choix mémorisé (`CONFIG["style"]`).

## Règles de sécurité à ne jamais affaiblir
- Toute écriture de fichier et toute commande bash non lecture seule demande une validation. Seule exception :
  le mode auto (`/auto`, case « Auto », `ETAT["auto"]`, désactivé au lancement), que l'utilisateur active lui-même :
  modifications de fichiers DANS le projet sans question, commandes jugées « sûres » par le modèle en cours
  (`juger_commande()`, tout doute ou réponse illisible = question). Il n'agit jamais en mode Chat, en mode plan, en -p,
  pour un invité, hors du projet, ni sur les commandes interdites ou l'écriture par bash (`mode_auto_actif()`).
- `sudo`, `su`, `pkexec`, `mkfs`, `dd of=/dev`, `rm -rf /`, `reboot`… restent toujours refusés.
- Écrire un fichier via bash (cat >, echo >, heredoc redirigé vers un fichier ou lu par un shell, sed -i)
  est refusé (un heredoc qui envoie du code à `python3 -` reste permis, avec validation) : le modèle doit
  passer par write_file / edit_file / replace_lines (aperçu + `/annuler`).
- « toujours » (t) ne doit jamais autoriser une commande chaînée dangereuse (`cd x && rm …`) :
  chaque segment d'une commande est vérifié séparément.
- Une commande n'est « lecture seule » que si aucune de ses options n'écrit, ne supprime ou ne lance
  un autre programme (`git branch -D`, `sort -o`, `find -fprintf`, `env <programme>`… demandent une
  validation) : vérifier option par option dans `commande_lecture_seule()`.
- Une commande bash arrêtée (délai dépassé, Ctrl+C) doit l'être avec tout son groupe de processus :
  aucun programme lancé par elle ne doit continuer à tourner.
- Les lectures hors du dossier du projet demandent une autorisation.
- En mode `-p`, toute action à valider est refusée automatiquement (le modèle continue sans elle).
- Interface web : jeton obligatoire sur toute l'API (sauf la page et `/api/connexion`), en-tête
  `X-Morpheus` exigé sur chaque POST (CSRF), fichiers lus par le volet limités au projet, dossiers
  ouvrables limités à `~/projets`, aux discussions, au dossier de lancement et aux dossiers qui ont
  déjà des conversations (jamais `~` ni `/`), validations toujours demandées. Un invité ne voit que
  son espace `~/projets-partages/<nom>/` ; paramètres et gestion des invités réservés à
  l'administrateur ; fichiers de jetons en mode 600.
- Telegram : le bot n'obéit qu'au compte enregistré (numéro de l'expéditeur ET de la conversation privée),
  y compris pour les boutons de validation ; il ne fait jamais `print()` (sys.stdout = la page web).

## Tests — obligatoires après chaque modification
```bash
bash tests/lance_tests.sh
```
- Les tests utilisent un **faux serveur** (`tests/faux.py`, ports 18434 et 18080) qui rejoue
  des réponses scriptées du modèle : aucun vrai modèle n'est appelé, ils ne gênent pas Ollama.
- Chaque test lance morpheus.py dans un dossier temporaire et lui envoie des saisies clavier.
- Pour toute nouvelle fonctionnalité ou correction, **ajoute un test** `tests/testNN.py` sur le
  modèle des existants (liste `faux.SCRIPT` de réponses, puis saisies via `input=`).
- Ne considère jamais une modification comme terminée si un test échoue.

## Déboguer un comportement réel
Chaque session est enregistrée dans `~/.local/share/morpheus/sessions/*.jsonl`.
Le champ `brut` contient la réponse exacte du modèle avant traitement : c'est là qu'il faut
regarder quand le modèle se comporte bizarrement (appel d'outil mal formé, etc.).

## Git
Le dossier est un dépôt git. Fais un commit après chaque modification validée par les tests,
avec un message en français qui décrit le changement.
