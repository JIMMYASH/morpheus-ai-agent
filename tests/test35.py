import os, sys, json, time, glob, subprocess
from urllib.request import Request, urlopen
from urllib.error import HTTPError
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
sys.path.insert(0, BASE); import faux
faux.lancer(18434)
env = dict(os.environ, HOME=HOME_TEST, XDG_DATA_HOME=os.path.join(HOME_TEST, ".local/share"))
PROJETS = os.path.realpath(os.path.join(HOME_TEST, "projets"))
CORBEILLE = os.path.join(HOME_TEST, ".local/share/Trash")
SESSIONS = os.path.join(HOME_TEST, ".local/share/morpheus/sessions")

# Renommer / mettre à la corbeille un dossier de projet depuis l'interface web.
PORT = 18769
URL = f"http://127.0.0.1:{PORT}"
serveur = subprocess.Popen([sys.executable, MORPHEUS, "--web", "--port", str(PORT), "--hote", "127.0.0.1"],
                           cwd=PROJ, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
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

    # Les dossiers techniques de ~/projets ne sont pas des projets
    for technique in ("__pycache__", "node_modules", "venv"):
        os.makedirs(os.path.join(PROJETS, technique))
    noms = [p["nom"] for p in appel("/api/projets")[1]["projets"]]
    assert not {"__pycache__", "node_modules", "venv"} & set(noms), noms
    assert appel("/api/projets", {"nom": "build"})[0] == 400, "un nom technique serait invisible dans la liste"

    # Projet « alpha » avec une conversation
    assert appel("/api/projets", {"nom": "alpha", "git": True})[0] == 200
    alpha = os.path.join(PROJETS, "alpha")
    open(os.path.join(alpha, "note.txt"), "w").write("contenu\n")
    demander("Que contient ce projet ?", "Un fichier note.txt.")
    assert appel("/api/projets", {"nom": "gamma"})[0] == 200          # un autre projet existe
    appel("/api/projet", {"chemin": alpha})
    ident = appel("/api/conversations")[1]["conversations"][0]["id"]
    assert appel("/api/conversation/ouvrir", {"id": ident})[0] == 200

    # Renommages refusés
    for mauvais in ("../evasion", "", "gamma"):
        assert appel("/api/projet/renommer", {"chemin": alpha, "nom": mauvais})[0] == 400, mauvais
    discussions = [p for p in appel("/api/projets")[1]["projets"] if p["type"] == "discussions"][0]["chemin"]
    for interdit in (os.path.realpath(PROJ), discussions, "/etc", PROJETS):
        assert appel("/api/projet/renommer", {"chemin": interdit, "nom": "x"})[0] == 400, interdit
        assert appel("/api/projet/supprimer", {"chemin": interdit})[0] == 400, interdit
    assert os.path.isdir(os.path.realpath(PROJ))

    # Renommer le projet ouvert : le dossier, ses conversations et la conversation ouverte suivent
    code, rep, _ = appel("/api/projet/renommer", {"chemin": alpha, "nom": "beta"})
    assert code == 200, rep
    beta = os.path.join(PROJETS, "beta")
    assert not os.path.exists(alpha) and open(os.path.join(beta, "note.txt")).read() == "contenu\n"
    etat = appel("/api/etat")[1]
    assert etat["racine"] == beta and etat["conversation"], etat
    c = appel("/api/conversations")[1]
    assert [v["titre"] for v in c["conversations"]] == ["Que contient ce projet ?"] and c["actuelle"] == etat["conversation"]
    entete = json.loads(open(os.path.join(SESSIONS, etat["conversation"] + ".jsonl")).readline())
    assert entete["racine"] == beta
    demander("Et maintenant ?", "On continue dans beta.")
    assert len(glob.glob(os.path.join(SESSIONS, "*.jsonl"))) == 1, "la conversation continue dans le même journal"

    # Mettre à la corbeille un projet non ouvert
    assert appel("/api/projet/supprimer", {"chemin": os.path.join(PROJETS, "gamma")})[0] == 200
    assert not os.path.exists(os.path.join(PROJETS, "gamma"))
    assert os.path.isdir(os.path.join(CORBEILLE, "files", "gamma"))
    assert appel("/api/etat")[1]["racine"] == beta

    # Mettre à la corbeille le projet ouvert : retour aux discussions, fichier .trashinfo correct
    assert appel("/api/projet/supprimer", {"chemin": beta})[0] == 200
    assert open(os.path.join(CORBEILLE, "files", "beta", "note.txt")).read() == "contenu\n"
    info = open(os.path.join(CORBEILLE, "info", "beta.trashinfo")).read()
    assert info.startswith("[Trash Info]\nPath=") and "beta" in info and "DeletionDate=" in info, info
    etat = appel("/api/etat")[1]
    assert etat["discussions"] is True, etat
    noms = [p["nom"] for p in appel("/api/projets")[1]["projets"]]
    assert "beta" not in noms and "gamma" not in noms, noms

    # Un second projet du même nom mis à la corbeille ne l'écrase pas
    assert appel("/api/projets", {"nom": "beta"})[0] == 200
    assert appel("/api/projet/supprimer", {"chemin": beta})[0] == 200
    assert os.path.isdir(os.path.join(CORBEILLE, "files", "beta.2"))
    print("OK : projets renommés (conversations comprises) et mis à la corbeille ; autres dossiers protégés")
finally:
    serveur.terminate()
    try:
        sortie = serveur.communicate(timeout=5)[0]
    except subprocess.TimeoutExpired:
        serveur.kill()
        sortie = serveur.communicate()[0]
    print(sortie[-2000:])
