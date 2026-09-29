import os, sys, json, time, glob, subprocess
from urllib.request import Request, urlopen
from urllib.error import HTTPError
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
sys.path.insert(0, BASE); import faux
faux.lancer(18434)
env = dict(os.environ, HOME=HOME_TEST)
SESSIONS = os.path.join(HOME_TEST, ".local/share/morpheus/sessions")
journaux = lambda: sorted(glob.glob(os.path.join(SESSIONS, "*.jsonl")))

# Conversations : chaque conversation vit dans un seul journal (une reprise continue dans le même
# fichier, aucun journal vide), et l'interface web permet de les lister, rouvrir, renommer, supprimer.

# --- 1. Terminal : pas de journal vide ; -c continue le même fichier ---
subprocess.run([sys.executable, MORPHEUS], input="/quitter\n", capture_output=True, text=True, timeout=60, cwd=PROJ, env=env)
assert journaux() == [], f"lancer puis quitter ne doit créer aucun journal : {journaux()}"
faux.SCRIPT += [faux.ol("Première réponse.")]
subprocess.run([sys.executable, MORPHEUS, "première question ?"], input="/quitter\n", capture_output=True, text=True,
               timeout=60, cwd=PROJ, env=env)
assert len(journaux()) == 1
faux.SCRIPT += [faux.ol("Deuxième réponse.")]
p = subprocess.run([sys.executable, MORPHEUS, "-c"], input="deuxième question ?\n/quitter\n", capture_output=True,
                   text=True, timeout=60, cwd=PROJ, env=env)
assert "Session précédente reprise" in p.stdout, p.stdout
assert len(journaux()) == 1, f"-c doit continuer le même journal, pas en créer un autre : {journaux()}"
contenu = open(journaux()[0], encoding="utf-8").read()
assert "première question" in contenu and "deuxième question" in contenu
assert contenu.count('"type": "entete"') == 1
for f in journaux():
    os.remove(f)

# --- 2. Interface web ---
PORT = 18767
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
    if reponse:
        faux.SCRIPT.append(faux.ol(reponse))
    assert appel("/api/message", {"texte": texte})[0] == 200
    for _ in range(100):
        evs = appel("/api/evenements?depuis=0")[1]["evenements"]
        if any(e["type"] == "fin" for e in evs[n0:]):
            return evs
        time.sleep(0.1)
    raise AssertionError("pas de fin")


def conversations():
    return appel("/api/conversations")[1]


try:
    for _ in range(50):
        try:
            urlopen(URL + "/", timeout=1).read()
            break
        except OSError:
            time.sleep(0.2)
    jeton = open(os.path.join(HOME_TEST, ".config/morpheus/jeton_web")).read().strip()
    COOKIE = appel("/api/connexion", {"jeton": jeton})[2]["Set-Cookie"].split(";")[0]
    assert journaux() == [], "ouvrir l'interface ne doit créer aucun journal"
    assert conversations() == {"conversations": [], "actuelle": None}

    demander("Explique le projet", "C'est un projet vide.")
    c = conversations()
    assert len(c["conversations"]) == 1 and c["conversations"][0]["titre"] == "Explique le projet", c
    premiere = c["conversations"][0]["id"]
    assert c["actuelle"] == premiere

    demander("/reset", None)
    assert conversations()["actuelle"] is None
    demander("Que mettre dans un README ?", "Voici une idée de README.")
    c = conversations()
    assert [v["titre"] for v in c["conversations"]] == ["Que mettre dans un README ?", "Explique le projet"], c
    seconde = c["actuelle"]

    # Renommer (le titre est gardé dans le journal)
    assert appel("/api/conversation/renommer", {"id": seconde, "titre": "  Mon   README  "})[0] == 200
    assert conversations()["conversations"][0]["titre"] == "Mon README"
    assert appel("/api/conversation/renommer", {"id": seconde, "titre": "   "})[0] == 400

    # Rouvrir la première : son contenu est rejoué, la suite s'écrit dans le même journal
    assert appel("/api/conversation/ouvrir", {"id": premiere})[0] == 200
    etat = appel("/api/etat")[1]
    evs = appel(f"/api/evenements?depuis={etat['debut']}")[1]["evenements"]
    assert [e["texte"] for e in evs if e["type"] == "utilisateur"] == ["Explique le projet"]
    assert "".join(e["texte"] for e in evs if e["type"] == "texte") == "C'est un projet vide."
    assert etat["conversation"] == premiere
    demander("Et maintenant ?", "Maintenant, on peut commencer.")
    assert len(journaux()) == 2, journaux()
    resume = [v for v in conversations()["conversations"] if v["id"] == premiere][0]
    assert resume["demandes"] == 2
    assert conversations()["conversations"][0]["id"] == premiere, "la plus récemment utilisée en premier"
    historique = [m["content"] for m in faux.RECUS[-1][1]["messages"] if m["role"] == "user"]
    assert any("Explique le projet" in h for h in historique), "le modèle doit recevoir l'historique repris"

    # Sécurité : identifiants invalides refusés
    for mauvais in ("../../x", "20260101-000000-000000", ""):
        assert appel("/api/conversation/ouvrir", {"id": mauvais})[0] == 400, mauvais
        assert appel("/api/conversation/supprimer", {"id": mauvais})[0] == 400, mauvais

    # Supprimer une autre conversation, puis la conversation ouverte
    assert appel("/api/conversation/supprimer", {"id": seconde})[0] == 200
    assert [v["id"] for v in conversations()["conversations"]] == [premiere]
    assert appel("/api/conversation/supprimer", {"id": premiere})[0] == 200
    assert conversations() == {"conversations": [], "actuelle": None}
    assert journaux() == []

    # Changer de projet ne crée pas de journal vide, et les conversations sont propres à chaque projet
    demander("Question dans le premier projet", "Réponse.")
    assert appel("/api/projets", {"nom": "autre"})[0] == 200
    assert conversations() == {"conversations": [], "actuelle": None}
    assert len(journaux()) == 1
    print("OK : conversations listées, rouvertes, renommées, supprimées ; un journal par conversation")
finally:
    serveur.terminate()
    try:
        sortie = serveur.communicate(timeout=5)[0]
    except subprocess.TimeoutExpired:
        serveur.kill()
        sortie = serveur.communicate()[0]
    print(sortie[-2000:])
