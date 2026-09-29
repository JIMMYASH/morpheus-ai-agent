import os, sys, json, time, subprocess
from urllib.request import Request, urlopen
from urllib.error import HTTPError
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
sys.path.insert(0, BASE); import faux
faux.lancer(18434)
env = dict(os.environ, HOME=HOME_TEST)

# Modèle choisi mais pas installé : la page propose de le télécharger (taille lue dans la bibliothèque
# d'Ollama), suit la progression, peut annuler ; réservé à l'administrateur.
faux.REGISTRE.update({"petit:1b": [1_000_000_000, 300_000_000], "lent:latest": [5_000_000_000] * 3})
PORT = 18773
URL = f"http://127.0.0.1:{PORT}"
serveur = subprocess.Popen([sys.executable, MORPHEUS, "--web", "--port", str(PORT), "--hote", "127.0.0.1"],
                           cwd=PROJ, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def appel(cookie, chemin, donnees=None):
    entetes = {"Content-Type": "application/json", "X-Morpheus": "1", "Cookie": cookie}
    corps = json.dumps(donnees).encode() if donnees is not None else None
    try:
        with urlopen(Request(URL + chemin, data=corps, headers=entetes), timeout=10) as r:
            return r.status, json.loads(r.read() or b"{}")
    except HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def connexion(jeton):
    with urlopen(Request(URL + "/api/connexion", data=json.dumps({"jeton": jeton}).encode(),
                         headers={"Content-Type": "application/json", "X-Morpheus": "1"}), timeout=10) as r:
        return r.headers["Set-Cookie"].split(";")[0]


def attendre_fin(cookie):
    for _ in range(150):
        t = appel(cookie, "/api/modele/telechargement")[1]
        if t.get("fini"):
            return t
        time.sleep(0.1)
    raise AssertionError("téléchargement jamais terminé : " + json.dumps(t))


try:
    for _ in range(50):
        try:
            urlopen(URL + "/", timeout=1).read()
            break
        except OSError:
            time.sleep(0.2)
    admin = connexion(open(os.path.join(HOME_TEST, ".config/morpheus/jeton_web")).read().strip())
    page = urlopen(URL + "/", timeout=5).read().decode()
    assert 'id="telechargement"' in page and "/api/modele/telecharger" in page

    # Pas installé mais dans la bibliothèque : proposé, avec la taille ; inconnu : refus simple
    code, r = appel(admin, "/api/modele", {"modele": "petit:1b"})
    assert code == 404 and r["telechargeable"] is True and r["taille"] == 1_300_000_500, r
    code, r = appel(admin, "/api/modele", {"modele": "inexistant:9b"})
    assert code == 400 and not r.get("telechargeable") and "introuvable" in r["erreur"], r
    assert appel(admin, "/api/etat")[1]["modele"] == "qwen3-coder-next", "le modèle ne change pas tant qu'il n'est pas installé"
    for mauvais in ("../x", "a b", "", "claude-code"):
        assert appel(admin, "/api/modele/telecharger", {"modele": mauvais})[0] == 400, mauvais

    # Téléchargement : progression puis succès ; le modèle peut ensuite être choisi
    assert appel(admin, "/api/modele/telecharger", {"modele": "petit:1b"})[0] == 200
    t = attendre_fin(admin)
    assert t["reussi"] and t["erreur"] is None and t["fait"] == t["total"] == 1_300_000_000, t
    assert appel(admin, "/api/modele", {"modele": "petit:1b"})[0] == 200
    assert appel(admin, "/api/etat")[1]["modele"] == "petit:1b"

    # Annulation d'un téléchargement lent ; un seul téléchargement à la fois
    faux.PAUSE_PULL = 0.3
    assert appel(admin, "/api/modele/telecharger", {"modele": "lent"})[0] == 200
    code, r = appel(admin, "/api/modele/telecharger", {"modele": "petit:1b"})
    assert code == 400 and "déjà en cours" in r["erreur"], r
    time.sleep(0.8)
    t = appel(admin, "/api/modele/telechargement")[1]
    assert not t["fini"] and 0 < t["fait"] < 15_000_000_000, t
    assert appel(admin, "/api/modele/annuler", {})[0] == 200
    t = attendre_fin(admin)
    assert not t["reussi"] and t["erreur"] == "téléchargement annulé", t
    faux.PAUSE_PULL = 0

    # Modèle refusé par Ollama au téléchargement (hors bibliothèque, taille inconnue) : erreur affichée
    assert appel(admin, "/api/modele/telecharger", {"modele": "hf.co/quelqun/modele:Q4"})[0] == 200
    t = attendre_fin(admin)
    assert not t["reussi"] and "does not exist" in t["erreur"], t

    # Invité : ni proposition ni téléchargement
    code, info = appel(admin, "/api/utilisateurs", {"nom": "Marie"})
    marie = connexion(info["lien"].split("jeton=")[1])
    code, r = appel(marie, "/api/modele", {"modele": "lent"})
    assert code == 400 and not r.get("telechargeable"), r
    assert appel(marie, "/api/modele/telecharger", {"modele": "lent"})[0] == 403
    assert appel(marie, "/api/modele/telechargement")[0] == 403
    print("OK")
finally:
    serveur.terminate()
    print(serveur.communicate(timeout=10)[0][-3000:])
