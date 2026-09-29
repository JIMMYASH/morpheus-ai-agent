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

# Erreur JSON fréquente chez les modèles faibles : une virgule finale avant ]
# ou }, ex. [{"content":"...","status":"pending"},]. Invalide en JSON strict
# (contrairement à Python), json.loads levait une JSONDecodeError et l'appel
# todo_write était rejeté au lieu d'être exécuté.
todos_virgule_finale = '[{"content":"Préparer le déploiement","status":"completed"},]'

faux.SCRIPT += [
    faux.ol("", [T("todo_write", {"todos": todos_virgule_finale})]),
    faux.ol("C'est fait."),
]
entree = "prépare la liste des tâches pour le déploiement\n/quitter\n"
p = subprocess.run([sys.executable, MORPHEUS], input=entree, capture_output=True, text=True,
                    timeout=60, cwd=PROJ, env=env)
print(p.stdout)
print(p.stderr[-2000:])

assert "Erreur : valeur invalide" not in p.stdout, "une virgule finale avant ] doit être tolérée, pas rejetée"
assert "Préparer le déploiement" in p.stdout, "la tâche doit s'afficher correctement"
print("OK : virgule finale avant ] tolérée par todo_write")
