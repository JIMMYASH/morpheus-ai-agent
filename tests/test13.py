import os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
import subprocess,sys,os
sys.path.insert(0,BASE); import faux
faux.lancer(18434)
T=lambda n,a:{"function":{"name":n,"arguments":a}}
orig="def a():\n    return 1\n\ndef b():\n    return 2\n\ndef a():\n    return 1\n"
open(PROJ+"/notes.py","w").write(orig)
faux.SCRIPT+=[
 faux.ol("",[T("bash",{"command":"sed -n '1,3p' notes.py"})]),
 faux.ol("",[T("bash",{"command":"head -n 2 notes.py > /tmp/x.py && cp /tmp/x.py notes.py && touch nouveau.txt"})]),
 faux.ol("Fichier nettoyé."),
 faux.ol("",[T("read_file",{"path":"notes.py"})]),
 faux.ol("",[T("replace_lines",{"path":"notes.py","start_line":6,"end_line":8,"new_content":""})]),
 faux.ol("Doublon supprimé."),
]
entree="nettoie\no\n/annuler\nsupprime le doublon\no\n/quitter\n"
p=subprocess.run([sys.executable,MORPHEUS],input=entree,capture_output=True,text=True,timeout=60,cwd=PROJ,env=dict(os.environ,HOME=HOME_TEST))
print(p.stdout[-2600:],p.stderr[-800:])
print("----\n"+open(PROJ+"/notes.py").read()); print("nouveau.txt existe:", os.path.exists(PROJ+"/nouveau.txt"))
