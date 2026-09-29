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
faux.SCRIPT+=[faux.ol("",[T("bash",{"command":"cd "+PROJ+" && cat notes.py"})])]
faux.SCRIPT+=[faux.ol("",[T("grep",{"pattern":f"x{i}"})]) for i in range(5)]
faux.SCRIPT+=[faux.ol("",[T("edit_file",{"path":"notes.py","old_string":"pass","new_string":"return 1"})]), faux.ol("Fait.")]
p=subprocess.run([sys.executable,MORPHEUS,"modifie add"],input="o\n/quitter\n",capture_output=True,text=True,timeout=60,cwd=PROJ,env=dict(os.environ,HOME=HOME_TEST))
print(p.stdout[-1200:],p.stderr[-800:]); print(open(PROJ+"/notes.py").read())
tool_msgs=faux.RECUS[-2][1]["messages"]
print("rappel présent:", any("Note de MORPHEUS" in m["content"] for m in tool_msgs))
print("options:", faux.RECUS[0][1]["options"], faux.RECUS[0][1]["model"])
