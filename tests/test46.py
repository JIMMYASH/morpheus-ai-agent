import os, sys, json, time, stat, threading, subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
sys.path.insert(0, BASE); import faux
faux.lancer(18434)
T = lambda n, a: {"function": {"name": n, "arguments": a}}
PORT_TG = 18091
env = dict(os.environ, HOME=HOME_TEST, XDG_DATA_HOME=os.path.join(HOME_TEST, ".local/share"),
           MORPHEUS_URL_TELEGRAM=f"http://127.0.0.1:{PORT_TG}")
env.pop("MORPHEUS_MODE", None)                    # mode Chat au démarrage, comme en vrai
JETON = "123456:" + "A" * 30
MOI, INTRUS = 42, 99

# Discuter avec MORPHEUS par Telegram : assistant « --telegram », bot réservé au compte enregistré,
# réponses renvoyées, validation par bouton ou au clavier. Un faux serveur Telegram remplace le vrai.
MISES_A_JOUR, ENVOYES, verrou = [], [], threading.Lock()
compteur = [0]


def ajouter(maj):
    with verrou:
        compteur[0] += 1
        MISES_A_JOUR.append(dict(maj, update_id=compteur[0]))


def message(expediteur, texte):
    ajouter({"message": {"message_id": compteur[0], "date": int(time.time()), "text": texte,
                         "from": {"id": expediteur, "first_name": "Jean" if expediteur == MOI else "Intrus"},
                         "chat": {"id": expediteur, "type": "private"}}})


def bouton(expediteur, donnees):
    ajouter({"callback_query": {"id": str(compteur[0]), "data": donnees, "from": {"id": expediteur}}})


class FauxTelegram(BaseHTTPRequestHandler):
    def do_POST(s):
        corps = json.loads(s.rfile.read(int(s.headers.get("Content-Length") or 0)) or b"{}")
        jeton, methode = s.path.split("/")[1][3:], s.path.split("/")[2]
        if jeton != JETON:
            s.send_response(401); s.end_headers(); s.wfile.write(b'{"ok":false,"description":"Unauthorized"}'); return
        resultat = True
        if methode == "getMe":
            resultat = {"id": 1, "is_bot": True, "username": "morpheus_test_bot"}
        elif methode == "getUpdates":
            for _ in range(10):                       # attente courte (le vrai Telegram attend jusqu'à 25 s)
                with verrou:
                    prets = [m for m in MISES_A_JOUR if m["update_id"] >= corps.get("offset", 0)]
                if prets or not corps.get("timeout"):
                    break
                time.sleep(0.1)
            resultat = prets
        elif methode in ("sendMessage", "editMessageReplyMarkup", "answerCallbackQuery"):
            with verrou:
                ENVOYES.append((methode, corps))
                resultat = {"message_id": 1000 + len(ENVOYES)}
        s.send_response(200); s.end_headers()
        s.wfile.write(json.dumps({"ok": True, "result": resultat}).encode())

    def log_message(s, *a):
        pass


serveur_tg = ThreadingHTTPServer(("127.0.0.1", PORT_TG), FauxTelegram)
threading.Thread(target=serveur_tg.serve_forever, daemon=True).start()


def attendre(condition, delai=10, quoi=""):
    for _ in range(int(delai * 10)):
        with verrou:
            envoyes = list(ENVOYES)
        trouve = [c for m, c in envoyes if condition(m, c)]
        if trouve:
            return trouve[-1]
        time.sleep(0.1)
    raise AssertionError(f"rien reçu : {quoi}\n{json.dumps(ENVOYES, ensure_ascii=False, indent=1)[-3000:]}")


def texte_recu(morceau):
    return lambda m, c: m == "sendMessage" and morceau in c.get("text", "")


# --- 1. Assistant de configuration : l'intrus est refusé, le bon compte est enregistré ---
message(INTRUS, "coucou")
message(MOI, "c'est moi")
config = subprocess.run([sys.executable, MORPHEUS, "--telegram"], input=f"{JETON}\nn\no\n", cwd=PROJ, env=env,
                        capture_output=True, text=True, timeout=30)
print(config.stdout, config.stderr)
fichier = os.path.join(HOME_TEST, ".config/morpheus/telegram.json")
assert "@morpheus_test_bot" in config.stdout and "C'est fait" in config.stdout, config.stdout
assert json.load(open(fichier)) == {"jeton": JETON, "utilisateur": MOI}
assert stat.S_IMODE(os.stat(fichier).st_mode) == 0o600, "le jeton doit être lisible par toi seul"
assert attendre(texte_recu("relié à ton compte"))["chat_id"] == MOI
with verrou:
    MISES_A_JOUR.clear(); ENVOYES.clear()

# --- 2. Le bot dans le serveur web ---
PORT = 18772
serveur = subprocess.Popen([sys.executable, MORPHEUS, "--web", "--port", str(PORT), "--hote", "127.0.0.1"],
                           cwd=PROJ, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
try:
    time.sleep(1.5)
    # Un inconnu est ignoré : aucune réponse, aucun appel au modèle
    n_modele = len(faux.RECUS)
    message(INTRUS, "lis mes fichiers")
    time.sleep(1.5)
    assert len(faux.RECUS) == n_modele, "le message d'un inconnu ne doit pas aller au modèle"
    assert not [c for m, c in ENVOYES if c.get("chat_id") == INTRUS], "aucune réponse à un inconnu"

    # Une question : la réponse revient, mise en forme
    faux.SCRIPT.append(faux.ol("**Salut** depuis `MORPHEUS`."))
    message(MOI, "bonjour")
    r = attendre(texte_recu("Salut"), quoi="réponse du modèle")
    assert r["parse_mode"] == "HTML" and "<b>Salut</b>" in r["text"] and "<code>MORPHEUS</code>" in r["text"], r
    assert faux.RECUS[-1][1]["messages"][-1]["content"].endswith("bonjour")

    etat = attendre(texte_recu("Projet :"), quoi="/etat") if message(MOI, "/etat") is None else None
    assert "Projet : Discussions" in etat["text"], "Telegram démarre hors projet, pas dans le projet du navigateur"
    assert "Mode : Chat" in etat["text"], "mode Chat par défaut"

    # Ouvrir le projet par /projets et son bouton
    message(MOI, "/projets")
    p = attendre(lambda m, c: m == "sendMessage" and "Choisis le projet" in c.get("text", ""), quoi="liste des projets")
    lignes = [l[0] for l in p["reply_markup"]["inline_keyboard"]]
    assert lignes[0]["text"] == "💬 Discussions ✔", lignes
    projet = [b for b in lignes if os.path.basename(PROJ) in b["text"]]
    assert projet and projet[0]["text"].startswith("📁"), lignes
    bouton(MOI, projet[0]["callback_data"])
    attendre(texte_recu("Projet ouvert"), quoi="projet ouvert")
    message(MOI, "/dev")
    attendre(texte_recu("Mode développeur"), quoi="passage en mode développeur")

    # Écriture validée par le bouton « Oui » (un clic de l'intrus est ignoré)
    faux.SCRIPT.extend([faux.ol("", [T("write_file", {"path": "note.txt", "content": "coucou\n"})]),
                        faux.ol("Fichier créé.")])
    message(MOI, "crée note.txt")
    q = attendre(lambda m, c: m == "sendMessage" and c.get("text", "").startswith("❓"), quoi="question avec boutons")
    boutons = [b["callback_data"] for b in q["reply_markup"]["inline_keyboard"][0]]
    assert boutons[0].endswith(":o") and boutons[-1].endswith(":n"), boutons
    bouton(INTRUS, boutons[0])
    time.sleep(1)
    assert not os.path.exists(os.path.join(PROJ, "note.txt")), "le clic d'un inconnu ne valide rien"
    bouton(MOI, boutons[0])
    attendre(texte_recu("Fichier créé."), quoi="fin de la demande")
    assert open(os.path.join(PROJ, "note.txt")).read() == "coucou\n"
    attendre(lambda m, c: m == "editMessageReplyMarkup" and "Oui" in json.dumps(c, ensure_ascii=False),
             quoi="boutons remplacés par la réponse")

    # Refus au clavier, avec une consigne
    faux.SCRIPT.extend([faux.ol("", [T("write_file", {"path": "autre.txt", "content": "x\n"})]),
                        faux.ol("Tu as refusé : je n'écris rien.")])
    n = len(ENVOYES)
    message(MOI, "crée autre.txt")
    attendre(lambda m, c: m == "sendMessage" and c.get("text", "").startswith("❓") and ENVOYES.index((m, c)) >= n, quoi="2e question")
    message(MOI, "pas maintenant")
    attendre(texte_recu("je n'écris rien"), quoi="fin après refus")
    assert not os.path.exists(os.path.join(PROJ, "autre.txt"))
    assert "pas maintenant" in json.dumps(faux.RECUS[-1][1]["messages"], ensure_ascii=False), "la consigne arrive au modèle"

    # /projets marque le projet ouvert ; /start repart hors projet
    n = len(ENVOYES)
    message(MOI, "/projets")
    p = attendre(lambda m, c: m == "sendMessage" and "Choisis" in c.get("text", "") and ENVOYES.index((m, c)) >= n)
    assert any(l[0]["text"].startswith("📂") and l[0]["text"].endswith("✔") for l in p["reply_markup"]["inline_keyboard"])
    # /nouveauprojet : crée le projet dans ~/projets (avec git) et l'ouvre ; nom invalide ou déjà pris refusé
    message(MOI, "/nouveauprojet")
    attendre(texte_recu("Donne le nom du projet"))
    message(MOI, "/nouveauprojet ../evasion")
    attendre(texte_recu("Impossible de créer le projet"))
    message(MOI, "/nouveauprojet Mon Site")
    attendre(texte_recu("« Mon Site » créé et ouvert"), quoi="projet créé")
    dossier = os.path.join(HOME_TEST, "projets", "Mon Site")
    assert os.path.isdir(os.path.join(dossier, ".git")), "projet créé avec git"
    n = len(ENVOYES)
    message(MOI, "/etat")
    assert "Projet : Mon Site" in attendre(lambda m, c: texte_recu("Projet :")(m, c) and ENVOYES.index((m, c)) >= n)["text"]
    message(MOI, "/nouveauprojet Mon Site")
    attendre(texte_recu("existe déjà"))
    message(MOI, "/start")
    attendre(texte_recu("hors projet"), quoi="/start")
    n = len(ENVOYES)
    message(MOI, "/etat")
    assert "Projet : Discussions" in attendre(lambda m, c: texte_recu("Projet :")(m, c) and ENVOYES.index((m, c)) >= n)["text"]
    # Discussion Telegram supprimée depuis le navigateur : le bot repart sur une nouvelle conversation
    # (sinon il recréerait le fichier supprimé en continuant d'y écrire)
    faux.SCRIPT.append(faux.ol("Réponse hors projet."))
    message(MOI, "question hors projet")
    attendre(texte_recu("Réponse hors projet."))
    from urllib.request import Request, urlopen
    URL = f"http://127.0.0.1:{PORT}"
    cookie = [""]

    def appel(chemin, donnees=None):
        entetes = {"Content-Type": "application/json", "X-Morpheus": "1", "Cookie": cookie[0]}
        with urlopen(Request(URL + chemin, data=json.dumps(donnees).encode() if donnees is not None else None,
                             headers=entetes), timeout=10) as r:
            return json.loads(r.read() or b"{}"), r.headers
    jeton_web = open(os.path.join(HOME_TEST, ".config/morpheus/jeton_web")).read().strip()
    cookie[0] = appel("/api/connexion", {"jeton": jeton_web})[1]["Set-Cookie"].split(";")[0]
    discussions = [p for p in appel("/api/projets")[0]["projets"] if p["type"] == "discussions"][0]["chemin"]
    appel("/api/projet", {"chemin": discussions})
    convs = appel("/api/conversations")[0]["conversations"]
    cible = [c for c in convs if "question hors projet" in c["titre"]]
    assert cible, convs
    appel("/api/conversation/supprimer", {"id": cible[0]["id"]})
    journal = os.path.join(HOME_TEST, ".local/share/morpheus/sessions", cible[0]["id"] + ".jsonl")
    assert not os.path.exists(journal)
    faux.SCRIPT.append(faux.ol("Encore une réponse."))
    message(MOI, "et maintenant ?")
    attendre(texte_recu("Encore une réponse."))
    assert not os.path.exists(journal), "la conversation supprimée ne doit pas réapparaître"
    assert "question hors projet" not in json.dumps(faux.RECUS[-1][1]["messages"], ensure_ascii=False), \
        "le bot est reparti sur une nouvelle conversation"
    # /style : boutons des modes de conversation ; un appui change le mode
    message(MOI, "/style")
    st = attendre(lambda m, c: m == "sendMessage" and c.get("text", "").startswith("Mode de conversation"), quoi="/style")
    assert "🔍 Relecteur : Critique" in st["text"], "chaque mode est décrit"
    lignes = [l[0]["text"] for l in st["reply_markup"]["inline_keyboard"]]
    assert lignes[0] == "💬 Par défaut ✔" and "🎓 Expert" in lignes and "🪜 Pas à pas" in lignes and len(lignes) == 10, lignes
    bouton(MOI, "s:expert")
    attendre(texte_recu("Mode de conversation : Expert."), quoi="mode Expert")
    print("OK : Telegram")
finally:
    serveur.terminate()
    try:
        sortie = serveur.communicate(timeout=5)[0]
    except subprocess.TimeoutExpired:
        serveur.kill()
        sortie = serveur.communicate()[0]
    print(sortie[-3000:])
