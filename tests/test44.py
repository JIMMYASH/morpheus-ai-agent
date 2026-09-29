import os, sys, json, time, subprocess, glob
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
env.pop("MORPHEUS_MODE", None)
SESSIONS = os.path.join(HOME_TEST, ".local/share/morpheus/sessions")

# Interface web : modifier un message déjà envoyé (la conversation repart de là), et « Arrêter »
# pendant que le modèle réfléchit (aucune donnée reçue) doit arrêter tout de suite.
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


def evenements():
    return appel("/api/evenements?depuis=0")[1]["evenements"]


def attendre_fin(n0, delai=10):
    for _ in range(int(delai * 10)):
        nouveaux = evenements()[n0:]
        # « Modifier » réaffiche la conversation (qui se termine par un « fin ») AVANT de lancer la demande :
        # seule la « fin » qui suit le « debut » de la demande compte.
        types = [e["type"] for e in nouveaux]
        if "debut" in types and "fin" in types[types.index("debut"):]:
            return nouveaux
        time.sleep(0.1)
    raise AssertionError("pas de fin")


def envoyer(chemin, donnees, reponses=()):
    n0 = len(evenements())
    faux.SCRIPT.extend(reponses)
    code, rep, _ = appel(chemin, donnees)
    assert code == 200, (code, rep)
    return attendre_fin(n0)


def demandes_journal():
    fichier = max(glob.glob(os.path.join(SESSIONS, "*.jsonl")), key=os.path.getmtime)
    lignes = [json.loads(l) for l in open(fichier, encoding="utf-8") if l.strip()]
    return [m["content"].split("]\n")[-1] for m in lignes if m.get("role") == "user"]


try:
    for _ in range(50):
        try:
            urlopen(URL + "/", timeout=1).read()
            break
        except OSError:
            time.sleep(0.2)
    jeton = open(os.path.join(HOME_TEST, ".config/morpheus/jeton_web")).read().strip()
    COOKIE = appel("/api/connexion", {"jeton": jeton})[2]["Set-Cookie"].split(";")[0]

    evts = envoyer("/api/message", {"texte": "première question"},
                   [faux.ol("", [T("bash", {"command": "ls"})]), faux.ol("Réponse 1.")])
    assert [e.get("rang") for e in evts if e["type"] == "utilisateur"] == [0], evts
    evts = envoyer("/api/message", {"texte": "deuxième question"}, [faux.ol("Réponse 2.")])
    assert [e.get("rang") for e in evts if e["type"] == "utilisateur"] == [1]
    evts = envoyer("/api/message", {"texte": "/dev"})
    assert [e.get("rang") for e in evts if e["type"] == "utilisateur"] == [None], "une commande ne se modifie pas"
    envoyer("/api/message", {"texte": "/chat"})

    # Modifier la deuxième question : la première et sa réponse restent, la suite est remplacée
    evts = envoyer("/api/modifier", {"rang": 1, "texte": "deuxième question corrigée"}, [faux.ol("Réponse 2 bis.")])
    assert any(e["type"] == "reinit" for e in evts), "la conversation est réaffichée"
    assert demandes_journal() == ["première question", "deuxième question corrigée"], demandes_journal()
    envoyes = [m["content"] for m in faux.RECUS[-1][1]["messages"] if m["role"] in ("user", "assistant")]
    assert "deuxième question" not in envoyes and envoyes[-1].endswith("deuxième question corrigée"), envoyes
    assert "Réponse 1." in envoyes and "Réponse 2." not in envoyes, envoyes
    rangs = [(e["texte"], e.get("rang")) for e in evts if e["type"] == "utilisateur"]
    assert rangs == [("première question", 0), ("deuxième question corrigée", 1)], rangs

    # Modifier la première : tout repart de zéro
    envoyer("/api/modifier", {"rang": 0, "texte": "tout autre chose"}, [faux.ol("Ok.")])
    assert demandes_journal() == ["tout autre chose"], demandes_journal()
    assert appel("/api/modifier", {"rang": 5, "texte": "x"})[0] == 400, "rang inexistant"
    assert appel("/api/modifier", {"rang": "0", "texte": "x"})[0] == 400, "rang invalide"
    assert demandes_journal() == ["tout autre chose"]

    # Arrêter pendant la réflexion : le modèle ne répond qu'au bout de 6 s, l'arrêt doit être immédiat
    n0 = len(evenements())
    faux.SCRIPT.append({"pause": 6})
    n_recus = len(faux.RECUS)
    assert appel("/api/message", {"texte": "question longue"})[0] == 200
    for _ in range(100):             # attendre que la demande soit vraiment chez le modèle (machine lente)
        if len(faux.RECUS) > n_recus:
            break
        time.sleep(0.05)
    time.sleep(0.2)
    assert appel("/api/modifier", {"rang": 1, "texte": "x"})[0] == 409, "pas de modification pendant le travail"
    debut = time.time()
    assert appel("/api/arreter", {})[1]["ok"] is True
    evts = attendre_fin(n0, delai=4)
    assert time.time() - debut < 3, "l'arrêt doit être immédiat"
    console = " ".join(e.get("texte", "") for e in evts if e["type"] == "console")
    assert "interrompu" in console and "Erreur" not in console, console
    print("OK : modifier un message, arrêter pendant la réflexion")
finally:
    serveur.terminate()
    try:
        sortie = serveur.communicate(timeout=5)[0]
    except subprocess.TimeoutExpired:
        serveur.kill()
        sortie = serveur.communicate()[0]
    print(sortie[-2000:])
