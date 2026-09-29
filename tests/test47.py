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
CONFIG = os.path.join(HOME_TEST, ".config/morpheus/config.json")

# Modes de conversation (Par défaut / Expert / Pédagogique) : consignes dans le prompt système,
# rappel joint à la demande suivante, choix mémorisé pour le prochain lancement.


def systeme(i=-1):
    return faux.RECUS[i][1]["messages"][0]["content"]


def derniere_demande(i=-1):
    return [m for m in faux.RECUS[i][1]["messages"] if m["role"] == "user"][-1]["content"]


# --- Terminal ---
faux.SCRIPT += [faux.ol("Réponse 1."), faux.ol("Réponse 2.")]
p = subprocess.run([sys.executable, MORPHEUS], input="question 1\n/style expert\nquestion 2\n/style\n/style farfelu\n/quitter\n",
                   capture_output=True, text=True, timeout=60, cwd=PROJ, env=env)
print(p.stdout[-2000:], p.stderr[-800:])
assert "« Par défaut »" in systeme(0) and "Pas de bloc de code" in systeme(0), "mode par défaut au départ"
assert "N'invente jamais de faits" in systeme(0) and "propose de passer en mode développeur" in systeme(0), "règles communes"
assert "Mode de conversation : Expert." in p.stdout
assert "« Expert »" in systeme(1) and "Suppose un public averti" in systeme(1) and "Pas de bloc de code" not in systeme(1), \
    "le prompt système suit le mode choisi"
assert "[Mode de conversation « Expert » désormais" in derniere_demande(1), "rappel joint à la demande suivante"
assert "Mode de conversation : Expert. Les modes :" in p.stdout and "/style pas_a_pas" in p.stdout \
    and "🔍 Relecteur — Critique" in p.stdout, "/style seul affiche le mode et la liste"
assert "Mode de conversation inconnu : farfelu" in p.stdout
assert json.load(open(CONFIG))["style"] == "expert", "le choix est mémorisé"

faux.SCRIPT.append(faux.ol("Réponse 3."))
subprocess.run([sys.executable, MORPHEUS], input="question 3\n/quitter\n", capture_output=True, text=True,
               timeout=60, cwd=PROJ, env=env)
assert "« Expert »" in systeme() and "désormais" not in derniere_demande(), "au lancement suivant : Expert, sans rappel"

# Nouveaux modes (nom avec accents et espaces accepté) et modes personnels de ~/.config/morpheus/modes.json
with open(os.path.join(HOME_TEST, ".config/morpheus/modes.json"), "w", encoding="utf-8") as f:
    json.dump({"Juriste": {"icone": "📜", "description": "Cite les textes de loi", "consignes": ["Cite l'article de loi exact."]},
               "Poète": "Réponds en alexandrins.", "Expert": ["ignoré : un mode intégré garde son nom"],
               "Vide": []}, f, ensure_ascii=False)
faux.SCRIPT += [faux.ol("Étape 1."), faux.ol("Vu."), faux.ol("Rime.")]
p = subprocess.run([sys.executable, MORPHEUS], input="/style Pas à pas\nq4\n/style juriste\nq5\n/style poete\nq6\n/style\n/quitter\n",
                   capture_output=True, text=True, timeout=60, cwd=PROJ, env=env)
print(p.stdout[-1500:])
assert "Mode de conversation : Pas à pas." in p.stdout
assert "« Pas à pas »" in systeme(-3) and "étapes numérotées" in systeme(-3)
assert "« Juriste »" in systeme(-2) and "Cite l'article de loi exact." in systeme(-2)
assert "« Poète »" in systeme(-1) and "Réponds en alexandrins." in systeme(-1) and "N'invente jamais de faits" in systeme(-1), \
    "les règles communes s'appliquent aussi aux modes personnels"
assert "/style juriste" in p.stdout and "📜 Juriste — Cite les textes de loi" in p.stdout and "✨ Poète" in p.stdout
assert "ignoré" not in p.stdout and "/style vide" not in p.stdout
assert json.load(open(CONFIG))["style"] == "poete"
os.remove(os.path.join(HOME_TEST, ".config/morpheus/modes.json"))
faux.SCRIPT.append(faux.ol("Réponse 7."))
subprocess.run([sys.executable, MORPHEUS], input="/style expert\nq7\n/quitter\n", capture_output=True, text=True,
               timeout=60, cwd=PROJ, env=env)

# --- Interface web : menu déroulant (/api/style) et commande /style ---
PORT = 18773
URL = f"http://127.0.0.1:{PORT}"
serveur = subprocess.Popen([sys.executable, MORPHEUS, "--web", "--port", str(PORT), "--hote", "127.0.0.1"],
                           cwd=PROJ, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
COOKIE = ""


def appel(chemin, donnees=None):
    entetes = {"Content-Type": "application/json", "X-Morpheus": "1", "Cookie": COOKIE}
    try:
        with urlopen(Request(URL + chemin, data=json.dumps(donnees).encode() if donnees is not None else None,
                             headers=entetes), timeout=10) as r:
            return r.status, json.loads(r.read() or b"{}"), r.headers
    except HTTPError as e:
        return e.code, json.loads(e.read() or b"{}"), e.headers


def attendre_fin(n0):
    for _ in range(100):
        nouveaux = appel("/api/evenements?depuis=0")[1]["evenements"][n0:]
        types = [e["type"] for e in nouveaux]
        if "debut" in types and "fin" in types[types.index("debut"):]:
            return nouveaux
        time.sleep(0.1)
    raise AssertionError("pas de fin")


def envoyer(texte, reponses=()):
    n0 = len(appel("/api/evenements?depuis=0")[1]["evenements"])
    faux.SCRIPT.extend(reponses)
    assert appel("/api/message", {"texte": texte})[0] == 200
    return attendre_fin(n0)


try:
    for _ in range(50):
        try:
            page = urlopen(URL + "/", timeout=1).read().decode()
            break
        except OSError:
            time.sleep(0.2)
    assert 'id="menu-style"' in page and 'class="fleche">▼' in page and "choix-style" not in page, \
        "menu des modes dans la ligne de saisie, avec sa flèche"
    assert page.index('id="menu-style"') < page.index('id="saisie"'), "juste avant la zone de saisie"
    jeton = open(os.path.join(HOME_TEST, ".config/morpheus/jeton_web")).read().strip()
    COOKIE = appel("/api/connexion", {"jeton": jeton})[2]["Set-Cookie"].split(";")[0]

    code, rep, _ = appel("/api/style", {"style": "pedagogique"})
    assert code == 200 and rep["style"] == "pedagogique", rep
    assert appel("/api/style", {"style": "farfelu"})[0] == 400, "mode inconnu refusé"
    evts = envoyer("explique les listes", [faux.ol("Une liste, c'est comme une étagère.")])
    assert "« Pédagogique »" in systeme() and "analogies simples" in systeme()
    assert "[Mode de conversation « Pédagogique » désormais" in derniere_demande()
    assert json.load(open(CONFIG))["style"] == "pedagogique"
    fin = [e for e in evts if e["type"] == "fin"][-1]
    assert fin["style"] == "pedagogique", "la page connaît le mode"
    assert [m["cle"] for m in fin["styles"]][:3] == ["defaut", "synthese", "expert"] and len(fin["styles"]) == 10, fin["styles"]
    assert all(m["description"] and m["icone"] for m in fin["styles"])

    evts = envoyer("/style défaut")
    assert any("Mode de conversation : Par défaut." in e.get("texte", "") for e in evts), evts
    assert [e for e in evts if e["type"] == "infos"][-1]["style"] == "defaut", "le menu suit la commande"
    envoyer("et les dictionnaires ?", [faux.ol("Des paires clé-valeur.")])
    assert "« Par défaut »" in systeme() and "« Pédagogique »" not in systeme()
    print("OK : modes de conversation")
finally:
    serveur.terminate()
    try:
        sortie = serveur.communicate(timeout=5)[0]
    except subprocess.TimeoutExpired:
        serveur.kill()
        sortie = serveur.communicate()[0]
    print(sortie[-2000:])
