import os, sys, glob, json, subprocess
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
sys.path.insert(0, BASE); import faux
faux.lancer(18434)
T = lambda n, a: {"function": {"name": n, "arguments": a}}
env = dict(os.environ, HOME=HOME_TEST)

# Le modèle recopie parfois dans old_string (et new_string) les numéros de ligne
# affichés par read_file ("     2\t    return 1") : old_string était alors introuvable.
with open(os.path.join(PROJ, "calcul.py"), "w", encoding="utf-8") as f:
    f.write("def f():\n    return 1\n")

faux.SCRIPT += [
    faux.ol("", [T("read_file", {"path": "calcul.py"})]),
    faux.ol("", [T("edit_file", {"path": "calcul.py",
                                 "old_string": "     1\tdef f():\n     2\t    return 1",
                                 "new_string": "     1\tdef f():\n     2\t    return 2"})]),
    faux.ol("Terminé : f renvoie maintenant 2."),
]
entree = "modifie f pour qu'elle renvoie 2\no\n/quitter\n"
p = subprocess.run([sys.executable, MORPHEUS], input=entree, capture_output=True, text=True,
                   timeout=60, cwd=PROJ, env=env)
print(p.stdout)
print(p.stderr[-2000:])

contenu = open(os.path.join(PROJ, "calcul.py"), encoding="utf-8").read()
assert contenu == "def f():\n    return 2\n", f"contenu inattendu : {contenu!r}"

fichiers = sorted(glob.glob(os.path.join(HOME_TEST, ".local/share/morpheus/sessions/*.jsonl")))
lignes = [json.loads(l) for l in open(fichiers[-1], encoding="utf-8") if l.strip()]
resultats = [m["content"] for m in lignes if m.get("role") == "tool"]
assert resultats[1].startswith("Fichier modifié") and "numéros de ligne retirés" in resultats[1], resultats[1]
print("OK : les numéros de ligne recopiés dans old_string/new_string sont retirés")
