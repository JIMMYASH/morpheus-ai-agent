import os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
import subprocess,sys,os
sys.path.insert(0,BASE); import faux
faux.lancer(18434)
T=lambda n,a:{"function":{"name":n,"arguments":a}}
faux.SCRIPT+=[faux.ol("",[T("bash",{"command":"cat > date.py << 'EOF'\nprint(1)\nEOF"})]),
 faux.ol("",[T("write_file",{"path":"date.py","content":"print(1)\n"})]),
 faux.ol("date.py créé.")]
p=subprocess.run([sys.executable,MORPHEUS,"crée date.py"],input="o\n/annuler\n/quitter\n",capture_output=True,text=True,timeout=60,cwd=PROJ,env=dict(os.environ,HOME=HOME_TEST))
print(p.stdout[-1500:],p.stderr[-800:]); print("date.py existe après /annuler :",os.path.exists(PROJ+"/date.py"))
