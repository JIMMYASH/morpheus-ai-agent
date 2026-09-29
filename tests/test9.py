import os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
import subprocess,sys,os
sys.path.insert(0,BASE); import faux
faux.lancer(18434)
T=lambda n,a:{"function":{"name":n,"arguments":a}}
env=dict(os.environ,HOME=HOME_TEST)
# session 1
faux.SCRIPT+=[faux.ol("",[T("bash",{"command":"ls"})]), faux.ol("Le dossier est vide.")]
subprocess.run([sys.executable,MORPHEUS,"liste le dossier"],input="/quitter\n",capture_output=True,text=True,timeout=60,cwd=PROJ,env=env)
# -c reprise
faux.SCRIPT+=[faux.ol("Tu m'avais demandé de lister le dossier.")]
p=subprocess.run([sys.executable,MORPHEUS,"-c"],input="qu'est-ce que je t'ai demandé ?\n/quitter\n",capture_output=True,text=True,timeout=60,cwd=PROJ,env=env)
print(p.stdout[-600:], p.stderr[-800:])
print([m["role"] for m in faux.RECUS[-1][1]["messages"]])
# -p : écriture refusée automatiquement
faux.SCRIPT+=[faux.ol("",[T("write_file",{"path":"z.txt","content":"z"})]), faux.ol("Je n'ai pas pu créer z.txt.")]
p=subprocess.run([sys.executable,MORPHEUS,"-p","crée z.txt"],capture_output=True,text=True,timeout=60,cwd=PROJ,env=env,stdin=subprocess.DEVNULL)
print(p.returncode, p.stdout[-700:], p.stderr[-800:]); print("z existe:", os.path.exists(PROJ+"/z.txt"))
