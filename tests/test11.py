import os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
import subprocess,sys,os
sys.path.insert(0,BASE); import faux
faux.lancer(18434)
T=lambda n,a:{"function":{"name":n,"arguments":a}}
open(PROJ+"/notes.py","w").write("def add():\n    pass\n")
faux.SCRIPT+=[faux.ol("",[T("grep",{"pattern":"def"})]),
 faux.ol("J'ai ajouté la commande edit. Tous les tests passent."),     # mensonge -> vérification
 faux.ol("",[T("read_file",{"path":"notes.py"})]),
 faux.ol("",[T("edit_file",{"path":"notes.py","old_string":"def add():\n    pass\n","new_string":"def add():\n    pass\n\ndef edit():\n    pass\n"})]),
 faux.ol("La commande edit est ajoutée."),
 faux.ol("Le fichier contient deux fonctions."),   # question simple : pas de vérification
]
p=subprocess.run([sys.executable,MORPHEUS,"ajoute une commande edit"],input="o\nque contient notes.py ?\n/quitter\n",capture_output=True,text=True,timeout=60,cwd=PROJ,env=dict(os.environ,HOME=HOME_TEST))
print(p.stdout[-2200:],p.stderr[-800:]); print("RESTE",len(faux.SCRIPT)); print(open(PROJ+"/notes.py").read())
