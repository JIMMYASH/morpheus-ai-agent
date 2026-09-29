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

# Reproduit un bug observé avec qwen3-coder-next : le modèle écrit parfois le
# JSON de todo_write en échappant les apostrophes (\') comme en Python, ce qui
# est invalide en JSON (seul le guillemet double doit être échappé). Avant la
# correction, json.loads levait une JSONDecodeError, remontée comme
# « Erreur : valeur invalide pour todos » au lieu de mettre à jour la liste.
barre = chr(92)  # backslash, construit à part pour ne pas l'échapper au sens Python
todos_invalide = ('[{"content":"Ajouter l' + barre + "'option --json à la commande list"
                   + '","status":"completed"},{"content":"Ajouter un test pour l' + barre
                   + "'option --json" + '","status":"completed"}]')

faux.SCRIPT += [
    faux.ol("", [T("todo_write", {"todos": todos_invalide})]),
    faux.ol("C'est fait."),
]
entree = "prépare la liste des tâches pour la fonctionnalité --json\n/quitter\n"
p = subprocess.run([sys.executable, MORPHEUS], input=entree, capture_output=True, text=True,
                    timeout=60, cwd=PROJ, env=env)
print(p.stdout)
print(p.stderr[-2000:])

assert "Erreur : valeur invalide" not in p.stdout, "le JSON avec apostrophe échappée doit être toléré, pas rejeté"
assert "Ajouter l'option --json à la commande list" in p.stdout, "la tâche doit s'afficher avec l'apostrophe correcte"
assert "☑" in p.stdout, "la tâche marquée complétée doit apparaître dans la liste affichée"
print("OK : JSON avec apostrophe échappée toléré par todo_write")
