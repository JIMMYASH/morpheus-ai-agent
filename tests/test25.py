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

# Bug observé dans les journaux : après une modification, relire le même fichier
# avec les mêmes paramètres était bloqué (« Appel identique déjà effectué »), alors
# que son contenu avait changé (replace_lines demande même explicitement de relire).
# Le modèle continuait alors avec des numéros de ligne périmés.
with open(os.path.join(PROJ, "notes.txt"), "w", encoding="utf-8") as f:
    f.write("ancienne ligne\n")

faux.SCRIPT += [
    faux.ol("", [T("read_file", {"path": "notes.txt"})]),                      # lecture 1
    faux.ol("", [T("read_file", {"path": "notes.txt"})]),                      # relecture sans modif -> bloquée
    faux.ol("", [T("edit_file", {"path": "notes.txt", "old_string": "ancienne",
                                 "new_string": "nouvelle"})]),                 # modification
    faux.ol("", [T("read_file", {"path": "notes.txt"})]),                      # relecture après modif -> exécutée
    faux.ol("Terminé."),
]
entree = "modifie notes.txt\no\n/quitter\n"
p = subprocess.run([sys.executable, MORPHEUS], input=entree, capture_output=True, text=True,
                   timeout=60, cwd=PROJ, env=env)
print(p.stdout)
print(p.stderr[-2000:])

fichiers = sorted(glob.glob(os.path.join(HOME_TEST, ".local/share/morpheus/sessions/*.jsonl")))
assert fichiers, "un journal de session doit avoir été écrit"
lignes = [json.loads(l) for l in open(fichiers[-1], encoding="utf-8") if l.strip()]
resultats = [m["content"] for m in lignes if m.get("role") == "tool" and m.get("name") == "read_file"]
print(resultats)
assert len(resultats) == 3, "trois lectures attendues dans le journal"
assert "ancienne ligne" in resultats[0], "la première lecture doit montrer l'ancien contenu"
assert "Appel identique" in resultats[1], "une relecture sans modification doit rester bloquée"
assert "nouvelle ligne" in resultats[2], "la relecture après modification doit être exécutée et montrer le nouveau contenu"
print("OK : un fichier peut être relu après avoir été modifié")
