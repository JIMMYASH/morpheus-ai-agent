import os, sys, subprocess
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
sys.path.insert(0, BASE); import faux
faux.lancer(18434)
T = lambda n, a: {"function": {"name": n, "arguments": a}}
env = dict(os.environ, HOME=HOME_TEST)

# Mode auto : modifications du projet sans question ; commandes qui écrivent jugées par le modèle
# (sûre -> exécutée, à vérifier ou réponse illisible -> question habituelle) ; interdits toujours refusés.
faux.SCRIPT += [faux.ol("", [T("write_file", {"path": "a.txt", "content": "bonjour\n"})]),
                faux.ol("", [T("bash", {"command": "touch b.txt"})]),
                faux.ol('Je réfléchis… {"verdict": "sure", "raison": "crée un fichier du projet"}'),     # juge
                faux.ol("", [T("bash", {"command": "rm a.txt"})]),
                faux.ol('{"verdict": "a_verifier", "raison": "supprime un fichier"}'),                # juge
                faux.ol("", [T("bash", {"command": "mkdir d"})]),
                faux.ol("je ne sais pas"),                                                            # juge illisible
                faux.ol("", [T("bash", {"command": "sudo apt install x"})]),
                faux.ol("", [T("write_file", {"path": "/tmp/hors_projet_morpheus_test50.txt", "content": "x"})])]
p = subprocess.run([sys.executable, MORPHEUS],
                   input="/auto\ncrée a.txt et b.txt\nn\ngarde a.txt\nn\npas de dossier\nn\n\n/quitter\n",
                   capture_output=True, text=True, timeout=60, cwd=PROJ, env=env)
print(p.stdout[-4000:], p.stderr[-800:])
assert "Mode auto activé" in p.stdout
assert "mode auto : modification appliquée sans question" in p.stdout and open(os.path.join(PROJ, "a.txt")).read() == "bonjour\n"
assert "Appliquer cette modification ?" not in p.stdout.split("hors_projet")[0], "pas de question dans le projet"
assert os.path.exists(os.path.join(PROJ, "b.txt")) and "exécutée sans question — crée un fichier du projet" in p.stdout
juges = [r[1] for r in faux.RECUS if "contrôleur de sécurité" in r[1]["messages"][0]["content"]]
assert len(juges) == 3, len(juges)
assert "touch b.txt" in juges[0]["messages"][1]["content"] and "crée a.txt et b.txt" in juges[0]["messages"][1]["content"]
assert not juges[0].get("tools"), "le juge n'a pas d'outils"
assert "commande à vérifier — supprime un fichier" in p.stdout and os.path.exists(os.path.join(PROJ, "a.txt")), \
    "commande douteuse : question, refusée"
assert "réponse du juge illisible" in p.stdout and not os.path.exists(os.path.join(PROJ, "d"))
assert p.stdout.count("Exécuter cette commande ?") == 2, "rm et mkdir demandés, sudo refusé sans question"
assert "Autoriser cette modification ?" in p.stdout and not os.path.exists("/tmp/hors_projet_morpheus_test50.txt"), \
    "hors du projet : toujours demandé"
assert "auto>" in p.stdout

# Sans /auto : tout est demandé comme avant ; /auto en mode Chat n'autorise rien
faux.SCRIPT += [faux.ol("", [T("write_file", {"path": "c.txt", "content": "c"})]), faux.ol("Non fait.")]
n = len(faux.RECUS)
p = subprocess.run([sys.executable, MORPHEUS], input="crée c.txt\nn\n\n/quitter\n",
                   capture_output=True, text=True, timeout=60, cwd=PROJ, env=env)
assert "Appliquer cette modification ?" in p.stdout and not os.path.exists(os.path.join(PROJ, "c.txt"))
faux.SCRIPT += [faux.ol("", [T("write_file", {"path": "c.txt", "content": "c"})]), faux.ol("Mode Chat.")]
p = subprocess.run([sys.executable, MORPHEUS], input="/auto on\ncrée c.txt\n/auto off\n/quitter\n",
                   capture_output=True, text=True, timeout=60, cwd=PROJ, env=dict(env, MORPHEUS_MODE="chat"))
print(p.stdout[-1500:])
assert "il agira quand tu passeras en mode développeur" in p.stdout and not os.path.exists(os.path.join(PROJ, "c.txt"))
assert "Mode auto désactivé" in p.stdout
print("OK")
