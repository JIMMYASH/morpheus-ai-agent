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

# Interface web (morpheus --web) : jeton obligatoire, conversation avec validation par
# boutons, volet de fichiers limité au projet, création/ouverture de projets, paramètres,
# bouton Arrêter.
PORT = 18765
URL = f"http://127.0.0.1:{PORT}"
serveur = subprocess.Popen([sys.executable, MORPHEUS, "--web", "--port", str(PORT), "--hote", "127.0.0.1"],
                           cwd=PROJ, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
COOKIE = ""


def appel(chemin, donnees=None, cookie=True, entete=True):
    entetes = {"Content-Type": "application/json"}
    if cookie and COOKIE:
        entetes["Cookie"] = COOKIE
    if entete and donnees is not None:
        entetes["X-Morpheus"] = "1"
    corps = json.dumps(donnees).encode() if donnees is not None else None
    try:
        with urlopen(Request(URL + chemin, data=corps, headers=entetes), timeout=10) as r:
            return r.status, json.loads(r.read() or b"{}"), r.headers
    except HTTPError as e:
        return e.code, json.loads(e.read() or b"{}"), e.headers


def evenements(depuis=0):
    return appel(f"/api/evenements?depuis={depuis}")[1]["evenements"]


def attendre(condition, delai=20):
    fin = time.time() + delai
    while time.time() < fin:
        evs = evenements()
        if condition(evs):
            return evs
        time.sleep(0.2)
    raise AssertionError("délai dépassé ; événements : " + json.dumps(evenements(), ensure_ascii=False)[-3000:])


try:
    for _ in range(50):                                   # attendre le démarrage du serveur
        try:
            urlopen(URL + "/", timeout=1).read()
            break
        except OSError:
            time.sleep(0.2)
    jeton = open(os.path.join(HOME_TEST, ".config/morpheus/jeton_web")).read().strip()
    assert oct(os.stat(os.path.join(HOME_TEST, ".config/morpheus/jeton_web")).st_mode)[-3:] == "600"

    # 1. Authentification
    assert appel("/api/etat")[0] == 401, "sans jeton, l'API doit refuser"
    assert appel("/api/connexion", {"jeton": "mauvais"})[0] == 401
    code, _, entetes = appel("/api/connexion", {"jeton": jeton})
    assert code == 200
    COOKIE = entetes["Set-Cookie"].split(";")[0]
    code, etat, _ = appel("/api/etat")
    assert code == 200 and etat["racine"] == os.path.realpath(PROJ), etat
    assert appel("/api/message", {"texte": "x"}, entete=False)[0] == 401, "sans l'en-tête X-Morpheus : refus (CSRF)"

    # 2. Conversation avec validation par bouton
    faux.SCRIPT += [faux.ol("", [T("write_file", {"path": "a.txt", "content": "bonjour\n"})]),
                    faux.ol("Fichier **a.txt** créé.")]
    assert appel("/api/message", {"texte": "crée a.txt"})[0] == 200
    evs = attendre(lambda e: any(x["type"] == "question" for x in e))
    assert appel("/api/message", {"texte": "autre"})[0] == 409, "une seule demande à la fois"
    question = [x for x in evs if x["type"] == "question"][-1]
    assert any(x["type"] == "diff" and x["chemin"] == "a.txt" for x in evs), "le diff doit partir dans le volet"
    assert appel("/api/reponse", {"id": question["id"], "reponse": "o"})[0] == 200
    evs = attendre(lambda e: any(x["type"] == "fin" for x in e[question["n"]:]))
    assert open(os.path.join(PROJ, "a.txt")).read() == "bonjour\n"
    types = [x["type"] for x in evs]
    assert "utilisateur" in types and "ecrit" in types and "texte" in types, types
    assert "".join(x["texte"] for x in evs if x["type"] == "texte") == "Fichier **a.txt** créé."
    assert any("write_file" in x.get("texte", "") for x in evs if x["type"] == "console")

    # 3. Refus avec consigne
    faux.SCRIPT += [faux.ol("", [T("write_file", {"path": "b.txt", "content": "b\n"})]),
                    faux.ol("D'accord, c'est refusé : je ne crée pas b.txt.")]
    n0 = len(evenements())
    appel("/api/message", {"texte": "crée b.txt"})
    evs = attendre(lambda e: any(x["type"] == "question" for x in e[n0:]))
    q = [x for x in evs[n0:] if x["type"] == "question"][-1]
    appel("/api/reponse", {"id": q["id"], "reponse": "n", "consigne": "pas maintenant"})
    attendre(lambda e: any(x["type"] == "fin" for x in e[q["n"]:]))
    assert not os.path.exists(os.path.join(PROJ, "b.txt"))
    assert "pas maintenant" in json.dumps(faux.RECUS[-1][1]["messages"], ensure_ascii=False), \
        "la consigne doit être transmise au modèle"

    # 4. Bouton Arrêter pendant une validation
    faux.SCRIPT += [faux.ol("", [T("write_file", {"path": "c.txt", "content": "c\n"})])]
    n0 = len(evenements())
    appel("/api/message", {"texte": "crée c.txt"})
    attendre(lambda e: any(x["type"] == "question" for x in e[n0:]))
    assert appel("/api/arreter", {})[1]["ok"]
    attendre(lambda e: any(x["type"] == "fin" for x in e[n0:]))
    assert not os.path.exists(os.path.join(PROJ, "c.txt"))

    # 5. Volet de fichiers : seulement dans le projet
    assert "a.txt" in appel("/api/arbre")[1]["fichiers"]
    assert appel("/api/fichier?chemin=a.txt")[1]["contenu"] == "bonjour\n"
    for interdit in ("../../../etc/passwd", "/etc/passwd", "~/.config/morpheus/jeton_web"):
        assert appel("/api/fichier?chemin=" + interdit)[0] == 400, interdit

    # 6. Commandes /annuler et /plan
    n0 = len(evenements())
    appel("/api/message", {"texte": "/plan"})
    evs = attendre(lambda e: any(x["type"] == "fin" for x in e[n0:]))
    assert [x for x in evs[n0:] if x["type"] == "fin"][-1]["mode_plan"] is True
    appel("/api/message", {"texte": "/plan"})
    time.sleep(0.5)

    # 7. Projets : création (nom validé), ouverture, liste limitée à ~/projets
    assert appel("/api/projets", {"nom": "../evasion"})[0] == 400
    assert appel("/api/projet", {"chemin": "/etc"})[0] == 400, "on ne peut ouvrir qu'un projet connu"
    code, rep, _ = appel("/api/projets", {"nom": "essai web", "git": True})
    assert code == 200, rep
    nouveau = os.path.join(HOME_TEST, "projets", "essai web")
    assert os.path.isdir(os.path.join(nouveau, ".git")) and os.path.isfile(os.path.join(nouveau, ".gitignore"))
    assert appel("/api/etat")[1]["racine"] == os.path.realpath(nouveau)
    assert appel("/api/arbre")[1]["fichiers"] == [".gitignore"]
    chemins = [p["chemin"] for p in appel("/api/projets")[1]["projets"]]
    assert os.path.realpath(nouveau) in chemins and os.path.realpath(PROJ) in chemins, chemins
    assert appel("/api/projet", {"chemin": os.path.realpath(PROJ)})[0] == 200

    # 8. Paramètres : enregistrés dans config.json, valeurs invalides refusées
    assert appel("/api/config", {"num_ctx": "100"})[0] == 400
    assert appel("/api/config", {"modele": "autre-modele", "temperature": "0.3", "top_k": ""})[0] == 200
    config = json.load(open(os.path.join(HOME_TEST, ".config/morpheus/config.json")))
    assert config["modele"] == "autre-modele" and config["temperature"] == 0.3 and config["top_k"] is None
    assert appel("/api/config")[1]["config"]["modele"] == "autre-modele"

    # 9. Suggestions de l'écran d'accueil : l'état du projet est fourni à la page
    etat = appel("/api/etat")[1]
    assert etat["projet_vide"] is False and etat["morpheus_md"] is False, etat
    appel("/api/projet", {"chemin": os.path.realpath(nouveau)})
    assert appel("/api/etat")[1]["projet_vide"] is True, "un projet avec seulement .gitignore compte comme vide"
    appel("/api/projet", {"chemin": os.path.realpath(PROJ)})

    # 10. Logo : servi sans jeton s'il existe à côté de morpheus.py, 404 sinon
    logo = os.path.join(os.path.dirname(MORPHEUS), "morpheus.png")
    try:
        with urlopen(URL + "/logo.png", timeout=5) as r:
            assert os.path.exists(logo) and r.headers["Content-Type"] == "image/png"
            assert "max-age" in r.headers["Cache-Control"] and r.read() == open(logo, "rb").read()
    except HTTPError as e:
        assert e.code == 404 and not os.path.exists(logo)

    # 11. La page elle-même est servie sans jeton (elle affiche la fenêtre de connexion)
    with urlopen(URL + "/", timeout=5) as r:
        page = r.read().decode()
        assert "MORPHE" in page and "Content-Security-Policy" in r.headers
    print("OK : interface web (jeton, conversation, validations, arrêt, fichiers, projets, paramètres)")
finally:
    serveur.terminate()
    try:
        sortie = serveur.communicate(timeout=5)[0]
    except subprocess.TimeoutExpired:
        serveur.kill()
        sortie = serveur.communicate()[0]
    print(sortie[-3000:])
