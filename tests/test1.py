import os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
import subprocess,sys,os,json
sys.path.insert(0,BASE); import faux
faux.lancer(18434)
T=lambda n,a:{"function":{"name":n,"arguments":a}}
faux.SCRIPT+= [
 faux.ol("Je crée le fichier.",[T("write_file",{"path":"toto.txt","content":"c'est le fichier de toto\n"})]),
 faux.ol("Fichier toto.txt créé."),
 # XML fallback
 faux.ol("Je lis.\n<tool_call>\n<function=read_file>\n<parameter=path>\ntoto.txt\n</parameter>\n</function>\n</tool_call>"),
 faux.ol("",[T("edit_file",{"path":"toto.txt","old_string":"toto","new_string":"titi"})]),
 faux.ol("Modifié."),
 faux.ol("",[T("bash",{"command":"ls -la"}),T("bash",{"command":"rm toto.txt"})]),
 faux.ol("Suppression refusée, j'ai listé à la place."),
 faux.ol("",[T("bash",{"command":"sudo apt update"})]),
 faux.ol("Je ne peux pas utiliser sudo."),
]
entree="crée toto.txt\no\nmodifie toto en titi\no\nnettoie\nn\nnon garde-le\nmets à jour\n/contexte\n/quitter\n"
p=subprocess.run([sys.executable,MORPHEUS],input=entree,capture_output=True,text=True,timeout=60,cwd=PROJ,env=dict(os.environ,HOME=HOME_TEST))
print(p.stdout); print(p.stderr[-3000:])
print("FICHIER:",open(PROJ+"/toto.txt").read())
print("RESTE SCRIPT:",len(faux.SCRIPT))
dernier=faux.RECUS[-1][1]
print([ (m["role"], m.get("tool_name","")) for m in dernier["messages"]])
print(dernier["options"])
