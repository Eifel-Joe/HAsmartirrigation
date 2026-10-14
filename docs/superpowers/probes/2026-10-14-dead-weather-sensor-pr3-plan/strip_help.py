"""Drop the hourly-calculation sentence from the panel help in all 8 languages.

Byte-exact: each file must contain its sentence (with the leading space) exactly
once; the file is rewritten via a temp file + os.replace, line endings untouched.
"""

import os
import sys
from pathlib import Path

DIR = Path(sys.argv[1])
SENTENCES = {
    "de.json": " Gilt nur, solange „Stündliche Verdunstung“ (Experimentelle Funktionen) aus ist.",
    "en.json": ' Applies only while \\"Hourly evapotranspiration\\" (Experimental features) is off.',
    "es.json": " Solo se aplica mientras «Evapotranspiración horaria» (Funciones experimentales) esté desactivada.",
    "fr.json": " Ne s’applique que tant que « Évapotranspiration horaire » (Fonctionnalités expérimentales) est désactivée.",
    "it.json": " Vale solo finché «Evapotraspirazione oraria» (Funzioni sperimentali) è disattivata.",
    "nl.json": " Geldt alleen zolang “Verdamping per uur” (Experimentele functies) uit staat.",
    "no.json": " Gjelder bare så lenge «Timesvis evapotranspirasjon» (Eksperimentelle funksjoner) er av.",
    "sk.json": " Platí len, kým je „Hodinová evapotranspirácia“ (Experimentálne funkcie) vypnutá.",
}

for name, sentence in SENTENCES.items():
    path = DIR / name
    data = path.read_bytes()
    needle = sentence.encode("utf-8")
    count = data.count(needle)
    if count != 1:
        sys.exit(f"{name}: sentence found {count} times, expected 1")
    tmp = path.with_suffix(".json.tmp")
    tmp.write_bytes(data.replace(needle, b"", 1))
    os.replace(tmp, path)
    print(f"{name}: removed")
