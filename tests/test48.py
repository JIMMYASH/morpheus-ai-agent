import os, sys, json, subprocess
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]

# Modèle « claude-code » : MORPHEUS pilote Claude Code (ici un faux programme claude) et répond lui-même
# à ses demandes d'autorisation, avec ses propres règles.
FAUX = os.path.join(BASE, "faux_claude.py")
SCENARIOS = os.path.join(HOME_TEST, "scenarios.json")
JOURNAL = os.path.join(HOME_TEST, "faux_claude.jsonl")
env = dict(os.environ, HOME=HOME_TEST, MORPHEUS_MODELE="claude-code:sonnet", MORPHEUS_CLAUDE=FAUX,
           FAUX_CLAUDE_SCENARIOS=SCENARIOS, FAUX_CLAUDE_JOURNAL=JOURNAL)


def lancer(scenarios, saisie, arguments=(), **autres):
    json.dump(scenarios, open(SCENARIOS, "w", encoding="utf-8"))
    open(JOURNAL, "w").close()
    p = subprocess.run([sys.executable, MORPHEUS, *arguments], input=saisie, capture_output=True, text=True,
                       timeout=60, cwd=PROJ, env=dict(env, **autres))
    print(p.stdout[-3000:], p.stderr[-1500:])
    lignes = [json.loads(l) for l in open(JOURNAL, encoding="utf-8")]
    return p, lignes


def decisions(lignes):
    return [l["decision"] for l in lignes if "decision" in l]


def arguments(lignes, rang=0):
    return [l["arguments"] for l in lignes if "arguments" in l][rang]


# Mode développeur : aperçu + validation pour Write, commandes interdites refusées sans question,
# écriture par bash refusée, refus avec consigne transmis, /annuler, reprise de la conversation.
a = os.path.join(PROJ, "a.txt")
p, lignes = lancer([[
    {"outil": "Write", "input": {"file_path": a, "content": "bonjour\n"}},
    {"outil": "Bash", "input": {"command": "sudo ls"}},
    {"outil": "Bash", "input": {"command": "cat > c.txt <<EOF\nx\nEOF"}},
    {"outil": "Bash", "input": {"command": "touch b.txt"}},
    {"outil": "Bash", "input": {"command": "ls"}},
    {"texte": "Fichier a.txt créé."}],
    [{"texte": "Deuxième réponse."}]],
    "crée a.txt\no\nn\npas de touch\n/annuler\nsuite\n/quitter\n")
args = arguments(lignes)
assert "--permission-prompt-tool" in args and args[args.index("--permission-prompt-tool") + 1] == "stdio"
assert args[args.index("--permission-mode") + 1] == "default"
assert args[args.index("--model") + 1] == "sonnet"
assert args[args.index("--setting-sources") + 1] == "", "les règles « allow » des réglages de Claude Code sont ignorées"
assert "Write" in args[args.index("--tools") + 1] and "Task," not in args[args.index("--tools") + 1] + ","
assert "--resume" not in args
assert "+bonjour" in p.stdout, "aperçu de la modification"
d = decisions(lignes)
assert d[0]["behavior"] == "allow", d
assert d[1]["behavior"] == "deny" and "administrateur" in d[1]["message"], "sudo refusé"
assert d[2]["behavior"] == "deny" and "Write ou Edit" in d[2]["message"], "écriture par heredoc refusée"
assert d[3]["behavior"] == "deny" and "pas de touch" in d[3]["message"] and not d[3].get("interrupt"), d[3]
assert d[4]["behavior"] == "allow", "ls est en lecture seule"
assert p.stdout.count("Exécuter cette commande ?") == 1, "sudo, heredoc et ls ne demandent rien"
assert not os.path.exists(os.path.join(PROJ, "b.txt")) and not os.path.exists(os.path.join(PROJ, "c.txt"))
assert "Fichier a.txt créé." in p.stdout
assert "supprimé (il n'existait pas avant)" in p.stdout and not os.path.exists(a), "/annuler efface a.txt"
args2 = arguments(lignes, 1)
assert args2[args2.index("--resume") + 1] == "session-faux-1", "la conversation continue dans la même session"
demandes = [l["demande"] for l in lignes if "demande" in l]
assert demandes[1].endswith("suite") and "annulé" in demandes[1], "la note /annuler est transmise"

# Reprise avec -c : la session de Claude Code est retrouvée dans le journal
p, lignes = lancer([[{"texte": "Repris."}]], "encore\n/quitter\n", ["-c"])
args = arguments(lignes)
assert args[args.index("--resume") + 1] == "session-faux-1", args
assert "Repris." in p.stdout

# Refus sans consigne : Claude Code est interrompu
p, lignes = lancer([[{"outil": "Write", "input": {"file_path": a, "content": "x"}}, {"texte": "jamais affiché"}]],
                   "crée a.txt\nn\n\n/quitter\n")
d = decisions(lignes)
assert d[0]["behavior"] == "deny" and d[0].get("interrupt"), d
assert "Tâche arrêtée" in p.stdout and not os.path.exists(a)

# Mode Chat : pas d'outil d'écriture proposé, écriture et commande qui écrit refusées sans question
p, lignes = lancer([[{"outil": "Write", "input": {"file_path": a, "content": "x"}},
                     {"outil": "Bash", "input": {"command": "touch b.txt"}}, {"texte": "Passe en mode dev."}]],
                   "crée a.txt\n/quitter\n", MORPHEUS_MODE="chat")
assert "Write" not in arguments(lignes)[arguments(lignes).index("--tools") + 1]
d = decisions(lignes)
assert all(x["behavior"] == "deny" and "mode Chat" in x["message"] for x in d), d
assert "Appliquer" not in p.stdout and "Exécuter" not in p.stdout
assert not os.path.exists(a) and not os.path.exists(os.path.join(PROJ, "b.txt"))

# Mode plan : Claude Code lancé en mode plan
p, lignes = lancer([[{"texte": "Plan."}]], "/plan\nprépare\n/quitter\n")
args = arguments(lignes)
assert args[args.index("--permission-mode") + 1] == "plan"

# Mode -p : toute action à valider est refusée automatiquement
p, lignes = lancer([[{"outil": "Write", "input": {"file_path": a, "content": "x"}}, {"texte": "Fini."}]],
                   "", ["-p", "crée a.txt"])
d = decisions(lignes)
assert d[0]["behavior"] == "deny" and "automatique" in d[0]["message"] and not d[0].get("interrupt"), d
assert not os.path.exists(a) and "Fini." in p.stdout

# Lecture hors du projet : autorisation demandée
p, lignes = lancer([[{"outil": "Read", "input": {"file_path": "/etc/hostname"}}, {"texte": "Lu."}]],
                   "lis /etc/hostname\nn\nnon\n/quitter\n")
assert "Lecture EN DEHORS du projet" in p.stdout and decisions(lignes)[0]["behavior"] == "deny"

# Claude Code absent : message clair, pas de plantage
p = subprocess.run([sys.executable, MORPHEUS], input="bonjour\n/quitter\n", capture_output=True, text=True,
                   timeout=60, cwd=PROJ, env=dict(env, MORPHEUS_CLAUDE="/inexistant/claude"))
print(p.stdout[-800:])
assert "Claude Code introuvable" in p.stdout
print("OK")
