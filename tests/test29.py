import os, sys, glob, json, subprocess
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
sys.path.insert(0, BASE); import faux
faux.lancer(18434)
T = lambda n, a: {"function": {"name": n, "arguments": a}}
env = dict(os.environ, HOME=HOME_TEST)

# Au délai dépassé, seul bash était tué : les programmes qu'il avait lancés (un serveur
# lancé par npm, par exemple) continuaient de tourner en arrière-plan. Et un serveur
# bloquait MORPHEUS jusqu'au délai maximal, avec un message peu utile.
faux.SCRIPT += [
    faux.ol("", [T("bash", {"command": "sleep 3141 | cat", "timeout": 2})]),
    faux.ol("", [T("bash", {"command": "python3 -m http.server 18997", "timeout": 3})]),
    faux.ol("Le serveur démarre correctement : lance « python3 -m http.server 18997 ».", None),
]
entree = "teste le serveur\no\no\n/quitter\n"
p = subprocess.run([sys.executable, MORPHEUS], input=entree, capture_output=True, text=True,
                   timeout=60, cwd=PROJ, env=env)
print(p.stdout)
print(p.stderr[-2000:])

# Motifs ancrés (^…$) : ne viser que ces programmes, pas une ligne de commande qui contiendrait ce texte.
MOTIF = "^(sleep 3141|python3 -m http.server 18997)$"
restants = subprocess.run(["pgrep", "-f", MOTIF], capture_output=True, text=True).stdout
subprocess.run(["pkill", "-f", MOTIF])
assert not restants.strip(), f"des programmes tournent encore après l'arrêt : {restants}"

fichiers = sorted(glob.glob(os.path.join(HOME_TEST, ".local/share/morpheus/sessions/*.jsonl")))
lignes = [json.loads(l) for l in open(fichiers[-1], encoding="utf-8") if l.strip()]
resultats = [m["content"] for m in lignes if m.get("role") == "tool"]
for r in resultats:
    print("---", r)
assert "Délai dépassé après 2 s" in resultats[0]
assert "Serveur lancé 3 s" in resultats[1] and "donne la commande à l'utilisateur" in resultats[1], \
    "un serveur doit être arrêté avec un message qui explique quoi faire"
print("OK : délai dépassé -> tous les programmes arrêtés ; serveur -> arrêté avec un message clair")
