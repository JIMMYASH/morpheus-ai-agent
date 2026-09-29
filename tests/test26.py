import os, sys, subprocess
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
sys.path.insert(0, BASE); import faux
faux.lancer(18434)
T = lambda n, a: {"function": {"name": n, "arguments": a}}
env = dict(os.environ, HOME=HOME_TEST)

# Des commandes qui modifient des choses étaient classées « lecture seule », donc
# exécutées sans validation : git branch -D, git remote remove, sort -o, uniq a b,
# tree -o, find -fprintf / -fls, env <programme>, git diff --output, rg --pre.

# 1. Classement direct par commande_lecture_seule()
os.chdir(PROJ)
sys.path.insert(0, os.path.dirname(MORPHEUS)); import morpheus

lecture = ["git branch", "git branch -a", "git branch -vv", "git branch --show-current",
           "git remote", "git remote -v", "git remote show origin", "git remote get-url origin",
           "git diff", "git log --oneline -5", "sort notes.txt", "sort -n -r notes.txt",
           "uniq notes.txt", "uniq -c notes.txt", "uniq -f 1 notes.txt", "tree", "tree -L 2",
           "find . -name '*.py'", "env", "rg motif", "ls -la | sort | uniq -c"]
modification = ["git branch -D essai", "git branch nouvelle", "git branch -m a b",
                "git remote remove origin", "git remote add x https://a.example",
                "git remote set-url origin https://a.example", "git diff --output=patch.txt",
                "git log --output=log.txt", "sort -o notes.txt notes.txt", "sort -uo sortie.txt notes.txt",
                "sort --output=sortie.txt notes.txt", "sort --compress-program=rm notes.txt",
                "uniq notes.txt sortie.txt", "uniq -c notes.txt sortie.txt", "tree -o arbre.txt",
                "find . -fprintf sortie.txt '%p'", "find . -fls sortie.txt", "find . -fprint0 sortie.txt",
                "env rm -rf dossier", "env -i bash", "rg --pre rm motif", "file -C -m magie", "ls && git branch -D essai"]
erreurs = [c for c in lecture if not morpheus.commande_lecture_seule(c)]
erreurs += [c for c in modification if morpheus.commande_lecture_seule(c)]
print("mal classées :", erreurs)
assert not erreurs, f"commandes mal classées : {erreurs}"

# 2. De bout en bout : en mode -p, git branch -D doit être refusé (validation requise)
subprocess.run(["git", "init", "-q"], cwd=PROJ, check=True)
faux.SCRIPT += [faux.ol("", [T("bash", {"command": "git branch -D essai"})]),
                faux.ol("Je n'ai pas pu supprimer la branche.")]
p = subprocess.run([sys.executable, MORPHEUS, "-p", "supprime la branche essai"], capture_output=True,
                   text=True, timeout=60, cwd=PROJ, env=env, stdin=subprocess.DEVNULL)
print(p.stdout[-1500:], p.stderr[-1500:])
assert "refusé automatiquement" in p.stdout, "git branch -D doit demander une validation (refusée en mode -p)"
print("OK : les commandes qui modifient ne passent plus pour de la lecture seule")
