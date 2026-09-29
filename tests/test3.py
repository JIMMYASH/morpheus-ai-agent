import os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
import subprocess,sys,os
sys.path.insert(0,BASE); import faux
faux.lancer(18434)
faux.SCRIPT+=[faux.ol('{"name": "write_file", "arguments": {"path": "toto2.txt", "content": "c\'est le fichier de toto"}}'),
 faux.ol('Je le crée :\n```json\n{"name": "list_dir", "arguments": {}}\n```'),
 faux.ol("Fait.")]
p=subprocess.run([sys.executable,MORPHEUS],input="crée toto2\no\n/quitter\n",capture_output=True,text=True,timeout=60,cwd=PROJ,env=dict(os.environ,HOME=HOME_TEST))
print(p.stdout,p.stderr[-2000:]); print(open(PROJ+"/toto2.txt").read())
