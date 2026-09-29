import os, sys, glob, json
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
import subprocess, sys, os
sys.path.insert(0, BASE); import faux
faux.lancer(18434)
env = dict(os.environ, HOME=HOME_TEST)

# Repéré en testant un modèle cloud (Ollama Cloud) : une erreur serveur 5xx
# transitoire interrompait toute la demande en cours, alors qu'un simple
# nouvel essai réussissait la plupart du temps. appeler_modele_avec_retry()
# retente maintenant une fois avant de remonter l'erreur à l'utilisateur.

# Partie 1 : une seule erreur transitoire, puis succès -> ne doit PAS être
# montrée comme une erreur fatale à l'utilisateur.
faux.SCRIPT += [
    faux.erreur(500, "Internal Server Error"),
    faux.ol("Bonjour, tout va bien."),
]
# Partie 2 : deux erreurs de suite (au-delà du nombre de tentatives) -> doit
# être clairement signalée à l'utilisateur, comme avant ce correctif.
faux.SCRIPT += [
    faux.erreur(500, "Internal Server Error"),
    faux.erreur(500, "Internal Server Error"),
]

entree = "bonjour\nbonjour encore\n/quitter\n"
p = subprocess.run([sys.executable, MORPHEUS], input=entree, capture_output=True, text=True,
                    timeout=60, cwd=PROJ, env=env)
print(p.stdout)
print(p.stderr[-2000:])

assert "erreur serveur transitoire" in p.stdout, "la première erreur doit déclencher une nouvelle tentative silencieuse"
assert "Bonjour, tout va bien." in p.stdout, "la deuxième tentative doit réussir et produire la réponse"
assert p.stdout.count("Erreur du serveur de modèle") == 1, \
    "la première partie ne doit pas remonter d'erreur fatale ; la deuxième (2 échecs) doit en remonter une seule"

# Chaque erreur serveur (absorbée ou définitive) doit être notée dans le
# journal, pour qu'un script de bilan puisse les compter après coup.
fichiers = sorted(glob.glob(os.path.join(HOME_TEST, ".local/share/morpheus/sessions/*.jsonl")))
assert fichiers, "un journal de session doit avoir été écrit"
lignes = [json.loads(l) for l in open(fichiers[-1], encoding="utf-8") if l.strip()]
erreurs = [l for l in lignes if l.get("type") == "erreur_serveur"]
print("erreurs journalisées :", erreurs)
assert len(erreurs) == 3, "les 3 erreurs serveur (1 absorbée + 2 de la partie définitive) doivent être journalisées"
assert [e["definitive"] for e in erreurs] == [False, False, True], \
    "seule la toute dernière erreur (après épuisement des tentatives) doit être marquée définitive"

print("OK : une erreur serveur transitoire est absorbée par une nouvelle tentative, deux échecs de suite sont bien signalés, et chaque erreur est journalisée")
