import os, sys, glob, json, subprocess
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
sys.path.insert(0, BASE); import faux
faux.lancer(18434)
T = lambda n, a: {"function": {"name": n, "arguments": a}}
env = dict(os.environ, HOME=HOME_TEST)
os.makedirs(HOME_TEST + "/.config/morpheus", exist_ok=True)
json.dump({"url_searxng": "http://127.0.0.1:18434"}, open(HOME_TEST + "/.config/morpheus/config.json", "w"))

# Session réelle observée : le modèle a relancé 45 fois la même recherche web jusqu'à la
# limite de 50 étapes. MORPHEUS doit : rappeler les liens trouvés (à ouvrir avec
# web_fetch), puis, si le modèle ignore deux notes anti-répétition, lui retirer les
# outils pour l'obliger à conclure en texte.
recherche = T("web_search", {"query": "operation ananas"})
faux.SCRIPT += [faux.ol("", [recherche])]                 # vraie recherche
faux.SCRIPT += [faux.ol("", [recherche]) for _ in range(6)]  # répétitions obstinées
faux.SCRIPT += [faux.ol("Je n'ai pas trouvé d'information fiable sur ce sujet.")]
entree = "cherche ce qu'est l'opération ananas\n/quitter\n"
p = subprocess.run([sys.executable, MORPHEUS], input=entree, capture_output=True, text=True,
                   timeout=90, cwd=PROJ, env=env)
print(p.stdout)
print(p.stderr[-2000:])

assert "Limite de 50 étapes" not in p.stdout
assert "réponse demandée sans outils" in p.stdout, "MORPHEUS doit annoncer qu'il retire les outils"
assert "Je n'ai pas trouvé d'information fiable" in p.stdout
dernier = faux.RECUS[-1][1]
assert "tools" not in dernier, "le dernier appel au modèle doit se faire sans outils"
assert "tools" in faux.RECUS[-2][1], "les appels précédents gardent les outils"
assert not faux.SCRIPT, "toutes les réponses scriptées doivent avoir été consommées"

fichiers = sorted(glob.glob(os.path.join(HOME_TEST, ".local/share/morpheus/sessions/*.jsonl")))
lignes = [json.loads(l) for l in open(fichiers[-1], encoding="utf-8") if l.strip()]
bloques = [m["content"] for m in lignes if m.get("role") == "tool" and "Recherche identique" in m["content"]]
assert bloques and "https://a.example" in bloques[0] and "web_fetch" in bloques[0], \
    "une recherche répétée doit rappeler les liens trouvés et proposer web_fetch"
print("OK : recherche répétée -> liens rappelés, puis réponse forcée sans outils")
