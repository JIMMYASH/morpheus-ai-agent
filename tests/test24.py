import os, sys, glob, json
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
import subprocess, sys, os
sys.path.insert(0, BASE); import faux
faux.lancer(18434)
T = lambda n, a: {"function": {"name": n, "arguments": a}}
env = dict(os.environ, HOME=HOME_TEST)

# Reproduit un bug observé avec qwen3-coder:30b : le modèle répète le même
# appel d'outil déjà fait (ignoré via « déjà fait »), tout en annonçant sans
# cesse une autre action qu'il n'exécute jamais. Comme l'appel répété compte
# quand même comme « le modèle a utilisé un outil », le rappel existant pour
# une action annoncée-mais-pas-exécutée ne se déclenchait jamais (il ne se
# déclenche que si le tour n'a AUCUN appel d'outil) : la conversation
# tournait en rond jusqu'à la limite de 50 étapes.
faux.SCRIPT += [
    faux.ol("", [T("list_dir", {"path": "."})]),                              # appel réel
    faux.ol("Je vais lire le fichier.", [T("list_dir", {"path": "."})]),      # répétition 1 (ignorée)
    faux.ol("Je vais lire le fichier.", [T("list_dir", {"path": "."})]),      # répétition 2 (ignorée) -> doit déclencher la note
    faux.ol("Terminé."),                                                      # doit pouvoir conclure après la note
]
entree = "regarde le dossier et dis-moi ce qu'il contient\n/quitter\n"
p = subprocess.run([sys.executable, MORPHEUS], input=entree, capture_output=True, text=True,
                    timeout=60, cwd=PROJ, env=env)
print(p.stdout)
print(p.stderr[-2000:])

assert "Limite de 50 étapes" not in p.stdout, "la note anti-répétition doit permettre de conclure avant la limite"
assert "Terminé." in p.stdout, "le modèle doit avoir pu conclure après la note"

fichiers = sorted(glob.glob(os.path.join(HOME_TEST, ".local/share/morpheus/sessions/*.jsonl")))
assert fichiers, "un journal de session doit avoir été écrit"
lignes = [json.loads(l) for l in open(fichiers[-1], encoding="utf-8") if l.strip()]
notes = [m for m in lignes if m.get("role") == "user" and "répètes des appels déjà faits" in m.get("content", "")]
assert notes, "une note anti-répétition doit avoir été injectée après deux tours sans rien de nouveau"
print("OK : une note anti-répétition est injectée quand le modèle ne fait que répéter un appel déjà fait")
