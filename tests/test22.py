import os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
import subprocess, sys, os
sys.path.insert(0, BASE); import faux
faux.lancer(18434)
env = dict(os.environ, HOME=HOME_TEST)

# Repéré avec un modèle cloud : un message de commit rédigé en anglais (la
# consigne « uniquement en français » ne mentionnait pas explicitement les
# messages de commit), et un `git add .` qui embarque __pycache__ sans
# .gitignore. Corrigé au niveau du prompt système (pas un problème de format
# d'appel d'outil, donc pas réparable côté code comme les bugs JSON).
# Ce test vérifie juste que les deux consignes sont bien présentes dans le
# prompt système effectivement envoyé au modèle.
faux.SCRIPT += [faux.ol("Bonjour.")]
entree = "bonjour\n/quitter\n"
p = subprocess.run([sys.executable, MORPHEUS], input=entree, capture_output=True, text=True,
                    timeout=60, cwd=PROJ, env=env)
print(p.stdout)
print(p.stderr[-2000:])

sysmsg = faux.RECUS[0][1]["messages"][0]["content"]
assert "messages de commit" in sysmsg, "la consigne français doit couvrir explicitement les messages de commit"
assert "__pycache__" in sysmsg and ".gitignore" in sysmsg, \
    "la consigne .gitignore/__pycache__ avant un commit doit être présente dans le prompt système"
print("OK : consignes commit-en-français et .gitignore/__pycache__ présentes dans le prompt système")
