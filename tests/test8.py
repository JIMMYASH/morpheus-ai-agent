import os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
import subprocess,sys,os,json
sys.path.insert(0,BASE); import faux
faux.lancer(18434)
T=lambda n,a:{"function":{"name":n,"arguments":a}}
os.makedirs(HOME_TEST+"/.config/morpheus",exist_ok=True)
json.dump({"url_searxng":"http://127.0.0.1:18434"},open(HOME_TEST+"/.config/morpheus/config.json","w"))
open(HOME_TEST+"/.config/morpheus/MORPHEUS.md","w").write("Toujours tutoyer l'utilisateur.")
faux.SCRIPT+=[
 # demande 1 : liste de tâches, arrêt prématuré -> relance
 faux.ol("",[T("todo_write",{"todos":[{"content":"Créer a.py","status":"in_progress"},{"content":"Créer b.py","status":"pending"}]})]),
 faux.ol("",[T("write_file",{"path":"a.py","content":"print('a')\n"})]),
 faux.ol("a.py est créé."),                                  # -> relance tâches
 faux.ol("",[T("write_file",{"path":"b.py","content":"print('b')\n"})]),
 faux.ol("",[T("todo_write",{"todos":'[{"content":"Créer a.py","status":"completed"},{"content":"Créer b.py","status":"fait"}]'})]),
 faux.ol("Les deux fichiers sont créés."),
 # demande 2 : mode plan -> write bloqué
 faux.ol("",[T("write_file",{"path":"c.py","content":"x"})]),
 faux.ol("Plan : 1. créer c.py"),
 # demande 3 : recherche web
 faux.ol("",[T("web_search",{"query":"ollama"})]),
 faux.ol("Trouvé."),
 # /compacter : résumé (sans outils)
 faux.ol("Résumé : l'utilisateur a demandé a.py et b.py, créés. Mode plan testé. Recherche web faite."),
]
entree="crée a.py et b.py\no\no\n/plan\ncrée c.py\n/plan\ncherche ollama\n/taches\n/annuler\n/contexte\n/compacter\n/contexte\n/xyz\n/quitter\n"
p=subprocess.run([sys.executable,MORPHEUS],input=entree,capture_output=True,text=True,timeout=60,cwd=PROJ,env=dict(os.environ,HOME=HOME_TEST))
print(p.stdout); print(p.stderr[-3000:])
print("RESTE",len(faux.SCRIPT), "fichiers:",sorted(os.listdir(PROJ)))
sysmsg=faux.RECUS[0][1]["messages"][0]["content"]; print("consigne globale:", "tutoyer" in sysmsg, "| tools:", len(faux.RECUS[0][1]["tools"]), "| keep_alive:", faux.RECUS[0][1].get("keep_alive"))
print("résumé sans outils:", "tools" not in faux.RECUS[-1][1])
