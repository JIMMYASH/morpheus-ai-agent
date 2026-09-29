import os, sys, json, time, zipfile, shutil, subprocess
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import quote
BASE = os.path.dirname(os.path.abspath(__file__))
MORPHEUS = os.environ["MORPHEUS_PY"]
PROJ = os.environ["MORPHEUS_TEST_PROJ"]
HOME_TEST = os.environ["MORPHEUS_TEST_HOME"]
sys.path.insert(0, BASE); import faux
faux.lancer(18434)
T = lambda n, a: {"function": {"name": n, "arguments": a}}
env = dict(os.environ, HOME=HOME_TEST)

# Documents : read_file extrait le texte des PDF, Word, LibreOffice, Excel et PowerPoint (lecture seule),
# et l'interface web permet d'envoyer des fichiers dans le projet.


def archive(nom, fichiers):
    with zipfile.ZipFile(os.path.join(PROJ, nom), "w") as z:
        for chemin, contenu in fichiers.items():
            z.writestr(chemin, contenu)


archive("rapport.docx", {"word/document.xml":
        '<w:document xmlns:w="w"><w:body><w:p><w:r><w:t>Bonjour depuis Word</w:t></w:r></w:p>'
        '<w:p><w:r><w:t>Deuxième &amp; dernier paragraphe</w:t></w:r></w:p></w:body></w:document>'})
archive("budget.xlsx", {
    "xl/sharedStrings.xml": "<sst><si><t>Poste</t></si><si><t>Montant</t></si><si><t>Loyer</t></si></sst>",
    "xl/worksheets/sheet1.xml": '<worksheet><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>'
                                '<row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2"><v>700</v></c></row></sheetData></worksheet>'})
archive("notes.odt", {"content.xml": '<office:document-content><text:h>Titre ODT</text:h><text:p>Texte LibreOffice</text:p></office:document-content>'})
archive("expose.pptx", {"ppt/slides/slide2.xml": "<p:sld><a:p><a:r><a:t>Conclusion</a:t></a:r></a:p></p:sld>",
                        "ppt/slides/slide1.xml": "<p:sld><a:p><a:r><a:t>Introduction</a:t></a:r></a:p></p:sld>"})
open(os.path.join(PROJ, "photo.png"), "wb").write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 50)
# Un PDF minimal écrit à la main (une page, un texte en Helvetica)
flux = b"BT /F1 24 Tf 72 700 Td (Bonjour PDF) Tj ET"
objets = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
          b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
          b"<< /Length %d >>\nstream\n" % len(flux) + flux + b"\nendstream",
          b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
pdf, positions = b"%PDF-1.4\n", []
for i, o in enumerate(objets, 1):
    positions.append(len(pdf))
    pdf += b"%d 0 obj\n" % i + o + b"\nendobj\n"
xref = len(pdf)
pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objets) + 1) + b"".join(b"%010d 00000 n \n" % p for p in positions)
pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objets) + 1, xref)
open(os.path.join(PROJ, "facture.pdf"), "wb").write(pdf)

# --- 1. Extraction par read_file (dans le terminal) ---
fichiers = ["rapport.docx", "budget.xlsx", "notes.odt", "expose.pptx", "photo.png"] + \
           (["facture.pdf"] if shutil.which("pdftotext") else [])
faux.SCRIPT += [faux.ol("", [T("read_file", {"path": f})]) for f in fichiers]
faux.SCRIPT += [faux.ol("", [T("edit_file", {"path": "rapport.docx", "old_string": "Bonjour", "new_string": "Salut"})]),
                faux.ol("J'ai lu les documents.")]
subprocess.run([sys.executable, MORPHEUS], input="résume les documents ?\n/quitter\n", capture_output=True,
               text=True, timeout=60, cwd=PROJ, env=env)
journal = sorted(os.listdir(os.path.join(HOME_TEST, ".local/share/morpheus/sessions")))[-1]
resultats = [json.loads(l)["content"] for l in open(os.path.join(HOME_TEST, ".local/share/morpheus/sessions", journal))
             if json.loads(l).get("role") == "tool"]
for r in resultats:
    print("---", r[:300])
docx, xlsx, odt, pptx, png = resultats[:5]
assert "lecture seule" in docx and "Bonjour depuis Word" in docx and "Deuxième & dernier paragraphe" in docx
assert "Poste\tMontant" in xlsx and "Loyer\t700" in xlsx
assert "Titre ODT" in odt and "Texte LibreOffice" in odt
assert pptx.index("Introduction") < pptx.index("Conclusion"), "les diapositives dans l'ordre"
assert "image" in png and "tu ne peux pas voir" in png
if shutil.which("pdftotext"):
    assert "Bonjour PDF" in resultats[5], resultats[5]
assert "est un document (DOCX)" in resultats[-1] and "nouveau fichier texte" in resultats[-1], \
    "un document ne doit pas pouvoir être modifié par edit_file, avec un message qui évite de réessayer"
assert open(os.path.join(PROJ, "rapport.docx"), "rb").read(2) == b"PK", "le document n'a pas été abîmé"

# --- 2. Envoi de fichiers par l'interface web ---
PORT = 18774
URL = f"http://127.0.0.1:{PORT}"
serveur = subprocess.Popen([sys.executable, MORPHEUS, "--web", "--port", str(PORT), "--hote", "127.0.0.1"],
                           cwd=PROJ, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def envoi(cookie, nom, contenu, entete=True, taille=None):
    entetes = {"Cookie": cookie, "Content-Type": "application/octet-stream"}
    if entete:
        entetes["X-Morpheus"] = "1"
    if taille is not None:
        entetes["Content-Length"] = str(taille)
    try:
        with urlopen(Request(f"{URL}/api/televerser?nom={quote(nom)}", data=contenu, headers=entetes), timeout=10) as r:
            return r.status, json.loads(r.read())
    except HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


try:
    for _ in range(50):
        try:
            urlopen(URL + "/", timeout=1).read()
            break
        except OSError:
            time.sleep(0.2)
    jeton = open(os.path.join(HOME_TEST, ".config/morpheus/jeton_web")).read().strip()
    with urlopen(Request(URL + "/api/connexion", data=json.dumps({"jeton": jeton}).encode(),
                         headers={"Content-Type": "application/json"}), timeout=10) as r:
        cookie = r.headers["Set-Cookie"].split(";")[0]

    code, rep = envoi(cookie, "compte rendu.txt", "Réunion du lundi\n".encode())
    assert code == 200 and rep["chemin"] == "compte rendu.txt", rep
    assert open(os.path.join(PROJ, "compte rendu.txt"), encoding="utf-8").read() == "Réunion du lundi\n"
    code, rep = envoi(cookie, "compte rendu.txt", b"autre version\n")
    assert rep["chemin"] == "compte rendu (2).txt", "jamais d'écrasement"
    assert open(os.path.join(PROJ, "compte rendu.txt"), encoding="utf-8").read() == "Réunion du lundi\n"
    for dangereux, attendu in (("../../evasion.txt", "evasion.txt"), ("/etc/passwd", "passwd"),
                               (".bashrc", "bashrc"), ("a<b>|c.txt", "a_b__c.txt"), ("", "fichier")):
        code, rep = envoi(cookie, dangereux, b"x")
        assert code == 200 and rep["chemin"] == attendu, (dangereux, rep)
    assert not os.path.exists(os.path.join(os.path.dirname(PROJ), "evasion.txt"))
    assert envoi(cookie, "x.txt", b"x", entete=False)[0] == 401, "l'en-tête anti-CSRF est obligatoire"
    assert envoi("", "x.txt", b"x")[0] == 401
    assert envoi(cookie, "gros.bin", b"x", taille=26_000_000)[0] == 413

    # Le message avec pièces jointes : le modèle est prévenu et lit le fichier ; pas de relance
    # « aucun fichier modifié » même si la demande dit « ajoute » (le fichier est déjà ajouté).
    faux.SCRIPT += [faux.ol("", [T("read_file", {"path": "compte rendu.txt"})]), faux.ol("C'est un compte rendu de réunion.")]
    message = "Ajoute ce compte rendu au projet\n\n[Pièces jointes, enregistrées dans le dossier du projet : compte rendu.txt — lis-les avec read_file pour répondre]"
    with urlopen(Request(URL + "/api/message", data=json.dumps({"texte": message}).encode(),
                         headers={"Content-Type": "application/json", "X-Morpheus": "1", "Cookie": cookie}), timeout=10):
        pass
    for _ in range(100):
        with urlopen(Request(URL + "/api/evenements?depuis=0", headers={"Cookie": cookie}), timeout=10) as r:
            evs = json.loads(r.read())["evenements"]
        if any(e["type"] == "fin" for e in evs[1:]) and any(e["type"] == "texte" for e in evs):
            break
        time.sleep(0.1)
    envoye = json.dumps(faux.RECUS[-1][1]["messages"], ensure_ascii=False)
    assert "Pièces jointes" in envoye and "Réunion du lundi" in envoye
    assert "Vérification de MORPHEUS" not in envoye and not faux.SCRIPT
    print("OK : documents lus (PDF, Word, Excel, LibreOffice, PowerPoint), images signalées, envois de fichiers sûrs")
finally:
    serveur.terminate()
    try:
        sortie = serveur.communicate(timeout=5)[0]
    except subprocess.TimeoutExpired:
        serveur.kill()
        sortie = serveur.communicate()[0]
    print(sortie[-2000:])
