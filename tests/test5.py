import os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
import subprocess,sys,os
sys.path.insert(0,BASE); import faux
faux.lancer(18434)
T=lambda n,a:{"function":{"name":n,"arguments":a}}
faux.SCRIPT+=[faux.ol("",[T("read_file",{"path":"toto.txt"})]),
 faux.ol("",[T("read_file",{"path":"toto.txt"})]),
 faux.ol('Je lis :\n```python\nread_file(path="t4.txt")\n```'),
 faux.ol("",[T("bash",{"command":"uptime"})]),
 faux.ol("Fini.")]
p=subprocess.run([sys.executable,MORPHEUS,"diag"],input="/quitter\n",capture_output=True,text=True,timeout=60,cwd=PROJ,env=dict(os.environ,HOME=HOME_TEST))
print(p.stdout[-2500:],p.stderr[-1500:])
