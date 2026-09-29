import os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
import subprocess,sys,os
sys.path.insert(0,BASE); import faux
faux.lancer(18434)
faux.SCRIPT+=[faux.ol("## Ce que fait ce projet\nC'est un **test** avec `sys.txt` :\n- point un\n* point deux\n```bash\nls\n```\nFin sans retour")]
p=subprocess.run([sys.executable,MORPHEUS,"explique"],input="/quitter\n",capture_output=True,text=True,timeout=60,cwd=PROJ,env=dict(os.environ,HOME=HOME_TEST))
print(p.stdout,p.stderr[-1500:])
