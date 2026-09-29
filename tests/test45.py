import os, sys, time, subprocess
from urllib.request import urlopen
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
env = dict(os.environ, HOME=HOME_TEST, XDG_DATA_HOME=os.path.join(HOME_TEST, ".local/share"))

# Interface web : le bouton « Nouvelle conversation » est en haut de la barre (sous « Nouveau projet »),
# au-dessus de la liste des projets, et non plus au milieu de la liste sous le projet ouvert.
PORT = 18771
serveur = subprocess.Popen([sys.executable, MORPHEUS, "--web", "--port", str(PORT), "--hote", "127.0.0.1"],
                           cwd=PROJ, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
try:
    page = None
    for _ in range(50):
        try:
            with urlopen(f"http://127.0.0.1:{PORT}/", timeout=5) as r:
                page = r.read().decode("utf-8")
            break
        except OSError:
            time.sleep(0.2)
    assert page, "la page web ne répond pas"
    assert page.count(">Nouvelle conversation</button>") == 1, "le bouton doit exister une seule fois"
    assert '<button id="btn-nouveau-projet">Nouveau projet</button>' in page, "« Nouveau projet » : même style, sans « + »"
    assert '<button id="btn-nouvelle-conv" title="Nouvelle conversation dans le projet ouvert">Nouvelle conversation</button>' in page
    i_projet = page.index('id="btn-nouveau-projet"')
    i_conv = page.index('id="btn-nouvelle-conv"')
    i_liste = page.index('<ul id="liste-projets">')
    assert i_projet < i_conv < i_liste, "le bouton doit être entre « Nouveau projet » et la liste des projets"
    assert "data-nouvelle" not in page, "plus de bouton « Nouvelle conversation » dans la liste des conversations"
    # Icône des projets : dossier ouvert pour le projet sélectionné, fermé pour les autres
    assert 'const icone = p.type === "discussions" ? "💬" : actif ? "📂" : "📁";' in page
    assert "${icone} ${echapper(p.nom)}" in page
    # Confirmations dans la page : confirm() / prompt() peuvent être bloqués par le navigateur sans rien afficher
    import re
    assert not re.search(r"\b(confirm|prompt|alert)\(", page), "utiliser confirmer() / demanderTexte()"
    assert '<dialog id="dlg-confirmer">' in page and page.count("await confirmer(") == 5
    print("OK : bouton Nouvelle conversation au-dessus des projets")
finally:
    serveur.terminate()
    try:
        sortie = serveur.communicate(timeout=5)[0]
    except subprocess.TimeoutExpired:
        serveur.kill()
        sortie = serveur.communicate()[0]
    print(sortie[-2000:])
