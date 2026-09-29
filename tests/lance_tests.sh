#!/usr/bin/env bash
# Lance tous les tests de MORPHEUS avec un faux serveur de modèle (aucun vrai modèle n'est appelé).
# Usage : bash tests/lance_tests.sh        (depuis le dossier de morpheus)
set -u
DOSSIER_TESTS="$(cd "$(dirname "$0")" && pwd)"
export MORPHEUS_PY="$(cd "$DOSSIER_TESTS/.." && pwd)/morpheus.py"
TRAVAIL="$(mktemp -d /tmp/morpheus-tests.XXXXXX)"
export MORPHEUS_TEST_PROJ="$TRAVAIL/proj"
export MORPHEUS_TEST_HOME="$TRAVAIL/home"
export MORPHEUS_URL_OLLAMA="http://127.0.0.1:18434"
export MORPHEUS_URL_LLAMACPP="http://127.0.0.1:18080"
export MORPHEUS_URL_TELEGRAM="http://127.0.0.1:18091"   # jamais le vrai Telegram pendant les tests
export MORPHEUS_URL_REGISTRE_OLLAMA="http://127.0.0.1:18434"   # bibliothèque d'Ollama simulée par faux.py
export MORPHEUS_CLAUDE="/inexistant/claude"             # jamais le vrai Claude Code (test48 utilise faux_claude.py)
unset MORPHEUS_MODELE MORPHEUS_SERVEUR MORPHEUS_NUM_CTX
export MORPHEUS_MODE=dev        # les tests existants modifient des fichiers ; le mode Chat a son propre test

echo "Vérification de la syntaxe…"
python3 -m py_compile "$MORPHEUS_PY" || { echo "ÉCHEC : erreur de syntaxe dans morpheus.py"; exit 1; }

echons=0
for t in "$DOSSIER_TESTS"/test*.py; do
    nom="$(basename "$t" .py)"
    rm -rf "$MORPHEUS_TEST_PROJ" "$MORPHEUS_TEST_HOME"
    mkdir -p "$MORPHEUS_TEST_PROJ" "$MORPHEUS_TEST_HOME"
    sortie="$TRAVAIL/$nom.out"
    if timeout 120 python3 "$t" > "$sortie" 2>&1 && ! grep -q "Traceback" "$sortie"; then
        echo "  OK      $nom"
    else
        echo "  ÉCHEC   $nom   (détails : $sortie)"
        echons=$((echons + 1))
    fi
done
if [ "$echons" -eq 0 ]; then
    echo "Tous les tests passent."
    rm -rf "$TRAVAIL"
else
    echo "$echons test(s) en échec. Sorties conservées dans $TRAVAIL"
    exit 1
fi
