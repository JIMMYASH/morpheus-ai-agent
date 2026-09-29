import os, sys, subprocess
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
sys.path.insert(0, BASE); import faux
faux.lancer(18434)
T = lambda n, a: {"function": {"name": n, "arguments": a}}
env = dict(os.environ, HOME=HOME_TEST)
env.pop("MORPHEUS_MODE", None)          # mode par défaut : Chat


def outils_recus(i):
    return {o["function"]["name"] for o in faux.RECUS[i][1].get("tools") or []}


# Mode Chat (par défaut) : pas d'outil d'écriture proposé, écriture et bash qui écrit refusés,
# lecture et bash en lecture seule permis.
faux.SCRIPT += [faux.ol("", [T("write_file", {"path": "a.txt", "content": "a"})]),
                faux.ol("", [T("bash", {"command": "touch b.txt"})]),
                faux.ol("", [T("bash", {"command": "ls"})]),
                faux.ol("Je ne peux rien créer en mode Chat : passe en mode développeur.")]
p = subprocess.run([sys.executable, MORPHEUS], input="crée a.txt\n/plan\n/quitter\n",
                   capture_output=True, text=True, timeout=60, cwd=PROJ, env=env)
print(p.stdout[-2500:], p.stderr[-800:])
assert "Mode Chat" in p.stdout, "le mode doit être annoncé au lancement"
assert "aucun fichier ne sera modifié" not in p.stdout, "plus de rappel répété à chaque demande en mode Chat"
assert "passe d'abord en mode développeur" in p.stdout, "/plan n'existe qu'en mode développeur"
assert not os.path.exists(os.path.join(PROJ, "a.txt")) and not os.path.exists(os.path.join(PROJ, "b.txt"))
outils = outils_recus(0)
assert "write_file" not in outils and "edit_file" not in outils and "web_search" in outils and "bash" in outils, outils
premier = faux.RECUS[0][1]["messages"][1]["content"]
assert "[Mode Chat" in premier, "le modèle doit savoir qu'il est en mode Chat"
resultats = [m["content"] for m in faux.RECUS[-1][1]["messages"] if m["role"] == "tool"]
assert "mode Chat" in resultats[0] and "mode Chat" in resultats[1], resultats
assert "Refusé" not in resultats[2], "ls est en lecture seule : permis en mode Chat"

# /dev : l'écriture redevient possible (avec validation) ; /mode rebascule en Chat
n = len(faux.RECUS)
faux.SCRIPT += [faux.ol("", [T("write_file", {"path": "a.txt", "content": "a"})]), faux.ol("a.txt créé."),
                faux.ol("Réponse en mode Chat.")]
p = subprocess.run([sys.executable, MORPHEUS], input="/dev\ncrée a.txt\no\n/mode\nbonjour ?\n/quitter\n",
                   capture_output=True, text=True, timeout=60, cwd=PROJ, env=env)
print(p.stdout[-2500:], p.stderr[-800:])
assert "Mode développeur : MORPHEUS peut créer" in p.stdout
assert open(os.path.join(PROJ, "a.txt")).read() == "a", "en mode développeur, l'écriture validée a lieu"
assert "write_file" in outils_recus(n)
assert "write_file" not in outils_recus(-1), "après /mode, retour au mode Chat"
dernier = [m["content"] for m in faux.RECUS[-1][1]["messages"] if m["role"] == "user"][-1]
assert "[Mode Chat" in dernier, dernier

# Mode choisi dans la configuration
env_dev = dict(env, MORPHEUS_MODE="développeur")
faux.SCRIPT += [faux.ol("Ok.")]
p = subprocess.run([sys.executable, MORPHEUS], input="salut\n/quitter\n",
                   capture_output=True, text=True, timeout=60, cwd=PROJ, env=env_dev)
assert "Mode développeur" in p.stdout and "write_file" in outils_recus(-1), p.stdout
print("OK : mode Chat par défaut, bascule /dev, /chat, /mode")
