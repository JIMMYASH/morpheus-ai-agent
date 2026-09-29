import os, sys, subprocess, time
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
sys.path.insert(0, BASE); import faux
faux.lancer(18434)
T = lambda n, a: {"function": {"name": n, "arguments": a}}
env = dict(os.environ, HOME=HOME_TEST)

# Corrections trouvées à la relecture des améliorations précédentes.

# 1. Après l'arrêt d'une commande, un programme détaché du groupe (setsid) qui garde la
#    sortie ouverte ne doit pas bloquer MORPHEUS jusqu'à sa fin.
faux.SCRIPT += [faux.ol("", [T("bash", {"command": "setsid sleep 3142 & sleep 100", "timeout": 2})]),
                faux.ol("Commande arrêtée.")]
debut = time.time()
p = subprocess.run([sys.executable, MORPHEUS], input="lance la commande\no\n/quitter\n", capture_output=True,
                   text=True, timeout=90, cwd=PROJ, env=env)
duree = time.time() - debut
subprocess.run(["pkill", "-f", "^sleep 3142$"])
print(p.stdout[-1500:], p.stderr[-1500:])
assert "Délai dépassé" in p.stdout or "Commande arrêtée" in p.stdout
assert duree < 30, f"MORPHEUS est resté bloqué {duree:.0f} s après l'arrêt de la commande"

os.chdir(PROJ)
sys.path.insert(0, os.path.dirname(MORPHEUS)); import morpheus

# 2. Détection des serveurs : le programme lancé, pas un mot quelconque de la commande.
serveurs = ["npm run dev", "npm start", "cd front && npm run dev", "python3 -m http.server 8000",
            "python3 manage.py runserver", "FLASK_APP=app.py flask run", "uvicorn app:app --reload",
            "npx vite", "vite preview", "yarn dev", "streamlit run app.py", "npm run dev &"]
pas_serveurs = ["pip install uvicorn", "npm install vite", "vite build", "npx vite build",
                "grep uvicorn requirements.txt", "npm run develop", "npm test", "python3 app.py"]
erreurs = [c for c in serveurs if not morpheus.est_serveur(c)] + [c for c in pas_serveurs if morpheus.est_serveur(c)]
assert not erreurs, f"serveurs mal détectés : {erreurs}"

# 3. write_file sans path ne doit jamais deviner (risque d'écraser un fichier existant).
with open("notes.txt", "w", encoding="utf-8") as f:
    f.write("ancien\n")
morpheus.ETAT["fichiers_demande"] = ["notes.txt"]
resultat, _ = morpheus.executer_outil("write_file", {"content": "nouveau\n"})
assert resultat.startswith("Erreur : paramètre(s) manquant(s) : path"), resultat
assert open("notes.txt", encoding="utf-8").read() == "ancien\n"

# 4. Numéros de ligne : une ligne ajoutée sans numéro dans new_string ne doit pas empêcher
#    de retirer les numéros des autres lignes (sinon ils finissent dans le fichier).
with open("calcul.py", "w", encoding="utf-8") as f:
    f.write("def f():\n    return 1\n")
morpheus.FICHIERS_LUS.add(str(morpheus.resoudre("calcul.py")))
morpheus.PERMISSIONS.edition = lambda p: None
resultat = morpheus.outil_edit_file("calcul.py", "     1\tdef f():\n     2\t    return 1",
                                    "     1\tdef f():\n    x = 1\n     2\t    return x")
contenu = open("calcul.py", encoding="utf-8").read()
assert contenu == "def f():\n    x = 1\n    return x\n", f"contenu inattendu : {contenu!r}"
print("OK : arrêt borné, serveurs bien détectés, write_file jamais deviné, numéros retirés ligne par ligne")
