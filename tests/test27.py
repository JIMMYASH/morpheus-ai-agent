import os, sys, glob, json, subprocess
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
sys.path.insert(0, BASE); import faux
faux.lancer(18434)
T = lambda n, a: {"function": {"name": n, "arguments": a}}
env = dict(os.environ, HOME=HOME_TEST)

# Le modèle oublie parfois complètement le paramètre path (edit_file avec seulement
# old_string/new_string), ou passe un motif (*.txt) à read_file. MORPHEUS doit :
#  - deviner path quand un seul fichier a servi pendant la demande ;
#  - sinon, lister les fichiers candidats dans l'erreur ;
#  - pour un motif, donner les fichiers correspondants.
with open(os.path.join(PROJ, "notes.txt"), "w", encoding="utf-8") as f:
    f.write("ancienne ligne\n")
with open(os.path.join(PROJ, "autre.txt"), "w", encoding="utf-8") as f:
    f.write("autre contenu\n")

faux.SCRIPT += [
    faux.ol("", [T("read_file", {"path": "notes.txt"})]),
    faux.ol("", [T("edit_file", {"old_string": "ancienne", "new_string": "nouvelle"})]),   # path deviné
    faux.ol("", [T("read_file", {"pattern": "*.txt"})]),                                  # motif
    faux.ol("", [T("read_file", {"path": "autre.txt"})]),
    faux.ol("", [T("edit_file", {"old_string": "autre", "new_string": "x"})]),            # ambigu
    faux.ol("Terminé."),
]
entree = "modifie notes.txt\no\n/quitter\n"
p = subprocess.run([sys.executable, MORPHEUS], input=entree, capture_output=True, text=True,
                   timeout=60, cwd=PROJ, env=env)
print(p.stdout)
print(p.stderr[-2000:])

assert "aucun fichier n'a été modifié" not in p.stdout, "la modification par path deviné doit compter comme une modification"
contenu = open(os.path.join(PROJ, "notes.txt"), encoding="utf-8").read()
assert contenu == "nouvelle ligne\n", f"edit_file sans path aurait dû modifier notes.txt : {contenu!r}"
assert open(os.path.join(PROJ, "autre.txt"), encoding="utf-8").read() == "autre contenu\n", \
    "avec deux fichiers candidats, MORPHEUS ne doit pas deviner"

fichiers = sorted(glob.glob(os.path.join(HOME_TEST, ".local/share/morpheus/sessions/*.jsonl")))
lignes = [json.loads(l) for l in open(fichiers[-1], encoding="utf-8") if l.strip()]
resultats = [m["content"] for m in lignes if m.get("role") == "tool"]
for r in resultats:
    print("---", r[:200])
assert "path manquant : j'ai utilisé notes.txt" in resultats[1] and resultats[1].startswith("Fichier modifié"), \
    "le modèle doit être prévenu du path deviné, sans masquer le résultat"
assert "est un motif" in resultats[2] and "notes.txt" in resultats[2] and "autre.txt" in resultats[2], \
    "read_file sur un motif doit lister les fichiers correspondants"
assert "Fichiers utilisés pendant cette demande : notes.txt, autre.txt" in resultats[4], \
    "avec plusieurs candidats, l'erreur doit les lister"
print("OK : path deviné si un seul fichier, candidats listés sinon, motif redirigé vers glob")
