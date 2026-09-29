import os, sys, json, time, subprocess
from urllib.request import Request, urlopen
from urllib.error import HTTPError
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
sys.path.insert(0, BASE); import faux
faux.lancer(18434)
env = dict(os.environ, HOME=HOME_TEST, XDG_DATA_HOME=os.path.join(HOME_TEST, ".local/share"))
SESSIONS = os.path.join(HOME_TEST, ".local/share/morpheus/sessions")
DISCUSSIONS = os.path.realpath(os.path.join(HOME_TEST, ".local/share/morpheus/discussions"))

# « Discussions » : conversations libres, sans projet. « Autres dossiers » : dossiers hors de
# ~/projets qui ont des conversations (jamais le dossier personnel).

# Anciennes sessions du terminal : une dans un dossier hors de ~/projets, une dans le dossier personnel.
ailleurs = os.path.realpath(os.path.join(HOME_TEST, "ailleurs"))
os.makedirs(ailleurs)
os.makedirs(SESSIONS)
RACINE_PROJETS = os.path.join(HOME_TEST, "projets")
os.makedirs(RACINE_PROJETS)
for nom, racine in (("20260101-100000-000001", ailleurs), ("20260101-100000-000002", os.path.realpath(HOME_TEST)),
                    ("20260101-100000-000003", os.path.realpath(RACINE_PROJETS))):
    with open(os.path.join(SESSIONS, nom + ".jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "entete", "racine": racine, "modele": "x"}) + "\n")
        f.write(json.dumps({"role": "user", "content": "vieille question"}) + "\n")
        f.write(json.dumps({"role": "assistant", "content": "vieille réponse"}) + "\n")

PORT = 18768
URL = f"http://127.0.0.1:{PORT}"
# Lancé depuis le dossier personnel, sans aucun projet : l'interface ouvre les discussions.
serveur = subprocess.Popen([sys.executable, MORPHEUS, "--web", "--port", str(PORT), "--hote", "127.0.0.1"],
                           cwd=HOME_TEST, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
COOKIE = ""


def appel(chemin, donnees=None):
    entetes = {"Content-Type": "application/json", "X-Morpheus": "1", "Cookie": COOKIE}
    corps = json.dumps(donnees).encode() if donnees is not None else None
    try:
        with urlopen(Request(URL + chemin, data=corps, headers=entetes), timeout=10) as r:
            return r.status, json.loads(r.read() or b"{}"), r.headers
    except HTTPError as e:
        return e.code, json.loads(e.read() or b"{}"), e.headers


def demander(texte, reponse):
    n0 = len(appel("/api/evenements?depuis=0")[1]["evenements"])
    faux.SCRIPT.append(faux.ol(reponse))
    assert appel("/api/message", {"texte": texte})[0] == 200
    for _ in range(100):
        if any(e["type"] == "fin" for e in appel("/api/evenements?depuis=0")[1]["evenements"][n0:]):
            return
        time.sleep(0.1)
    raise AssertionError("pas de fin")


try:
    for _ in range(50):
        try:
            urlopen(URL + "/", timeout=1).read()
            break
        except OSError:
            time.sleep(0.2)
    jeton = open(os.path.join(HOME_TEST, ".config/morpheus/jeton_web")).read().strip()
    COOKIE = appel("/api/connexion", {"jeton": jeton})[2]["Set-Cookie"].split(";")[0]

    etat = appel("/api/etat")[1]
    assert etat["racine"] == DISCUSSIONS and etat["discussions"] is True and etat["projet"] == "Discussions", etat

    projets = appel("/api/projets")[1]["projets"]
    assert projets[0] == {"nom": "Discussions", "chemin": DISCUSSIONS, "type": "discussions"}, projets
    autres = [p for p in projets if p["type"] == "autre"]
    assert [p["chemin"] for p in autres] == [ailleurs], f"seul « ailleurs » doit apparaître (ni ~ ni ~/projets) : {autres}"
    assert appel("/api/projet", {"chemin": os.path.realpath(RACINE_PROJETS)})[0] == 400, "~/projets n'est pas un projet"
    assert autres[0]["nom"] == "~/ailleurs"

    # Une discussion, rangée à part
    demander("Qu'est-ce qu'une liste en Python ?", "Une suite ordonnée de valeurs.")
    c = appel("/api/conversations")[1]["conversations"]
    assert [v["titre"] for v in c] == ["Qu'est-ce qu'une liste en Python ?"]
    systeme = faux.RECUS[-1][1]["messages"][0]["content"]
    assert "discussion libre" in systeme, "le modèle doit savoir qu'aucun projet n'est associé"

    # L'ancienne session d'un autre dossier est consultable
    assert appel("/api/projet", {"chemin": ailleurs})[0] == 200
    c = appel("/api/conversations")[1]["conversations"]
    assert [v["titre"] for v in c] == ["vieille question"], c
    assert appel("/api/conversation/ouvrir", {"id": c[0]["id"]})[0] == 200

    # Le dossier personnel reste interdit
    assert appel("/api/projet", {"chemin": os.path.realpath(HOME_TEST)})[0] == 400

    # Retour aux discussions : la discussion est toujours là
    assert appel("/api/projet", {"chemin": DISCUSSIONS})[0] == 200
    assert len(appel("/api/conversations")[1]["conversations"]) == 1
    # Retirer « ailleurs » de la liste : ses conversations vont à la corbeille, le dossier reste
    assert appel("/api/dossier/retirer", {"chemin": DISCUSSIONS})[0] == 400, "seuls les autres dossiers"
    code, rep, _ = appel("/api/dossier/retirer", {"chemin": ailleurs})
    assert code == 200 and rep["conversations"] == 1, rep
    assert os.path.isdir(ailleurs), "le dossier ne doit pas être touché"
    assert os.path.exists(os.path.join(HOME_TEST, ".local/share/Trash/files/20260101-100000-000001.jsonl"))
    assert not [p for p in appel("/api/projets")[1]["projets"] if p["type"] == "autre"]
    print("OK : discussions libres, autres dossiers consultables et retirables, dossier personnel exclu")
finally:
    serveur.terminate()
    try:
        sortie = serveur.communicate(timeout=5)[0]
    except subprocess.TimeoutExpired:
        serveur.kill()
        sortie = serveur.communicate()[0]
    print(sortie[-2000:])
