import os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
import subprocess, sys, os
sys.path.insert(0, BASE); import faux
faux.lancer(18434)
T = lambda n, a: {"function": {"name": n, "arguments": a}}
env = dict(os.environ, HOME=HOME_TEST)

# Reproduit un bug observé avec qwen3-coder-next : le modèle appelle web_fetch
# en nommant l'URL "path" (la convention des autres outils) au lieu de "url",
# avec en plus des paramètres inventés (start_line, end_line copiés d'un autre
# outil). Le rattrapage « un paramètre manquant + un paramètre inconnu » ne se
# déclenchait pas ici car il y avait 3 paramètres inconnus, pas 1.
faux.SCRIPT += [
    faux.ol("", [T("web_fetch", {"path": "http://127.0.0.1:18434/page",
                                  "start_line": "1", "end_line": "50"})]),
    faux.ol("Voilà le contenu."),
]
entree = "récupère le contenu de http://127.0.0.1:18434/page\n/quitter\n"
p = subprocess.run([sys.executable, MORPHEUS], input=entree, capture_output=True, text=True,
                    timeout=60, cwd=PROJ, env=env)
print(p.stdout)
print(p.stderr[-2000:])

assert "paramètre(s) manquant(s)" not in p.stdout, "path doit être compris comme url pour web_fetch"
assert "Contenu web" in p.stdout, "le contenu doit avoir été récupéré du premier coup"
print("OK : web_fetch(path=...) toléré comme alias de url")
