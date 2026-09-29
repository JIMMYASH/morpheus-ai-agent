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
env = dict(os.environ, HOME=HOME_TEST, XDG_DATA_HOME=os.path.join(HOME_TEST, ".local/share"))
env.pop("MORPHEUS_MODE", None)          # mode par défaut : Chat

# Interface web : interrupteur Chat / Dév (commandes /chat et /dev), mode Chat par défaut.
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


def envoyer(texte, reponses=()):
    n0 = len(appel("/api/evenements?depuis=0")[1]["evenements"])
    faux.SCRIPT.extend(reponses)
    assert appel("/api/message", {"texte": texte})[0] == 200
    for _ in range(100):
        nouveaux = appel("/api/evenements?depuis=0")[1]["evenements"][n0:]
        fin = [e for e in nouveaux if e["type"] == "fin"]
        if fin:
            return fin[-1], nouveaux
        time.sleep(0.1)
    raise AssertionError("pas de fin")


try:
    for _ in range(50):
        try:
            page = urlopen(URL + "/", timeout=1).read().decode()
            break
        except OSError:
            time.sleep(0.2)
    assert 'id="choix-mode"' in page, "l'interrupteur Chat / Dév doit être dans la page"
    jeton = open(os.path.join(HOME_TEST, ".config/morpheus/jeton_web")).read().strip()
    COOKIE = appel("/api/connexion", {"jeton": jeton})[2]["Set-Cookie"].split(";")[0]
    assert appel("/api/etat")[1]["mode"] == "chat"

    # Mode Chat : l'écriture est refusée sans même demander de validation
    fin, evts = envoyer("crée a.txt", [faux.ol("", [T("write_file", {"path": "a.txt", "content": "a"})]),
                                        faux.ol("Impossible en mode Chat.")])
    assert not [e for e in evts if e["type"] == "question"], "aucune validation ne doit être demandée"
    assert "write_file" not in {o["function"]["name"] for o in faux.RECUS[-1][1]["tools"]}

    fin, _ = envoyer("/dev")
    assert fin["mode"] == "dev" and appel("/api/etat")[1]["mode"] == "dev", fin
    fin, _ = envoyer("/plan")
    assert fin["mode_plan"] is True
    fin, _ = envoyer("/chat")
    assert fin["mode"] == "chat" and fin["mode_plan"] is False, "revenir en Chat quitte le mode plan"
    fin, _ = envoyer("/mode")
    assert fin["mode"] == "dev"
    print("OK : interrupteur Chat / Dév de l'interface web")
finally:
    serveur.terminate()
    try:
        sortie = serveur.communicate(timeout=5)[0]
    except subprocess.TimeoutExpired:
        serveur.kill()
        sortie = serveur.communicate()[0]
    print(sortie[-2000:])
