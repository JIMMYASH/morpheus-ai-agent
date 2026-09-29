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
PARTAGES = os.path.realpath(os.path.join(HOME_TEST, "projets-partages"))

# Plusieurs personnes : un lien (jeton) par invité, un espace à soi, une file d'attente pour le modèle.
PORT = 18771
URL = f"http://127.0.0.1:{PORT}"
serveur = subprocess.Popen([sys.executable, MORPHEUS, "--web", "--port", str(PORT), "--hote", "127.0.0.1"],
                           cwd=PROJ, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def appel(cookie, chemin, donnees=None):
    entetes = {"Content-Type": "application/json", "X-Morpheus": "1", "Cookie": cookie}
    corps = json.dumps(donnees).encode() if donnees is not None else None
    try:
        with urlopen(Request(URL + chemin, data=corps, headers=entetes), timeout=10) as r:
            return r.status, json.loads(r.read() or b"{}"), r.headers
    except HTTPError as e:
        return e.code, json.loads(e.read() or b"{}"), e.headers


def connexion(jeton):
    code, _, entetes = appel("", "/api/connexion", {"jeton": jeton})
    assert code == 200
    return entetes["Set-Cookie"].split(";")[0]


def evenements(cookie, depuis=0):
    return appel(cookie, f"/api/evenements?depuis={depuis}")[1]["evenements"]


def attendre(cookie, condition, delai=20):
    fin = time.time() + delai
    while time.time() < fin:
        evs = evenements(cookie)
        if condition(evs):
            return evs
        time.sleep(0.1)
    raise AssertionError("délai dépassé : " + json.dumps(evenements(cookie), ensure_ascii=False)[-2000:])


try:
    for _ in range(50):
        try:
            urlopen(URL + "/", timeout=1).read()
            break
        except OSError:
            time.sleep(0.2)
    admin = connexion(open(os.path.join(HOME_TEST, ".config/morpheus/jeton_web")).read().strip())
    etat = appel(admin, "/api/etat")[1]
    assert etat["admin"] is True and etat["racine"] == os.path.realpath(PROJ), etat

    # 1. Création d'invités (administrateur seulement)
    code, marie_info, _ = appel(admin, "/api/utilisateurs", {"nom": "Marie"})
    assert code == 200 and "?jeton=" in marie_info["lien"], marie_info
    assert appel(admin, "/api/utilisateurs", {"nom": "marie"})[0] == 400, "nom déjà pris (sans tenir compte des majuscules)"
    for mauvais in ("", "../x", "admin"):
        assert appel(admin, "/api/utilisateurs", {"nom": mauvais})[0] == 400, mauvais
    fichier = os.path.join(HOME_TEST, ".config/morpheus/utilisateurs.json")
    assert oct(os.stat(fichier).st_mode)[-3:] == "600"
    assert [u["nom"] for u in appel(admin, "/api/utilisateurs")[1]["utilisateurs"]] == ["Marie"]

    # 2. Marie se connecte avec son lien : son espace, pas de paramètres
    marie = connexion(marie_info["lien"].split("jeton=")[1])
    etat = appel(marie, "/api/etat")[1]
    assert etat["utilisateur"] == "Marie" and etat["admin"] is False and etat["discussions"] is True, etat
    assert etat["racine"].startswith(os.path.join(PARTAGES, "Marie")), etat
    for chemin in ("/api/config", "/api/utilisateurs"):
        assert appel(marie, chemin)[0] == 403, chemin
    assert appel(marie, "/api/utilisateurs", {"nom": "Pirate"})[0] == 403
    assert appel(marie, "/api/config", {"modele": "x"})[0] == 403

    # 3. Cloisonnement des projets
    assert appel(marie, "/api/projets", {"nom": "jardin"})[0] == 200
    jardin = os.path.join(PARTAGES, "Marie", "jardin")
    assert os.path.isdir(jardin) and appel(marie, "/api/etat")[1]["racine"] == jardin
    projets_admin = [p["chemin"] for p in appel(admin, "/api/projets")[1]["projets"]]
    assert not any(c.startswith(PARTAGES) for c in projets_admin), projets_admin
    assert appel(admin, "/api/projet", {"chemin": jardin})[0] == 400, "l'admin n'ouvre pas les projets de Marie"
    assert appel(marie, "/api/projet", {"chemin": os.path.realpath(PROJ)})[0] == 400, "Marie n'ouvre pas les dossiers de l'admin"
    assert appel(marie, "/api/fichier?chemin=" + os.path.join(os.path.realpath(PROJ), "x"))[0] == 400
    assert appel(admin, "/api/etat")[1]["racine"] == os.path.realpath(PROJ), "l'admin n'a pas bougé"

    # 4. File d'attente : l'admin attend une validation, Marie envoie une demande → elle attend son tour
    faux.SCRIPT += [faux.ol("", [T("write_file", {"path": "a.txt", "content": "a\n"})]),
                    faux.ol("Fichier a.txt créé."),
                    faux.ol("Bonjour Marie !")]
    n_admin = len(evenements(admin))
    assert appel(admin, "/api/message", {"texte": "crée a.txt"})[0] == 200
    evs = attendre(admin, lambda e: any(x["type"] == "question" for x in e[n_admin:]))
    question = [x for x in evs[n_admin:] if x["type"] == "question"][-1]
    n_marie = len(evenements(marie))
    assert appel(marie, "/api/message", {"texte": "dis bonjour ?"})[0] == 200
    evs_m = attendre(marie, lambda e: any(x["type"] == "attente" for x in e[n_marie:]))
    assert [x["position"] for x in evs_m[n_marie:] if x["type"] == "attente"][-1] == 1
    assert [x["texte"] for x in evs_m[n_marie:] if x["type"] == "utilisateur"] == ["dis bonjour ?"], \
        "le message de Marie s'affiche tout de suite"
    assert appel(marie, "/api/message", {"texte": "encore ?"})[0] == 409, "une seule demande à la fois par personne"
    assert not any(x["type"] == "question" for x in evs_m), "Marie ne voit pas les validations de l'admin"
    time.sleep(0.5)
    assert not any(x["type"] == "texte" for x in evenements(marie)[n_marie:]), "Marie attend son tour"
    appel(admin, "/api/reponse", {"id": question["id"], "reponse": "o"})
    evs_m = attendre(marie, lambda e: any(x["type"] == "fin" for x in e[n_marie:]))
    assert "".join(x["texte"] for x in evs_m[n_marie:] if x["type"] == "texte") == "Bonjour Marie !"
    assert os.path.exists(os.path.join(PROJ, "a.txt")) and not os.path.exists(os.path.join(jardin, "a.txt"))
    assert not any(x.get("texte") == "Bonjour Marie !" for x in evenements(admin)), "l'admin ne voit pas le chat de Marie"

    # 5. Conversations séparées
    titres = lambda c: [v["titre"] for v in appel(c, "/api/conversations")[1]["conversations"]]
    assert titres(marie) == ["dis bonjour ?"] and "dis bonjour ?" not in titres(admin)

    # 6. Retirer sa demande de la file
    faux.SCRIPT += [faux.ol("", [T("write_file", {"path": "b.txt", "content": "b\n"})]), faux.ol("Refus noté, c'est refusé.")]
    n_admin = len(evenements(admin))
    appel(admin, "/api/message", {"texte": "crée b.txt"})
    evs = attendre(admin, lambda e: any(x["type"] == "question" for x in e[n_admin:]))
    question = [x for x in evs[n_admin:] if x["type"] == "question"][-1]
    n_marie = len(evenements(marie))
    appel(marie, "/api/message", {"texte": "une autre question ?"})
    attendre(marie, lambda e: any(x["type"] == "attente" for x in e[n_marie:]))
    assert appel(marie, "/api/arreter", {})[1]["ok"] is True
    attendre(marie, lambda e: any(x["type"] == "fin" for x in e[n_marie:]))
    assert appel(marie, "/api/etat")[1]["occupe"] is False
    appel(admin, "/api/reponse", {"id": question["id"], "reponse": "n", "consigne": ""})
    attendre(admin, lambda e: any(x["type"] == "fin" for x in e[question["n"]:]))
    # Refus sans consigne : la tâche de l'admin s'arrête sans rappeler le modèle ; et la demande retirée
    # de Marie n'est jamais partie : la réponse scriptée restante n'a donc pas été consommée.
    assert faux.SCRIPT == [faux.ol("Refus noté, c'est refusé.")], faux.SCRIPT
    faux.SCRIPT.clear()

    # 7. Modèle propre à l'invité (l'administrateur garde le sien)
    assert appel(marie, "/api/modele", {"modele": "autre:7b"})[0] == 200
    assert appel(marie, "/api/etat")[1]["modele"] == "autre:7b"
    assert appel(admin, "/api/etat")[1]["modele"] == "qwen3-coder-next"
    config = os.path.join(HOME_TEST, ".config/morpheus/config.json")
    assert json.load(open(config)).get("modele") in (None, "qwen3-coder-next")
    faux.SCRIPT.append(faux.ol("Réponse du petit modèle."))
    n_marie = len(evenements(marie))
    appel(marie, "/api/message", {"texte": "qui es-tu ?"})
    attendre(marie, lambda e: any(x["type"] == "fin" for x in e[n_marie:]))
    assert faux.RECUS[-1][1]["model"] == "autre:7b"

    # 8. Révocation : le lien de Marie ne marche plus, ses fichiers restent
    assert appel(admin, "/api/utilisateurs/revoquer", {"nom": "Marie"})[0] == 200
    assert appel(marie, "/api/etat")[0] == 401
    assert os.path.isdir(jardin)
    print("OK : invités avec lien personnel, espaces séparés, file d'attente, modèle par invité, révocation")
finally:
    serveur.terminate()
    try:
        sortie = serveur.communicate(timeout=5)[0]
    except subprocess.TimeoutExpired:
        serveur.kill()
        sortie = serveur.communicate()[0]
    print(sortie[-3000:])
