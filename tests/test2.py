import os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
import subprocess,sys,os
sys.path.insert(0,BASE); import faux
faux.lancer(18080)
T=lambda n,a:{"function":{"name":n,"arguments":a}}
faux.SCRIPT+=[faux.ol("Je regarde.",[T("glob",{"pattern":"**/*.txt"}),T("grep",{"pattern":"titi","ignore_case":"true"})]),faux.ol("Trouvé toto.txt.")]
p=subprocess.run([sys.executable,MORPHEUS,"trouve","les","txt"],input="/quitter\n",capture_output=True,text=True,timeout=60,cwd=PROJ,env=dict(os.environ,HOME=HOME_TEST,MORPHEUS_SERVEUR="llamacpp"))
print(p.stdout,p.stderr[-2000:])
print([(m["role"],m.get("tool_call_id")) for m in faux.RECUS[-1][1]["messages"]])
print(faux.RECUS[-1][1]["messages"][2])
