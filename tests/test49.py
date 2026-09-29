import os, sys, json, time, subprocess
from urllib.request import Request, urlopen
from urllib.error import HTTPError
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]

# Claude Code dans l'interface web : proposé à l'administrateur, validations par boutons, arrêt,
# jamais utilisable par un invité (c'est l'abonnement de l'administrateur).
SCENARIOS = os.path.join(HOME_TEST, "scenarios.json")
JOURNAL = os.path.join(HOME_TEST, "faux_claude.jsonl")
env = dict(os.environ, HOME=HOME_TEST, MORPHEUS_CLAUDE=os.path.join(BASE, "faux_claude.py"),
           FAUX_CLAUDE_SCENARIOS=SCENARIOS, FAUX_CLAUDE_JOURNAL=JOURNAL)
open(JOURNAL, "w").close()
a = os.path.join(PROJ, "a.txt")
json.dump([[{"outil": "Write", "input": {"file_path": a, "content": "bonjour\n"}}, {"texte": "a.txt créé."}]],
          open(SCENARIOS, "w", encoding="utf-8"))
PORT = 18772
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
    return appel("", "/api/connexion", {"jeton": jeton})[2]["Set-Cookie"].split(";")[0]


def evenements(cookie):
    return appel(cookie, "/api/evenements?depuis=0")[1]["evenements"]


def attendre(cookie, condition, n=0):
    for _ in range(200):
        evs = evenements(cookie)
        if condition(evs[n:]):
            return evs[n:]
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
    assert "claude-code" in appel(admin, "/api/modeles")[1]["autres"], "Claude Code proposé à l'administrateur"
    assert appel(admin, "/api/modele", {"modele": "claude-code"})[0] == 200
    assert appel(admin, "/api/etat")[1]["modele"] == "claude-code"

    # Validation par boutons dans la page
    n = len(evenements(admin))
    appel(admin, "/api/message", {"texte": "crée a.txt"})
    evs = attendre(admin, lambda e: any(x["type"] == "question" for x in e), n)
    assert any(x["type"] == "diff" for x in evs), "aperçu dans le volet Modifications"
    question = [x for x in evs if x["type"] == "question"][-1]
    appel(admin, "/api/reponse", {"id": question["id"], "reponse": "o"})
    evs = attendre(admin, lambda e: any(x["type"] == "fin" for x in e), n)
    assert "".join(x["texte"] for x in evs if x["type"] == "texte") == "a.txt créé.", evs
    assert open(a).read() == "bonjour\n"

    # « Arrêter » : Claude Code et la commande qu'il a lancée sont arrêtés
    json.dump([[{"outil": "Bash", "input": {"command": "sleep 77"}}, {"texte": "jamais"}]],
              open(SCENARIOS, "w", encoding="utf-8"))
    n = len(evenements(admin))
    appel(admin, "/api/message", {"texte": "attends"})
    evs = attendre(admin, lambda e: any(x["type"] == "question" for x in e), n)
    appel(admin, "/api/reponse", {"id": [x for x in evs if x["type"] == "question"][-1]["id"], "reponse": "o"})
    en_route = lambda: subprocess.run(["pgrep", "-f", "^sleep 77$"], capture_output=True).returncode == 0
    for _ in range(50):
        if en_route():
            break
        time.sleep(0.1)
    assert en_route(), "la commande doit avoir démarré"
    assert appel(admin, "/api/arreter", {})[1]["ok"] is True
    evs = attendre(admin, lambda e: any(x["type"] == "fin" for x in e), n)
    time.sleep(0.3)
    assert not en_route(), "la commande lancée par Claude Code doit être arrêtée"
    assert not any("jamais" in x.get("texte", "") for x in evs)

    # Invité : Claude Code ni proposé, ni sélectionnable, ni utilisé même s'il est le modèle par défaut
    code, info, _ = appel(admin, "/api/utilisateurs", {"nom": "Marie"})
    assert code == 200
    marie = connexion(info["lien"].split("jeton=")[1])
    assert not any(m.startswith("claude-code") for m in appel(marie, "/api/modeles")[1]["autres"])
    code, reponse, _ = appel(marie, "/api/modele", {"modele": "claude-code"})
    assert code == 400 and "administrateur" in reponse.get("erreur", json.dumps(reponse)), reponse
    lancements = sum(1 for l in open(JOURNAL) if '"arguments"' in l)
    n = len(evenements(marie))
    appel(marie, "/api/message", {"texte": "bonjour ?"})
    evs = attendre(marie, lambda e: any(x["type"] == "fin" for x in e), n)
    assert any("réservé à l'administrateur" in x.get("texte", "") for x in evs), evs
    assert sum(1 for l in open(JOURNAL) if '"arguments"' in l) == lancements, "Claude Code jamais lancé pour un invité"

    # Mode auto : l'administrateur l'active (case « Auto »), un invité ne peut pas
    n = len(evenements(admin))
    appel(admin, "/api/message", {"texte": "/auto"})
    evs = attendre(admin, lambda e: any(x["type"] == "fin" for x in e), n)
    assert [x for x in evs if x["type"] == "fin"][-1]["auto"] is True and appel(admin, "/api/etat")[1]["auto"] is True
    n = len(evenements(marie))
    appel(marie, "/api/message", {"texte": "/auto on"})
    evs = attendre(marie, lambda e: any(x["type"] == "fin" for x in e), n)
    assert any("réservé à l'administrateur" in x.get("texte", "") for x in evs) and appel(marie, "/api/etat")[1]["auto"] is False
    print("OK")
finally:
    serveur.terminate()
    print(serveur.communicate(timeout=10)[0][-3000:])
