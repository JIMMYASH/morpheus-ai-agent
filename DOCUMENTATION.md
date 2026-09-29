# Morpheus AI Agent — documentation complète

Morpheus AI Agent (MORPHEUS) est un assistant de programmation qui travaille dans ton
dossier de projet, à la manière de Claude Code : il lit tes fichiers, les modifie, lance des
commandes, cherche sur le web… et te demande ton accord avant chaque action qui change quelque chose.

Il fonctionne avec un **modèle local** (Ollama ou llama-server), un **modèle cloud d'Ollama**
(ex. `kimi-k2.7-code:cloud`), ou en pilotant **Claude Code** avec ton abonnement Claude.
On l'utilise au choix dans le **terminal**, dans le **navigateur** (interface web, aussi depuis
d'autres appareils du réseau) ou depuis **Telegram**.

Tout tient dans un seul fichier, `morpheus.py`, qui n'utilise que la bibliothèque standard de
Python : rien à installer avec pip.

---

## Sommaire

1. [Installation et lancement](#1-installation-et-lancement)
2. [Premiers pas](#2-premiers-pas)
3. [Les modes de travail : Chat, Développeur, Plan, Auto](#3-les-modes-de-travail)
4. [Validations et sécurité](#4-validations-et-sécurité)
5. [Les modèles : Ollama, cloud, llama-server, Claude Code](#5-les-modèles)
6. [Les modes de conversation (ton des réponses)](#6-les-modes-de-conversation)
7. [Commandes du terminal](#7-commandes-du-terminal)
8. [Interface web](#8-interface-web)
9. [Telegram](#9-telegram)
10. [Mémoire, consignes et conversations](#10-mémoire-consignes-et-conversations)
11. [Les outils du modèle](#11-les-outils-du-modèle)
12. [Configuration](#12-configuration)
13. [Fichiers et dossiers utilisés](#13-fichiers-et-dossiers-utilisés)
14. [Dépannage](#14-dépannage)
15. [Pour les développeurs](#15-pour-les-développeurs)

---

## 1. Installation et lancement

### Ce qu'il faut

- **Linux** (développé et testé sous Ubuntu ; macOS et Windows ne sont pas pris en charge) avec
  **Python 3.10 ou plus récent**.
- **Ollama** qui tourne (`systemctl status ollama`), avec au moins un modèle (`ollama list`), ou
  un modèle cloud après `ollama signin`. À la place : **llama-server** (llama.cpp), ou
  **Claude Code** (programme `claude`, voir § 5.4).
- Facultatif : `pdftotext` (paquet `poppler-utils`) pour lire les PDF ; une instance **SearXNG**
  pour une meilleure recherche web.

### Installation

Il suffit de récupérer le dossier (ou même le seul fichier `morpheus.py`) et de créer un alias :

```bash
git clone https://github.com/JIMMYASH/morpheus-ai-agent.git ~/outils/morpheus
echo "alias morpheus='python3 ~/outils/morpheus/morpheus.py'" >> ~/.bashrc
source ~/.bashrc
```

Le logo `morpheus.png`, s'il est placé à côté de `morpheus.py`, s'affiche dans l'interface web ;
sans lui, le titre texte suffit.

### Les façons de le lancer

| Commande | Effet |
|---|---|
| `morpheus` | Nouvelle session dans le dossier courant (qui devient le projet) |
| `morpheus -c` | Reprend la dernière conversation de ce dossier |
| `morpheus "ta demande"` | Démarre directement avec cette demande |
| `morpheus -p "question"` | Répond une fois puis quitte, sans interaction (voir § 4) |
| `morpheus --web` | Interface web (options `--port 8765`, `--hote 0.0.0.0`) |
| `morpheus --telegram` | Relie un bot Telegram à ton compte (une seule fois) |
| `MORPHEUS_MODELE=claude-code morpheus` | Utilise Claude Code pour cette session |
| `MORPHEUS_MODE=dev morpheus` | Démarre directement en mode développeur |

> Lance toujours MORPHEUS **dans le dossier du projet** (`cd ~/projets/mon-projet` puis `morpheus`).
> Lancé depuis ton dossier personnel, il te prévient.

### L'interface web en service permanent

Pour que l'interface web tourne en permanence (et démarre avec la session), crée le service
utilisateur `~/.config/systemd/user/morpheus.service` :

```ini
[Unit]
Description=MORPHEUS — interface web
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=%h/projets
ExecStart=/usr/bin/python3 %h/outils/morpheus/morpheus.py --web --port 8765
Environment=PYTHONUNBUFFERED=1
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

puis active-le avec `systemctl --user daemon-reload && systemctl --user enable --now morpheus`.
Ensuite :

```bash
systemctl --user status morpheus      # état
systemctl --user restart morpheus     # à faire après chaque modification de morpheus.py
journalctl --user -u morpheus -f      # messages du service
```

Un programme Python ne relit pas son fichier en cours de route : **après une mise à jour de
`morpheus.py`, redémarre le service**, sinon l'interface web reste sur l'ancienne version.

---

## 2. Premiers pas

```text
$ cd ~/projets/calculs
$ morpheus
Morpheus AI Agent — ollama · qwen3-coder-next · contexte 65536
Projet : /home/moi/projets/calculs
Mode Chat : questions, lecture et recherche web, aucune modification. /dev pour le mode développeur.

chat> Que fait ce projet ?
● list_dir(.)
● read_file(calcul.py)
● Ce projet contient une petite calculatrice…

chat> /dev
Mode développeur : MORPHEUS peut créer, modifier et supprimer (avec ta validation).

> Ajoute une fonction de division qui refuse la division par zéro
● read_file(calcul.py)
● edit_file(calcul.py)
   --- calcul.py (avant)
   +++ calcul.py (après)
   +def diviser(a, b):
   +    if b == 0:
   +        raise ValueError("division par zéro")
   +    return a / b
   Appliquer cette modification ? [o]ui / [n]on / [t]oujours (modifs de fichiers du projet) : o
● J'ai ajouté la fonction diviser() dans calcul.py.
```

Conseils :
- Écris une demande précise, comme à un collègue. Termine une ligne par `\` pour continuer sur la
  ligne suivante.
- **Ctrl+C** interrompt le modèle ou la commande en cours ; **Ctrl+D** ou `/quitter` pour sortir.
- `/init` crée un fichier `MORPHEUS.md` qui décrit le projet : les sessions suivantes démarrent
  en le connaissant (§ 10).

---

## 3. Les modes de travail

### Chat (au lancement, par défaut)

Pour poser des questions sans risque. MORPHEUS peut **lire** les fichiers, lancer des commandes
**en lecture seule** (`ls`, `git status`, `df -h`…) et **chercher sur le web**. Il ne peut **rien
créer, modifier ni supprimer** : les outils d'écriture ne lui sont même pas proposés, et une tentative
est refusée. S'il faut modifier quelque chose, il te propose de passer en mode développeur.

L'invite est `chat>`.

### Développeur (`/dev`)

MORPHEUS peut créer, modifier, supprimer des fichiers et lancer des commandes, **toujours avec ta
validation** (§ 4). L'invite est `>`. `/chat` pour revenir au mode Chat, `/mode` pour basculer.

Le mode au lancement se règle avec `"mode": "chat"` ou `"dev"` dans `config.json`, ou `MORPHEUS_MODE`.

### Plan (`/plan`, en mode développeur)

MORPHEUS explore le projet en lecture seule et propose un **plan détaillé et numéroté**, sans rien
modifier. `/plan` à nouveau pour quitter le mode plan et lui demander de l'exécuter. L'invite est
`plan>`.

### Auto (`/auto`, en mode développeur)

Pour travailler sans être interrompu à chaque étape, comme l'« auto mode » de Claude Code :

- les **modifications de fichiers du projet** sont appliquées sans question (l'aperçu reste affiché,
  et `/annuler` fonctionne toujours) ;
- chaque **commande qui écrit** est d'abord **jugée par le modèle en cours** (un appel spécial, avec
  une consigne de sécurité) :
  - jugée **sûre** (lancer les tests, `mkdir`, `git add`, `git commit`…) : exécutée directement,
    avec la raison affichée ;
  - jugée **à vérifier** (suppression, `git push`, `curl … | bash`, installation, lecture de
    secrets, commande sans rapport avec la demande…) : la question habituelle t'est posée, avec la
    raison ;
  - si le juge hésite ou répond de travers : la question t'est posée.

Ce que le mode auto **ne fait jamais** : autoriser une commande interdite (`sudo`…) ou l'écriture de
fichier par bash, modifier ou lire hors du projet sans te demander, agir en mode Chat, en mode plan
ou en `-p`. Il est **désactivé à chaque lancement** et **réservé à l'administrateur** dans
l'interface web. L'invite devient `auto>`.

`/auto` bascule, `/auto on` et `/auto off` sont explicites. Dans le web : la case **Auto** à côté de
« Plan » ; sur Telegram : `/auto`.

Chaque commande jugée coûte un petit appel au modèle (quelques secondes). Avec Claude Code, le juge
est Claude haiku.

---

## 4. Validations et sécurité

### Les validations o / n / t

Avant chaque action qui modifie quelque chose, MORPHEUS affiche ce qu'il va faire (un **diff**
avant/après pour un fichier, la commande complète pour bash) et demande :

- **o** (oui) : faire cette action ;
- **n** (non) : refuser. MORPHEUS demande alors « Que dois-je faire à la place ? » : ta réponse est
  transmise au modèle comme consigne, et il continue avec. **Entrée seule = arrêter la tâche** ;
- **t** (toujours) : accepter pour le reste de la session, selon la catégorie :
  - toutes les modifications de fichiers **du projet** ;
  - pour une commande : tout ce programme (ex. `pytest`), ou un préfixe (`python3 notes.py`), ou
    seulement la commande exacte pour les programmes sensibles (`rm`, `git`, `curl`, `python3`,
    `pip`, `find`, `sed`…).

Les autorisations « toujours » sont oubliées quand on change de projet dans le web ; elles sont
visibles (et remises à zéro) dans Paramètres.

### Ce qui passe sans question

Les commandes **en lecture seule** : `ls`, `cat`, `head`, `grep`, `wc`, `df`, `free`, `uname`,
`git status|diff|log|show`… Elles sont vérifiées **option par option** : `git branch -D`,
`sort -o fichier`, `find -delete`, `find -exec`, `tree -o`, `env programme`, `sed` sans `-n`… ne
sont pas de la lecture et demandent une validation.

### Ce qui est toujours refusé

- `sudo`, `su`, `pkexec`, `mkfs`, `dd of=/dev/…`, `rm -rf /` (ou `~`, `/home`), `shutdown`, `reboot`,
  `chmod … /`, la « fork bomb »… Même avec « toujours » ou en mode auto. **Chaque morceau** d'une
  commande enchaînée (`cd x && rm …`, `a ; b`, `a | b`) est vérifié séparément.
- **Écrire un fichier via bash** (`cat >`, `echo >`, `printf >`, `tee`, heredoc vers un fichier,
  `sed -i`, `perl -i`) : le modèle doit utiliser ses outils d'écriture, qui montrent un aperçu et sont
  annulables. Exception : un heredoc envoyé à `python3 -` (avec validation).

### Hors du projet

- Une **lecture** en dehors du dossier du projet demande ton autorisation (« toujours » possible).
- Une **écriture** en dehors du projet est signalée en rouge et demande une validation, sans
  « toujours ».

### `/annuler`

Restaure les fichiers modifiés pendant la **dernière demande**, y compris par une commande bash
(MORPHEUS prend un instantané du projet avant chaque commande qui écrit ; limite : fichiers de moins
de 5 Mo, 50 Mo au total). Un fichier créé est supprimé, un fichier supprimé est recréé. Le modèle est
prévenu de l'annulation.

### Commandes longues et serveurs

- Chaque commande a un délai (120 s par défaut, 600 s au plus). Au délai dépassé, sur Ctrl+C ou sur
  « Arrêter », la commande est arrêtée **avec tous les programmes qu'elle a lancés**.
- Les serveurs de développement (`flask run`, `uvicorn`, `npm run dev`, `python3 -m http.server`,
  `manage.py runserver`, `streamlit run`…) tournent 15 s pour vérifier qu'ils démarrent, puis sont
  arrêtés : MORPHEUS te donne la commande pour les lancer toi-même.
- Les commandes n'ont pas accès au clavier : une commande qui attend un mot de passe (`git push` en
  HTTPS, `ssh` avec phrase de passe) échoue au lieu de bloquer.

### Mode `-p` (script)

`morpheus -p "question"` répond puis quitte. **Toute action à valider est refusée
automatiquement** : le modèle continue sans elle et te dit ce qu'il faudrait faire toi-même.

---

## 5. Les modèles

### 5.1 Ollama (par défaut)

Le modèle est choisi par `"modele"` dans `config.json`, par `MORPHEUS_MODELE`, ou dans la liste
déroulante de l'interface web. `num_ctx` (65 536 par défaut) fixe la taille du contexte ;
`keep_alive` (30 min) garde le modèle chargé entre deux questions.

**Modèle pas encore installé** : si tu choisis dans l'interface web (liste ou « Autre modèle… ») un
modèle qui existe dans la bibliothèque d'Ollama mais n'est pas sur ta machine, MORPHEUS propose de le
télécharger en indiquant sa taille (« Le télécharger maintenant (1,3 Go) ? »). La progression
s'affiche à côté de la liste des modèles (✕ pour annuler) ; tu peux continuer à travailler pendant ce
temps, et le modèle est choisi automatiquement à la fin. Un nom inconnu est simplement refusé. Un
seul téléchargement à la fois, réservé à l'administrateur. Dans le terminal : `ollama pull nom`.

### 5.2 Modèles cloud d'Ollama

Après `ollama signin`, un modèle cloud (ex. `kimi-k2.7-code:cloud`, `gpt-oss:120b-cloud`) s'utilise
comme un modèle local : il suffit de mettre son nom. Ils n'apparaissent pas parmi les modèles
installés : l'interface web les propose dans le groupe « Cloud et récents » (ou « Autre modèle… »).

### 5.3 llama-server (llama.cpp)

`"serveur": "llamacpp"` et `"url_llamacpp": "http://127.0.0.1:8080"` : MORPHEUS utilise alors
l'API `/v1/chat/completions`. Les réglages d'échantillonnage (`temperature`, `top_p`, `top_k`,
`repeat_penalty`) valent pour les deux serveurs ; laissés vides, ce sont les réglages recommandés
du modèle.

### 5.4 Claude Code

MORPHEUS peut piloter **Claude Code** (le programme `claude`, avec ton abonnement Claude, sans clé
API). On le choisit comme un modèle :

| Modèle | Effet |
|---|---|
| `claude-code` | Le modèle par défaut de Claude Code (selon ton abonnement et le réglage `/model` de `claude`) |
| `claude-code:opus` | Le dernier Opus : le plus capable, consomme plus vite tes limites d'utilisation |
| `claude-code:sonnet` | Bon compromis qualité / rapidité |
| `claude-code:haiku` | Le plus rapide, pour les questions simples |

Choix : liste des modèles dans le web (réservé à l'administrateur), ou
`MORPHEUS_MODELE=claude-code morpheus` dans le terminal.

**Comment ça marche.** Claude Code fait le travail avec ses propres outils (Read, Edit, Write, Bash,
Glob, Grep, WebFetch, WebSearch, liste de tâches), mais **chaque action qui demande une autorisation
est demandée à MORPHEUS**, qui applique ses propres règles : aperçu et validation o / n / t,
commandes interdites, écriture par bash refusée, mode Chat (outils d'écriture retirés), mode plan,
mode auto, lectures hors projet, `/annuler`. Un refus avec consigne est transmis à Claude Code ; un
refus sans consigne l'arrête. Les réglages personnels de Claude Code (règles d'autorisation
automatique) sont ignorés, pour que tout passe par MORPHEUS. Les sous-agents et tâches planifiées de
Claude Code ne sont pas proposés.

La conversation continue d'une demande à l'autre (et avec `morpheus -c`) : MORPHEUS garde
l'identifiant de session de Claude Code dans son journal. « Arrêter » coupe Claude Code et tout ce
qu'il a lancé.

Installation de Claude Code, si besoin : `curl -fsSL https://claude.ai/install.sh | bash`, puis
lancer `claude` une fois pour se connecter.

**Limites** : `/compacter` est sans effet (Claude Code gère sa conversation lui-même) ; en changeant
de modèle en pleine conversation, Claude Code ne voit pas les échanges précédents ; dans le web,
« Modifier » un ancien message ne l'efface pas de la mémoire de Claude Code ; les invités ne peuvent
pas l'utiliser (c'est ton abonnement).

---

## 6. Les modes de conversation

Indépendants de Chat / Développeur, ils règlent **le ton et la forme** des réponses :

| Mode | Pour quoi |
|---|---|
| 💬 Par défaut | Réponses courtes et directes |
| ⚡ Synthèse | 3 lignes maximum, l'essentiel d'abord |
| 🎓 Expert | Technique et précis, pour public averti |
| 🧑‍🏫 Pédagogique | Explications progressives, analogies simples |
| 🪜 Pas à pas | Étapes numérotées, commandes à copier |
| 🔍 Relecteur | Critique : bugs, risques, points fragiles |
| 🧭 Coach | Te guide par des questions, sans donner la réponse |
| ⚖️ Comparatif | Options, pour et contre, recommandation |
| 😈 Avocat du diable | Cherche les failles de ton idée |
| ✍️ Rédaction | Français soigné : courriel, README, documentation |

Changer : `/style expert` (accents et espaces acceptés : `/style Pas à pas` ; raccourcis `court`,
`pedago`, `critique`, `avocat`…), `/style` seul pour voir la liste ; dans le web, le menu de la ligne
de saisie ; sur Telegram, `/style` puis un bouton. Le choix est mémorisé pour les lancements suivants.
Quel que soit le mode, MORPHEUS répond en français, n'invente pas de faits et s'en tient à la demande.

### Tes propres modes

Crée `~/.config/morpheus/modes.json` (relu à chaque usage, pas besoin de relancer) :

```json
{
  "Juriste": {"icone": "📜", "description": "Cite les textes de loi",
              "consignes": ["Cite l'article de loi exact.", "Distingue le droit et l'usage."]},
  "Poète": "Réponds en alexandrins."
}
```

20 modes au plus, 10 consignes par mode ; un mode intégré garde son nom.

---

## 7. Commandes du terminal

| Commande | Effet |
|---|---|
| `/aide` | Aide |
| `/chat` · `/dev` · `/mode` | Mode Chat, mode développeur, bascule entre les deux |
| `/plan` | Mode plan on/off (en mode développeur) |
| `/auto` · `/auto on` · `/auto off` | Mode auto |
| `/annuler` | Annule les modifications de fichiers de la dernière demande |
| `/taches` | Liste des tâches tenue par le modèle |
| `/init` | Crée ou améliore `MORPHEUS.md` (en mode développeur) |
| `/style [nom]` | Mode de conversation |
| `/compacter` | Résume la conversation pour libérer du contexte |
| `/reset` | Nouvelle conversation |
| `/contexte` | Taille de la conversation (tokens) |
| `/config` | Configuration utilisée |
| `/quitter` | Quitter (ou Ctrl+D) |

Après chaque réponse, une barre d'état affiche la taille du contexte, la vitesse (tokens/s) et les
modes actifs. Les flèches haut/bas rappellent les saisies précédentes (historique conservé).

---

## 8. Interface web

### Lancement et connexion

`morpheus --web` (ou le service, § 1) affiche deux liens contenant le **jeton d'accès** : un pour
cette machine, un pour le réseau local (téléphone, autre ordinateur). Le jeton est ensuite mémorisé
dans le navigateur. Il est enregistré dans `~/.config/morpheus/jeton_web` ; supprimer ce fichier et
relancer en crée un nouveau (les anciens liens ne marchent plus).

### L'écran

- **En-tête** : nom du projet, **liste des modèles** (« Installés », « Cloud et récents » avec les
  modèles cloud, Claude Code et les derniers utilisés, « Autre modèle… »), interrupteur
  **Chat / Développeur**, cases **Plan** et **Auto**, bouton **</> Code**, thème 🌓, menu utilisateur.
- **Écran d'accueil** : des suggestions adaptées (discussion, projet vide, projet existant, `/init`
  s'il n'y a pas de `MORPHEUS.md`). Un clic remplit la zone de saisie sans envoyer ; les « … » à
  compléter sont sélectionnés.
- **Chat** : réponses en direct, Markdown (titres, listes, tableaux, code coloré avec bouton
  « Copier »), activité des outils, bouton **Arrêter** (comme Ctrl+C). Un message déjà envoyé peut
  être **modifié** : la conversation repart de là (les fichiers déjà modifiés ne sont pas restaurés,
  utilise `/annuler`).
- **Validations** : une carte **Oui / Toujours / Non** (touches `o`, `t`, `n`) ; « Non » permet
  d'écrire une consigne.
- **Volet de code** : onglet *Fichiers* (arborescence, visionneuse avec numéros de ligne, fichiers
  modifiés marqués d'un point) et onglet *Modifications* (diff des modifications en attente de ta
  validation). Il s'ouvre tout seul quand une modification est proposée.
- **Pièces jointes** : bouton 📎 ou glisser-déposer ; les fichiers (25 Mo au plus) sont enregistrés
  dans le projet (jamais d'écrasement : « rapport (2).pdf ») et MORPHEUS est invité à les lire.
- **Barre d'état** : contexte, vitesse, mode plan ou auto, position dans la file d'attente.

Toutes les commandes du terminal s'utilisent aussi dans la zone de saisie (`/annuler`, `/plan`,
`/auto`, `/init`, `/style`, `/compacter`, `/reset`, `/reprendre`, `/taches`, `/contexte`, `/aide`).

### Projets, conversations et discussions

- **Barre de gauche** : les projets de `~/projets`, et sous le projet ouvert ses conversations (la
  plus récente en premier). Clic = rouvrir (l'historique est rejoué et le modèle le reçoit), ✎ =
  renommer, 🗑 = supprimer.
- **Nouveau projet** : crée le dossier (option `git init` + `.gitignore`) et peut envoyer une
  première demande. ✎ renomme un projet (ses conversations suivent), 🗑 le met à la **corbeille**
  d'Ubuntu (récupérable).
- **Discussions** (en haut) : conversations libres, sans projet ; pas de volet de code ni de mode
  plan.
- **Autres dossiers** : les dossiers hors de `~/projets` qui ont des conversations (par exemple
  lancés depuis le terminal) restent consultables ; « Retirer de la liste » met leurs conversations à
  la corbeille sans toucher aux fichiers.

### Paramètres (administrateur)

Serveur, modèle, URL, contexte, échantillonnage, étapes max, `keep_alive`, SearXNG — enregistrés
dans `~/.config/morpheus/config.json`. On y voit aussi les autorisations « toujours » de la session
(avec un bouton pour les effacer), le thème et la gestion des invités.

### Invités

Paramètres → Utilisateurs invités : un nom donne un **lien personnel** à envoyer (révocable).
Chaque invité a son espace `~/projets-partages/<nom>/` (projets, discussions, conversations,
autorisations, modèle) et ne voit ni tes projets ni ceux des autres. Les invités n'ont accès ni aux
paramètres, ni à Claude Code, ni au mode auto : leurs actions sont toujours validées une à une.

Le modèle traite **une demande à la fois** : les autres attendent dans une file (« ⏳ 1 demande avant
la tienne ») ; « Arrêter » retire une demande de la file.

> Les invités utilisent MORPHEUS **avec ton compte Ubuntu** : le cloisonnement est organisationnel,
> pas une vraie séparation des droits. N'invite que des personnes de confiance.

### Sécurité de l'interface

- Jeton obligatoire sur toute l'API (cookie `HttpOnly` / `SameSite=Strict`), et chaque action exige
  un en-tête que les autres sites ne peuvent pas ajouter (protection CSRF).
- Le volet de code ne lit que des fichiers du projet ; seuls `~/projets`, les discussions, le
  dossier de lancement et les dossiers ayant déjà des conversations peuvent être ouverts (jamais `~`
  ni `/`).
- Fichiers de jetons lisibles par toi seul (mode 600).
- La connexion est en **HTTP simple, non chiffrée** : à réserver à un réseau de confiance. Pour
  n'écouter que sur cette machine : `--hote 127.0.0.1`.

---

## 9. Telegram

### Configuration (une seule fois)

```bash
morpheus --telegram
```

1. Dans Telegram, écris à **@BotFather**, envoie `/newbot`, choisis un nom et un identifiant finissant
   par « bot ».
2. Colle le jeton donné par BotFather.
3. Envoie un message quelconque à ton bot depuis **ton** compte, et confirme que c'est bien toi.
4. Relance le service web : `systemctl --user restart morpheus`.

Le bot tourne ensuite **dans le serveur web** (aucun port à ouvrir : il interroge Telegram). Il
**n'obéit qu'à ton compte** (y compris pour les boutons de validation). Réglages dans
`~/.config/morpheus/telegram.json` ; pour débrancher : supprimer ce fichier et relancer le service.

### Utilisation

Écris tes demandes comme dans le web. Le bot démarre dans les **Discussions** (hors projet).

| Commande | Effet |
|---|---|
| `/projets` | Choisir le projet (boutons) |
| `/nouveauprojet Nom` | Créer un projet (avec git) et l'ouvrir |
| `/nouvelle` | Nouvelle conversation dans le projet ouvert |
| `/start` | Retour aux Discussions, nouvelle conversation |
| `/reprendre` | Rouvrir la dernière conversation du projet |
| `/style` | Mode de conversation (boutons) |
| `/chat` · `/dev` · `/auto` | Mode Chat, mode développeur, mode auto |
| `/annuler` | Annuler les modifications de la dernière demande |
| `/stop` | Arrêter la demande en cours |
| `/etat` | Projet, mode et modèle |
| `/aide` | Aide |

Validation : boutons **Oui / Toujours / Non**, ou réponds `o`, `t`, `n` (tout autre texte = non, avec
ce texte comme consigne). Les conversations Telegram apparaissent aussi dans le navigateur.

---

## 10. Mémoire, consignes et conversations

- **`MORPHEUS.md` du projet** (à la racine) : consignes permanentes pour ce projet (but, structure,
  commandes, conventions), données au modèle au début de chaque conversation. `/init` le crée ou
  l'améliore.
- **`~/.config/morpheus/MORPHEUS.md`** : tes consignes personnelles, valables dans tous les projets.
- **Journaux** : chaque conversation est enregistrée dans
  `~/.local/share/morpheus/sessions/*.jsonl` (demandes, réponses, résultats des outils, réponse
  brute du modèle dans le champ `brut`, erreurs du serveur). C'est ce qui permet `morpheus -c`, la
  liste des conversations du web… et le débogage.
- **Contexte** : au-delà de 75 % du contexte, les anciens échanges sont **résumés** par le modèle
  (`/compacter` pour le faire à la main) ; en dernier recours, les plus anciens messages sont retirés.

---

## 11. Les outils du modèle

Avec Ollama ou llama-server, le modèle dispose de ces outils :

| Outil | Rôle |
|---|---|
| `read_file` | Lit un fichier (avec `offset` / `limit`), lignes numérotées ; extrait le texte des PDF, Word, LibreOffice, Excel, PowerPoint (lecture seule) |
| `write_file` | Crée un fichier ou le réécrit entièrement (aperçu + validation) |
| `edit_file` | Remplace un passage exact (aperçu + validation) |
| `replace_lines` | Remplace ou supprime un bloc de lignes par numéro |
| `bash` | Commande non interactive dans le dossier du projet |
| `glob` | Trouve des fichiers par motif de nom |
| `grep` | Cherche une expression régulière dans les fichiers |
| `list_dir` | Liste un dossier |
| `web_fetch` | Télécharge une page web et en extrait le texte |
| `web_search` | Recherche web (SearXNG si configuré, sinon DuckDuckGo) |
| `todo_write` | Liste de tâches affichée à l'écran (`/taches`) |

En mode Chat, `write_file`, `edit_file` et `replace_lines` ne sont pas proposés.

### Ce que MORPHEUS rattrape chez un modèle faible

Les modèles locaux inventent des noms d'outils, oublient des paramètres, écrivent leurs appels en
texte ou prétendent avoir fini. MORPHEUS compense dans le code :

- appels d'outils écrits en texte (XML, JSON, pseudo-code) reconnus et exécutés, et masqués à
  l'affichage ;
- noms d'outils et de paramètres approximatifs corrigés (`file_path` → `path`, outil inventé mais
  commande fournie → `bash`…) ; `path` oublié retrouvé quand un seul fichier est en jeu ;
- JSON d'arguments tolérant (virgule finale, apostrophe échappée, nombres écrits `42.0`) ;
- numéros de ligne recopiés par erreur dans `edit_file` retirés ;
- appels identiques répétés bloqués, avec relance ; au bout de deux avertissements ignorés, un tour
  **sans outils** oblige le modèle à conclure ;
- relance si le modèle annonce une action sans la faire, ou laisse des tâches non terminées ;
- vérification qu'un fichier a vraiment été modifié avant d'accepter « c'est fait » ;
- nouvelle tentative automatique après une erreur passagère du serveur (utile en cloud) ;
- en mode plan, rappel de conclure après quelques étapes d'exploration.

---

## 12. Configuration

Ordre d'application : valeurs par défaut → `~/.config/morpheus/config.json` → variables
d'environnement. L'interface web (Paramètres) écrit dans `config.json`.

| Clé | Défaut | Rôle |
|---|---|---|
| `serveur` | `"ollama"` | `"ollama"` ou `"llamacpp"` |
| `url_ollama` | `http://127.0.0.1:11434` | Adresse d'Ollama |
| `url_llamacpp` | `http://127.0.0.1:8080` | Adresse de llama-server |
| `modele` | `"qwen3-coder-next"` | Modèle (ou `claude-code`, `claude-code:opus`…) |
| `num_ctx` | `65536` | Taille du contexte |
| `temperature`, `top_p`, `top_k`, `repeat_penalty` | vides | Échantillonnage (vide = réglages du modèle) |
| `max_etapes` | `50` | Appels d'outils au plus par demande |
| `keep_alive` | `"30m"` | Durée pendant laquelle Ollama garde le modèle chargé |
| `url_searxng` | `""` | SearXNG (ex. `http://127.0.0.1:8888`) pour la recherche web |
| `mode` | `"chat"` | Mode au lancement : `"chat"` ou `"dev"` |
| `style` | `"defaut"` | Mode de conversation (mémorisé automatiquement) |
| `commande_claude` | `"claude"` | Programme Claude Code |
| `url_telegram` | `https://api.telegram.org` | API Telegram |
| `url_registre_ollama` | `https://registry.ollama.ai` | Bibliothèque d'Ollama (taille d'un modèle à télécharger) |

Variables d'environnement : `MORPHEUS_SERVEUR`, `MORPHEUS_MODELE`, `MORPHEUS_NUM_CTX`,
`MORPHEUS_URL_OLLAMA`, `MORPHEUS_URL_LLAMACPP`, `MORPHEUS_MODE`, `MORPHEUS_CLAUDE`,
`MORPHEUS_URL_TELEGRAM`, `MORPHEUS_URL_REGISTRE_OLLAMA`.

Exemple :

```json
{
  "modele": "kimi-k2.7-code:cloud",
  "url_searxng": "http://127.0.0.1:8888",
  "mode": "chat"
}
```

`/config` (terminal) affiche la configuration réellement utilisée.

---

## 13. Fichiers et dossiers utilisés

| Chemin | Contenu |
|---|---|
| `morpheus.py` (où tu l'as installé) | Le programme |
| `morpheus.png` (à côté) | Logo (facultatif) |
| `~/.config/morpheus/config.json` | Configuration |
| `~/.config/morpheus/MORPHEUS.md` | Tes consignes personnelles |
| `~/.config/morpheus/modes.json` | Tes modes de conversation |
| `~/.config/morpheus/jeton_web` | Jeton administrateur du web (mode 600) |
| `~/.config/morpheus/utilisateurs.json` | Invités et leurs jetons (mode 600) |
| `~/.config/morpheus/telegram.json` | Réglages Telegram (mode 600) |
| `~/.config/systemd/user/morpheus.service` | Service de l'interface web |
| `~/.local/share/morpheus/sessions/` | Journaux des conversations |
| `~/.local/share/morpheus/discussions/` | Dossier des discussions sans projet |
| `~/.local/share/morpheus/historique_saisie` | Historique des saisies du terminal |
| `~/projets/` | Tes projets (liste du web) |
| `~/projets-partages/<nom>/` | Espace de chaque invité |
| `MORPHEUS.md` (dans un projet) | Consignes du projet |

---

## 14. Dépannage

| Problème | Solution |
|---|---|
| « Erreur du serveur de modèle » | `systemctl status ollama`, puis `ollama list` pour vérifier le nom du modèle ; pour un modèle cloud : `ollama signin` |
| Une nouveauté n'apparaît pas dans le web | `systemctl --user restart morpheus`, puis recharger la page |
| Le choix d'un modèle revient à l'ancien | Le serveur ne connaît pas ce modèle (nom mal écrit, ou service pas redémarré) : un message s'affiche en bas de la page. Un modèle simplement pas installé est proposé au téléchargement |
| « Claude Code introuvable » | Installer Claude Code, ou régler `commande_claude` ; vérifier que `claude` se lance dans un terminal |
| « Erreur de Claude Code » (connexion) | Lancer `claude` une fois dans un terminal pour se connecter |
| Le modèle tourne en rond | « Arrêter » ou Ctrl+C, puis reformuler plus précisément ; `/reset` pour repartir de zéro |
| Réponses lentes ou contexte plein | `/compacter`, ou `/reset` |
| Recherche web médiocre | Installer SearXNG et renseigner `url_searxng` |
| Lien web refusé | Jeton changé : reprendre le lien affiché au lancement (ou `journalctl --user -u morpheus`) |
| Comportement bizarre du modèle | Regarder le champ `brut` du dernier journal dans `~/.local/share/morpheus/sessions/` |

---

## 15. Pour les développeurs

### Règles du projet

Détaillées dans `CLAUDE.md` : un seul fichier, bibliothèque standard uniquement, textes et
commentaires en français, compenser les faiblesses du modèle **dans le code**, ne jamais affaiblir
les règles de sécurité, un test par fonctionnalité, un commit par modification validée.

### Organisation de `morpheus.py`

1. Configuration (`CONFIG`, `charger_config()`).
2. Affichage (couleurs, diff, `AfficheurFlux`).
3. Chemins et permissions (`Permissions`, commandes interdites et en lecture seule, mode auto et son
   juge `juger_commande()`, instantanés pour `/annuler`).
4. Outils (`OUTILS`, `FONCTIONS`, `executer_outil()`).
5. Communication avec le modèle (`appeler_modele()`, `extraire_appels_texte()`).
6. Conversation (prompt système, modes de conversation, journal, `traiter_demande()`), puis
   Claude Code (`traiter_demande_claude()`, `decision_claude()`).
7. Interface web (`SessionWeb`, `ServeurWeb`, `ConsoleWeb`, `GestionnaireWeb`, `PAGE_WEB`).
8. Telegram (`BotTelegram`, `configurer_telegram()`).
9. `main()` : arguments et commandes du terminal.

### Tests

```bash
bash tests/lance_tests.sh
```

Chaque `tests/testNN.py` lance `morpheus.py` dans un dossier temporaire face à un **faux serveur de
modèle** (`tests/faux.py`, réponses scriptées) : aucun vrai modèle n'est appelé. Claude Code est
remplacé par `tests/faux_claude.py`, Telegram par un faux serveur local. Pour une nouvelle
fonctionnalité, ajoute un test sur le modèle des existants.

---

## Licence

Morpheus AI Agent est distribué sous licence **MIT** (fichier `LICENSE`) : tu peux l'utiliser, le
modifier et le redistribuer librement, y compris dans un projet commercial, en gardant la mention de
copyright. Il est fourni **sans aucune garantie** : il exécute des commandes et modifie des fichiers
avec les droits de ton compte, relis ce qu'il propose avant de valider.
