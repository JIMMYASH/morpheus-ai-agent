import os, sys, importlib.util

# Test unitaire direct (pas de sous-processus ni de faux serveur) : on vérifie
# le contrat de _lire_flux(), la fonction qui protège contre une coupure
# réseau EN PLEIN MILIEU d'une réponse en streaming (pas une erreur HTTP
# propre, une vraie coupure de connexion — plus probable depuis qu'on utilise
# un modèle cloud). Avant ce correctif, une telle exception (OSError,
# ConnectionResetError, http.client.IncompleteRead...) remontait brute et
# aurait fait planter tout MORPHEUS au lieu d'être retentée comme les autres
# erreurs serveur transitoires.

spec = importlib.util.spec_from_file_location("morpheus", os.environ["MORPHEUS_PY"])
morpheus = importlib.util.module_from_spec(spec)
spec.loader.exec_module(morpheus)


def flux_qui_coupe():
    yield b'{"message":{"role":"assistant","content":"debut"},"done":false}\n'
    raise ConnectionResetError("connexion réinitialisée par le pair")


leve = None
try:
    list(morpheus._lire_flux(flux_qui_coupe()))
except morpheus.ErreurServeur as e:
    leve = e
print("ErreurServeur levée :", leve is not None, "-", leve)
assert leve is not None, "une coupure réseau en plein flux doit être convertie en ErreurServeur, pas planter"

# Un flux normal (sans coupure) ne doit pas être affecté.
normal = list(morpheus._lire_flux([b"a\n", b"b\n"]))
print("flux normal :", normal)
assert normal == [b"a\n", b"b\n"], "un flux sans coupure doit passer inchangé"

print("OK : coupure réseau en plein flux convertie en ErreurServeur, flux normal inchangé")
