import os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
import subprocess,sys,os
sys.path.insert(0,BASE); import faux
faux.lancer(18434)
T=lambda n,a:{"function":{"name":n,"arguments":a}}
open(PROJ+"/MORPHEUS.md","w").write("Pour ajouter une commande, modifier notes.py.\nTests : python3 -m unittest\n")
faux.SCRIPT+=[faux.ol("",[T("notes.py",{"command":"ls"})]), faux.ol("Avec python3 -m unittest."),
              faux.ol("J'ai ajouté la commande."), faux.ol("",[T("write_file",{"path":"x.py","content":"x=1\n"})]), faux.ol("Fait.")]
p=subprocess.run([sys.executable,MORPHEUS],input="comment je lance les tests ?\najoute un fichier x.py\no\n/quitter\n",capture_output=True,text=True,timeout=60,cwd=PROJ,env=dict(os.environ,HOME=HOME_TEST))
print(p.stdout[-1500:], p.stderr[-500:]); print("RESTE", len(faux.SCRIPT))
