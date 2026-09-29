import os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
import subprocess,sys,os
sys.path.insert(0,BASE); import faux
faux.lancer(18434)
open(PROJ+"/MORPHEUS.md","w").write("Lancer les tests : python3 -m unittest test_notes.py\n")
faux.SCRIPT+=[faux.ol("python3 -m unittest test_notes.py"),faux.ol("ok")]
p=subprocess.run([sys.executable,MORPHEUS],input="comment lancer les tests ?\nautre\n/quitter\n",capture_output=True,text=True,timeout=60,cwd=PROJ,env=dict(os.environ,HOME=HOME_TEST))
m1=faux.RECUS[0][1]["messages"]; m2=faux.RECUS[1][1]["messages"]
print("1re demande contient consignes:", "Consignes du projet" in m1[1]["content"])
print("2e demande sans doublon:", "Consignes du projet" not in m2[-1]["content"])
print("system sans MORPHEUS.md:", "unittest" not in m1[0]["content"])
