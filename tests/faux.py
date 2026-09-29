import json, threading, sys, time
from http.server import BaseHTTPRequestHandler, HTTPServer
SCRIPT=[]; RECUS=[]; MODELES=["qwen3-coder-next","autre:7b"]; CLOUD=["kimi-k2.7-code:cloud"]
def ol(content="", tool_calls=None):
    return {"content":content,"tool_calls":tool_calls}
def erreur(code=500, message="Internal Server Error"):
    return {"erreur":code,"message":message}
class H(BaseHTTPRequestHandler):
    def do_POST(s):
        corps=json.loads(s.rfile.read(int(s.headers["Content-Length"])))
        if s.path=="/api/show":   # fiche d'un modèle : connu s'il est installé ou dans CLOUD
            s.send_response(200 if corps.get("model") in MODELES+CLOUD else 404); s.end_headers(); s.wfile.write(b"{}"); return
        RECUS.append((s.path,corps))
        r=SCRIPT.pop(0)
        if "pause" in r:   # modèle qui « réfléchit » sans rien envoyer (puis répond, si on l'attend encore)
            time.sleep(r["pause"])
            try:
                s.send_response(200); s.end_headers()
                s.wfile.write(b'{"message":{"role":"assistant","content":"trop tard"},"done":true}\n')
            except OSError:
                pass
            return
        if "erreur" in r:
            s.send_response(r["erreur"]); s.end_headers()
            s.wfile.write(json.dumps({"error":r["message"]}).encode())
            return
        s.send_response(200); s.end_headers()
        if s.path=="/api/chat":
            txt=r.get("content","")
            for i in range(0,len(txt),7):
                s.wfile.write((json.dumps({"message":{"role":"assistant","content":txt[i:i+7]},"done":False})+"\n").encode())
            if r.get("tool_calls"):
                s.wfile.write((json.dumps({"message":{"role":"assistant","content":"","tool_calls":r["tool_calls"]},"done":False})+"\n").encode())
            s.wfile.write(b'{"message":{"role":"assistant","content":""},"done":true,"prompt_eval_count":1200,"eval_count":80,"eval_duration":1000000000}\n')
        else:
            txt=r.get("content","")
            for i in range(0,len(txt),5):
                s.wfile.write(("data: "+json.dumps({"choices":[{"delta":{"content":txt[i:i+5]}}]})+"\n\n").encode())
            for j,tc in enumerate(r.get("tool_calls") or []):
                a=json.dumps(tc["function"]["arguments"])
                s.wfile.write(("data: "+json.dumps({"choices":[{"delta":{"tool_calls":[{"index":j,"id":"x%d"%j,"function":{"name":tc["function"]["name"],"arguments":a[:10]}}]}}]})+"\n\n").encode())
                s.wfile.write(("data: "+json.dumps({"choices":[{"delta":{"tool_calls":[{"index":j,"function":{"arguments":a[10:]}}]}}]})+"\n\n").encode())
            s.wfile.write(b"data: [DONE]\n\n")
    def do_GET(s):
        if s.path=="/api/tags":   # liste des modèles installés (Ollama)
            b=json.dumps({"models":[{"name":n} for n in MODELES]}).encode()
            s.send_response(200); s.end_headers(); s.wfile.write(b); return
        b=json.dumps({"results":[{"title":"Résultat A","url":"https://a.example","content":"extrait A"}]}).encode()
        s.send_response(200); s.end_headers(); s.wfile.write(b)
    def log_message(s,*a): pass
def lancer(port):
    srv=HTTPServer(("127.0.0.1",port),H); threading.Thread(target=srv.serve_forever,daemon=True).start()
