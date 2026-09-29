import os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
import subprocess,sys,os
sys.path.insert(0,BASE); import faux
faux.lancer(18434)
T=lambda n,a:{"function":{"name":n,"arguments":a}}
faux.SCRIPT+=[faux.ol("Je commence.",[T("bash",{"command":"uname -a"})]),
 faux.ol("Vérifions maintenant les processus en cours."),
 faux.ol("",[T("bash",{"command":"uptime"})]),
 faux.ol("Diagnostic terminé, voilà le résumé."),
 faux.ol("Bonjour !")]
p=subprocess.run([sys.executable,MORPHEUS,"diag"],input="salut\n/quitter\n",capture_output=True,text=True,timeout=60,cwd=PROJ,env=dict(os.environ,HOME=HOME_TEST))
print(p.stdout[-2000:],p.stderr[-1500:]); print(len(faux.SCRIPT))
