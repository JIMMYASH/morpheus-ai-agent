import os, sys, glob, json, subprocess
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
sys.path.insert(0, BASE); import faux
faux.lancer(18434)
env = dict(os.environ, HOME=HOME_TEST)

# Session réelle : « Aide-moi à écrire un message… » ; le modèle demande des précisions, mais le mot
# « écrire » faisait croire à une demande de modification de fichier : MORPHEUS le relançait deux fois
# (« Vérification : aucun fichier n'a été modifié… ») et le modèle se justifiait en boucle.


def verifications(cwd, demande, reponse):
    faux.SCRIPT.append(faux.ol(reponse))
    n0 = len(faux.RECUS)
    subprocess.run([sys.executable, MORPHEUS], input=demande + "\n/quitter\n", capture_output=True, text=True,
                   timeout=60, cwd=cwd, env=env)
    assert not faux.SCRIPT, "le modèle a été rappelé alors qu'il ne fallait pas"
    return sum("Vérification de MORPHEUS" in json.dumps(c["messages"], ensure_ascii=False) for _, c in faux.RECUS[n0:])


# 1. Dans un projet : le modèle pose une question pour préciser → pas de relance
assert verifications(PROJ, "ajoute une fonction de tri", "Quel critère de tri veux-tu : par date ou par nom ?") == 0

# 2. Dans le dossier des discussions : jamais de vérification « aucun fichier modifié »
discussions = os.path.join(HOME_TEST, ".local/share/morpheus/discussions")
os.makedirs(discussions)
assert verifications(discussions, "Aide-moi à écrire un message chaleureux pour ma sœur",
                     "Voici une proposition : « Chère sœur, … »") == 0

# 3. Garde-fou conservé : un modèle qui prétend avoir fini sans rien modifier est toujours relancé
faux.SCRIPT += [faux.ol("J'ai ajouté la fonction de tri. Autre chose ?"), faux.ol("Je ne peux pas le faire sans lire le fichier.")]
n0 = len(faux.RECUS)
subprocess.run([sys.executable, MORPHEUS], input="ajoute une fonction de tri\n/quitter\n", capture_output=True,
               text=True, timeout=60, cwd=PROJ, env=env)
assert any("Vérification de MORPHEUS" in json.dumps(c["messages"], ensure_ascii=False) for _, c in faux.RECUS[n0:]), \
    "une fausse annonce (« J'ai ajouté… ») doit toujours être vérifiée"
print("OK : pas de relance pour une question de précision ni en discussion ; fausse annonce toujours vérifiée")
