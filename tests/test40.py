import os, sys, subprocess
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
sys.path.insert(0, BASE); import faux
faux.lancer(18434)
T = lambda n, a: {"function": {"name": n, "arguments": a}}

# todo_write accepte les formats de Kimi : texte de la tâche dans « label » ou « title »,
# liste écrite à la façon Python, une seule tâche sans liste ; et signale une liste illisible.
faux.SCRIPT += [
    faux.ol("", [T("todo_write", {"todos": [{"id": 1, "label": "Lire le code", "status": "in_progress"},
                                             {"id": 2, "title": "Corriger le bug", "status": "pending"}]})]),
    faux.ol("", [T("todo_write", {"todos": "[{'id': 1, 'label': 'Lire le code', 'status': 'completed'}, "
                                            "{'id': 2, 'label': 'Corriger le bug', 'status': 'completed'}]"})]),
    faux.ol("", [T("todo_write", {"todos": {"Title": "Tâche unique", "Status": "done"}})]),
    faux.ol("", [T("todo_write", {"todos": [{"id": 1, "status": "pending"}]})]),
    faux.ol("C'est fini."),
]
p = subprocess.run([sys.executable, MORPHEUS], input="fais le travail\n/quitter\n", capture_output=True,
                   text=True, timeout=60, cwd=PROJ, env=dict(os.environ, HOME=HOME_TEST))
print(p.stdout); print(p.stderr[-3000:])

resultats = [m["content"] for _, corps in faux.RECUS for m in corps.get("messages", []) if m.get("role") == "tool"]
resultats = list(dict.fromkeys(resultats))      # chaque requête renvoie tout l'historique
print(resultats)
assert "◐ Lire le code" in resultats[0] and "☐ Corriger le bug" in resultats[0], resultats[0]
assert "☑ Lire le code" in resultats[1] and "☑ Corriger le bug" in resultats[1], resultats[1]
assert "☑ Tâche unique" in resultats[2], resultats[2]
assert resultats[3].startswith("Erreur : aucune tâche lisible"), resultats[3]
assert len(faux.SCRIPT) == 0, "réponses non consommées"

# Sortie redirigée (morpheus -p > fichier) : pas d'indicateur d'attente « … » collé aux lignes.
faux.SCRIPT += [faux.ol("", [T("list_dir", {"path": "."})]), faux.ol("Dossier vide.")]
p = subprocess.run([sys.executable, MORPHEUS, "-p", "que contient le dossier ?"], capture_output=True, text=True,
                   timeout=60, cwd=PROJ, env=dict(os.environ, HOME=HOME_TEST), stdin=subprocess.DEVNULL)
print(p.stdout)
assert "Dossier vide." in p.stdout and "…" not in p.stdout, p.stdout
print("OK")
