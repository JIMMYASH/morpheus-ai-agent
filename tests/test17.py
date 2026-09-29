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

# Reproduit un bug observé avec qwen3-coder-next : le modèle écrit parfois les
# paramètres entiers (offset, limit) en notation flottante, ex. "42.0" au lieu
# de "42". int("42.0") lève une ValueError en Python, donc read_file échouait
# avec « Erreur : valeur invalide pour offset », forçant le modèle à contourner
# read_file avec bash/cat au lieu de l'outil prévu.
with open(os.path.join(PROJ, "fichier.txt"), "w") as f:
    f.write("\n".join(f"L{n:03d}" for n in range(1, 101)) + "\n")

faux.SCRIPT += [
    faux.ol("", [T("read_file", {"path": "fichier.txt", "offset": "42.0", "limit": "10.0"})]),
    faux.ol("Voilà les lignes demandées."),
]
entree = "montre-moi les lignes 42 à 51 de fichier.txt\n/quitter\n"
p = subprocess.run([sys.executable, MORPHEUS], input=entree, capture_output=True, text=True,
                    timeout=60, cwd=PROJ, env=env)
print(p.stdout)
print(p.stderr[-2000:])

assert "Erreur : valeur invalide" not in p.stdout, "un offset/limit écrit en notation flottante doit être toléré"
assert "L042" in p.stdout, "la ligne 42 doit apparaître : offset='42.0' doit être compris comme 42"
assert "11 lignes au total" in p.stdout, "10 lignes de contenu + la note finale : limit='10.0' doit être compris comme 10"
print("OK : offset/limit en notation flottante tolérés par read_file")
