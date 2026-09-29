import os, sys, subprocess
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
sys.path.insert(0, BASE); import faux
faux.lancer(18434)
T = lambda n, a: {"function": {"name": n, "arguments": a}}
env = dict(os.environ, HOME=HOME_TEST)

# 1. Heredoc : le code envoyé à un programme (python3 - << 'PY') n'est plus pris pour une écriture
#    de fichier à cause d'un « > » dans ce code ; heredoc + redirection vers un fichier, tee, ou
#    heredoc lu par un shell restent refusés.
os.chdir(PROJ)
sys.path.insert(0, os.path.dirname(MORPHEUS)); import morpheus

permis = ["python3 - << 'PY'\nprint('déplacé', 'a', '->', 'b')\nif 3 > 2: pass\nPY",
          "cd collection && python3 - <<PY\nx = 1 > 0\nPY 2>&1",
          "python3 - <<PY >/dev/null\nprint(1)\nPY"]
refuses = ["cat > f.txt << EOF\nbonjour\nEOF", "cat <<EOF > f.txt\nbonjour\nEOF", "cat <<EOF>>f.txt\nx\nEOF",
           "tee f.txt <<EOF\nx\nEOF", "python3 - <<PY > sortie.txt\nprint(1)\nPY",
           "bash <<EOF\necho a > f\nEOF", "bash <<EOF\npython3 x.py > f\nEOF", "nohup sh <<EOF\nls > f\nEOF",
           "cat <<-EOF > f\n\tx\n\tEOF", "python3 - <<PY\nx\nPY\ncat > g <<X\ny\nX", "echo hi > f", "sed -i s/a/b/ f"]
erreurs = [c for c in permis if morpheus.ecrit_du_contenu(c)] + \
          [c for c in refuses if not morpheus.ecrit_du_contenu(c)]
assert not erreurs, f"mal classées : {erreurs}"

# 2. Mode -p : une action refusée automatiquement n'arrête plus tout, le modèle continue sans elle.
open(os.path.join(PROJ, "main.py"), "w").write("print(1 / 0)\n")
faux.SCRIPT += [faux.ol("", [T("bash", {"command": "python3 main.py"})]),
                faux.ol("", [T("read_file", {"path": "main.py"})]),
                faux.ol("main.py divise par zéro. Lance toi-même : python3 main.py")]
p = subprocess.run([sys.executable, MORPHEUS, "-p", "vérifie main.py"], capture_output=True, text=True,
                   timeout=60, cwd=PROJ, env=env, stdin=subprocess.DEVNULL)
print(p.stdout, p.stderr[-2000:])
assert "refusé automatiquement" in p.stdout
assert "Tâche arrêtée" not in p.stdout and "divise par zéro" in p.stdout, p.stdout
assert len(faux.SCRIPT) == 0, "réponses non consommées"
refus = [m["content"] for m in faux.RECUS[1][1]["messages"] if m.get("role") == "tool"][-1]
assert "mode automatique (-p)" in refus and "continue sans elle" in refus, refus

# 3. Tâches bloquées par ce refus : le modèle le dit, MORPHEUS ne le relance pas pour rien.
faux.SCRIPT += [faux.ol("", [T("todo_write", {"todos": [{"content": "Lancer main.py", "status": "in_progress"},
                                                         {"content": "Corriger", "status": "pending"}]})]),
                faux.ol("", [T("bash", {"command": "python3 main.py"})]),
                faux.ol("Je ne peux pas lancer main.py : l'action a été refusée.")]
p = subprocess.run([sys.executable, MORPHEUS, "-p", "lance et corrige main.py"], capture_output=True, text=True,
                   timeout=60, cwd=PROJ, env=env, stdin=subprocess.DEVNULL)
print(p.stdout, p.stderr[-2000:])
assert "(relance" not in p.stdout and "Je ne peux pas lancer" in p.stdout, p.stdout
assert len(faux.SCRIPT) == 0, "réponses non consommées"
print("OK")
