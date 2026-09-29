#!/usr/bin/env python3
"""Faux programme `claude` (Claude Code) pour les tests : rejoue un scénario en « stream-json ».
FAUX_CLAUDE_SCENARIOS : fichier JSON, liste de scénarios (un par lancement, consommés dans l'ordre).
Un scénario est une liste d'étapes : {"texte": "..."} ou {"outil": "Write", "input": {...}}.
FAUX_CLAUDE_JOURNAL : fichier où sont notés les arguments reçus et les réponses de MORPHEUS."""
import json, os, subprocess, sys

journal = open(os.environ["FAUX_CLAUDE_JOURNAL"], "a", encoding="utf-8")


def noter(objet):
    journal.write(json.dumps(objet, ensure_ascii=False) + "\n")
    journal.flush()


def envoyer(objet):
    print(json.dumps(objet, ensure_ascii=False), flush=True)


fichier = os.environ["FAUX_CLAUDE_SCENARIOS"]
scenarios = json.load(open(fichier, encoding="utf-8"))
scenario = scenarios.pop(0) if scenarios else [{"texte": "(plus de scénario)"}]
json.dump(scenarios, open(fichier, "w", encoding="utf-8"))
noter({"arguments": sys.argv[1:]})

lignes = iter(sys.stdin)
demande = None
for ligne in lignes:
    o = json.loads(ligne)
    if o.get("type") == "control_request":
        envoyer({"type": "control_response", "response": {"subtype": "success", "request_id": o["request_id"], "response": {}}})
    elif o.get("type") == "user":
        demande = o["message"]["content"]
        break
noter({"demande": demande})
envoyer({"type": "system", "subtype": "init", "session_id": "session-faux-1", "tools": []})
for i, etape in enumerate(scenario):
    ident = f"msg_{i}"
    if "texte" in etape:
        envoyer({"type": "stream_event", "event": {"type": "message_start", "message": {"id": ident}}})
        envoyer({"type": "stream_event", "event": {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}}})
        for morceau in (etape["texte"][:5], etape["texte"][5:]):
            envoyer({"type": "stream_event", "event": {"type": "content_block_delta", "index": 0,
                                                       "delta": {"type": "text_delta", "text": morceau}}})
        envoyer({"type": "stream_event", "event": {"type": "content_block_stop", "index": 0}})
        envoyer({"type": "assistant", "message": {"id": ident, "content": [{"type": "text", "text": etape["texte"]}]}})
        continue
    outil, entree = etape["outil"], etape["input"]
    appel = f"toolu_{i}"
    envoyer({"type": "assistant", "message": {"id": ident, "content": [
        {"type": "tool_use", "id": appel, "name": outil, "input": entree}]}})
    envoyer({"type": "control_request", "request_id": f"req_{i}", "request": {
        "subtype": "can_use_tool", "tool_name": outil, "input": entree, "tool_use_id": appel}})
    reponse = json.loads(next(lignes))
    decision = reponse["response"]["response"]
    noter({"outil": outil, "decision": decision})
    if decision.get("behavior") != "allow":
        envoyer({"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": appel, "content": decision.get("message"), "is_error": True}]}})
        if decision.get("interrupt"):
            break
        continue
    if outil == "Write":
        with open(entree["file_path"], "w", encoding="utf-8") as f:
            f.write(entree["content"])
        sortie = "File created successfully"
    elif outil == "Bash":
        sortie = subprocess.run(["bash", "-c", entree["command"]], capture_output=True, text=True).stdout or "(ok)"
    else:
        sortie = "ok"
    envoyer({"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": appel, "content": sortie}]}})
envoyer({"type": "result", "subtype": "success", "is_error": False, "session_id": "session-faux-1", "result": ""})
for ligne in lignes:           # attend que MORPHEUS ferme l'entrée
    pass
