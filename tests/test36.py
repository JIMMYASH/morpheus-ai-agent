import os, sys, json, time, subprocess
from urllib.request import Request, urlopen
from urllib.error import HTTPError
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
sys.path.insert(0, BASE); import faux
faux.lancer(18434)
T = lambda n, a: {"function": {"name": n, "arguments": a}}
env = dict(os.environ, HOME=HOME_TEST)

# Liste déroulante des modèles installés : changer de modèle depuis l'en-tête de l'interface web.
PORT = 18770
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


def attendre(condition):
    for _ in range(100):
        evs = appel("/api/evenements?depuis=0")[1]["evenements"]
        if condition(evs):
            return evs
        time.sleep(0.1)
    raise AssertionError("délai dépassé")


# Un ancien journal utilisé avec un modèle cloud qui n'est plus le modèle courant
SESSIONS = os.path.join(HOME_TEST, ".local/share/morpheus/sessions")
os.makedirs(SESSIONS)
with open(os.path.join(SESSIONS, "20260101-100000-000001.jsonl"), "w", encoding="utf-8") as f:
    f.write(json.dumps({"type": "entete", "racine": "/ailleurs", "modele": "vieux-modele:cloud"}) + "\n")
    f.write(json.dumps({"role": "user", "content": "question"}) + "\n")

try:
    for _ in range(50):
        try:
            urlopen(URL + "/", timeout=1).read()
            break
        except OSError:
            time.sleep(0.2)
    jeton = open(os.path.join(HOME_TEST, ".config/morpheus/jeton_web")).read().strip()
    COOKIE = appel("/api/connexion", {"jeton": jeton})[2]["Set-Cookie"].split(";")[0]

    d = appel("/api/modeles")[1]
    assert d["installes"] == ["autre:7b", "qwen3-coder-next"] and d["actuel"] == "qwen3-coder-next", d
    assert d["autres"] == ["vieux-modele:cloud"], "les modèles des anciens journaux doivent être proposés"

    # Modèle cloud (connu d'Ollama mais pas « installé ») : accepté, et il reste dans la liste ensuite
    assert appel("/api/modele", {"modele": "kimi-k2.7-code:cloud"})[0] == 200
    assert appel("/api/etat")[1]["modele"] == "kimi-k2.7-code:cloud"

    # Changement de modèle : appliqué tout de suite, enregistré, annoncé aux autres onglets
    assert appel("/api/modele", {"modele": "autre:7b"})[0] == 200
    assert appel("/api/etat")[1]["modele"] == "autre:7b"
    assert "kimi-k2.7-code:cloud" in appel("/api/modeles")[1]["autres"], "kimi ne doit pas disparaître de la liste"
    assert json.load(open(os.path.join(HOME_TEST, ".config/morpheus/config.json")))["modele"] == "autre:7b"
    assert any(e["type"] == "infos" and e["modele"] == "autre:7b" for e in appel("/api/evenements?depuis=0")[1]["evenements"])
    faux.SCRIPT.append(faux.ol("Bonjour depuis autre:7b."))
    n0 = len(appel("/api/evenements?depuis=0")[1]["evenements"])
    appel("/api/message", {"texte": "dis bonjour ?"})
    attendre(lambda e: any(x["type"] == "fin" for x in e[n0:]))
    assert faux.RECUS[-1][1]["model"] == "autre:7b", "la requête suivante doit utiliser le nouveau modèle"

    # Modèle non installé : refusé
    assert appel("/api/modele", {"modele": "inexistant"})[0] == 400
    assert appel("/api/modele", {"modele": ""})[0] == 400

    # Pendant une demande en cours (validation en attente) : refusé
    faux.SCRIPT += [faux.ol("", [T("write_file", {"path": "x.txt", "content": "x\n"})]), faux.ol("Fichier créé.")]
    n0 = len(appel("/api/evenements?depuis=0")[1]["evenements"])
    appel("/api/message", {"texte": "crée x.txt"})
    evs = attendre(lambda e: any(x["type"] == "question" for x in e[n0:]))
    assert appel("/api/modele", {"modele": "qwen3-coder-next"})[0] == 409
    q = [x for x in evs[n0:] if x["type"] == "question"][-1]
    appel("/api/reponse", {"id": q["id"], "reponse": "o"})
    attendre(lambda e: any(x["type"] == "fin" for x in e[q["n"]:]))
    assert appel("/api/modele", {"modele": "qwen3-coder-next"})[0] == 200
    print("OK : liste des modèles installés, changement immédiat et enregistré, refus si inconnu ou occupé")
finally:
    serveur.terminate()
    try:
        sortie = serveur.communicate(timeout=5)[0]
    except subprocess.TimeoutExpired:
        serveur.kill()
        sortie = serveur.communicate()[0]
    print(sortie[-2000:])
