import os, sys, glob, json
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
import subprocess, sys, os
sys.path.insert(0, BASE); import faux
faux.lancer(18434)
T = lambda n, a: {"function": {"name": n, "arguments": a}}
env = dict(os.environ, HOME=HOME_TEST)

# Reproduit un bug observé en mode /plan avec qwen3-coder-next : bloqué en
# lecture seule, le modèle peut explorer indéfiniment (read_file, list_dir,
# glob, grep...) sans jamais conclure par un plan en texte, jusqu'à épuiser
# la limite de 50 étapes. En mode normal il existe un rappel après quelques
# explorations sans modification (exige_modif) ; il était désactivé en mode
# plan. On vérifie ici qu'une note de recentrage est injectée après quelques
# étapes d'exploration sans conclusion, et que le modèle finit par conclure
# avant d'atteindre la limite.
with open(os.path.join(PROJ, "fichier.txt"), "w") as f:
    f.write("contenu\n")

faux.SCRIPT += [
    faux.ol("", [T("read_file", {"path": "fichier.txt"})]),
    faux.ol("", [T("list_dir", {"path": "."})]),
    faux.ol("", [T("glob", {"pattern": "*.txt"})]),
    faux.ol("", [T("grep", {"pattern": "contenu"})]),
    faux.ol("Plan : ajouter une fonction traiter() dans fichier.txt."),
]
entree = "/plan\najoute une fonction traiter() dans fichier.txt\n/quitter\n"
p = subprocess.run([sys.executable, MORPHEUS], input=entree, capture_output=True, text=True,
                    timeout=60, cwd=PROJ, env=env)
print(p.stdout)
print(p.stderr[-2000:])

assert "Limite de 50 étapes" not in p.stdout, "la note de recentrage doit permettre de conclure avant la limite"
assert "Plan : ajouter une fonction traiter()" in p.stdout, "le modèle doit avoir pu conclure par le plan"

fichiers = sorted(glob.glob(os.path.join(HOME_TEST, ".local/share/morpheus/sessions/*.jsonl")))
assert fichiers, "un journal de session doit avoir été écrit"
lignes = [json.loads(l) for l in open(fichiers[-1], encoding="utf-8") if l.strip()]
notes = [m for m in lignes if m.get("role") == "user" and "mode plan" in m.get("content", "")]
assert notes, "une note de recentrage « mode plan » doit avoir été injectée dans la conversation"
print("OK : note de recentrage injectée en mode plan après plusieurs étapes sans conclusion")
