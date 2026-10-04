"""Plan revision 2 (2026-10-04): the edits on top of probe-2026-10-03.patch.

PR 1 now ships alone (JustChr's answer on #188: detection, outage list, notice and
event first, with no behaviour change). So nothing it says may promise the cut: the
constants comment, the module docstring, the log warning and the notice in all eight
languages change; the docs gain the section "When a sensor goes silent". Every anchor
must match exactly once, as in probe_apply.py.

Usage: python probe_rev2.py <worktree root>
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(sys.argv[1])
IP = ROOT / "custom_components" / "irrigation_plus"


def edit(path, old, new):
    raw = path.read_bytes()
    crlf = b"\r\n" in raw
    text = raw.decode("utf-8").replace("\r\n", "\n")
    count = text.count(old)
    if count != 1:
        sys.exit(f"ABORT {path.name}: {count} matches for {old[:70]!r}")
    text = text.replace(old, new)
    if crlf:
        text = text.replace("\n", "\r\n")
    path.write_bytes(text.encode("utf-8"))
    print(f"ok {path.relative_to(ROOT)}: {old.strip()[:60]!r}")


# --- const.py: the limit's comment no longer claims cloud polling fits --------
edit(
    IP / "const.py",
    "# A sensor field whose HA device has not reported for this long counts as dead:\n"
    "# its outage is recorded on the sensor group and the user is told. Long enough\n"
    "# for an HA restart, a cloud integration's polling interval and a quiet night on\n"
    "# an integration that writes only on change.\n",
    "# A sensor field whose HA device has not reported for this long counts as\n"
    "# silent: its outage is recorded on the sensor group and the user is told. Long\n"
    "# enough for an HA restart and a quiet night on an integration that writes only\n"
    "# on change. Fixed: an integration that updates less often than this raises the\n"
    "# notice between its updates, which docs/configuration-sensor-groups.md says.\n",
)

# --- sensor_liveness.py: docstring and warning promise no cut -----------------
edit(
    IP / "sensor_liveness.py",
    "Cutting an outage out of the calculation is not done here; the aggregation reads the\n"
    "ledger this module writes.\n",
    "Nothing here changes a calculation: a silent sensor's last value is still used, as\n"
    "before. The ledger records when it fell silent and the notice tells the user.\n",
)
edit(
    IP / "sensor_liveness.py",
    '                "Sensor group %s: %s (%s) has not reported since %s; its readings "\n'
    '                "count only until %s hours after that",\n'
    "                name,\n"
    "                outage.entity_id,\n"
    '                ", ".join(outage.fields),\n'
    "                outage.start,\n"
    "                const.SENSOR_STALE_AFTER_SECONDS // 3600,\n"
    "            )\n",
    '                "Sensor group %s: %s (%s) has not reported since %s; its last "\n'
    '                "value is still used",\n'
    "                name,\n"
    "                outage.entity_id,\n"
    '                ", ".join(outage.fields),\n'
    "                outage.start,\n"
    "            )\n",
)

# --- translations: the notice of PR 1 --------------------------------------------
DESCRIPTIONS = {
    "en": (
        "Irrigation Plus has not heard from {entities} since {since}. The last reported "
        "values are still used as if they were current, so zones that depend on them "
        "are calculated with those values until new ones arrive.\n\n"
        "Check the device and its integration. If you replaced the device, select its "
        "new entities in the sensor group. If the value is meant to be fixed, use the "
        '"Static value" source instead. If the integration only updates every few '
        "hours, this notice appears between its updates and does not mean the sensor "
        "has failed.\n\n"
        "This notice clears itself when the sensor reports again."
    ),
    "de": (
        "Irrigation Plus hat seit {since} nichts mehr von {entities} gehört. Die zuletzt "
        "gemeldeten Werte werden weiter verwendet, als wären sie aktuell; Zonen, die "
        "davon abhängen, werden damit berechnet, bis wieder Werte kommen.\n\n"
        "Prüfe das Gerät und seine Integration. Hast du das Gerät ersetzt, wähle seine "
        "neuen Entitäten in der Sensorgruppe. Soll der Wert fest sein, nutze stattdessen "
        "die Quelle „Fester Wert“. Aktualisiert die Integration nur alle paar Stunden, "
        "erscheint dieser Hinweis zwischen ihren Updates und bedeutet keinen Ausfall.\n\n"
        "Dieser Hinweis verschwindet von selbst, sobald der Sensor wieder meldet."
    ),
    "es": (
        "Irrigation Plus no tiene noticias de {entities} desde {since}. Los últimos "
        "valores recibidos se siguen usando como si fueran actuales, así que las zonas "
        "que dependen de ellos se calculan con esos valores hasta que lleguen otros "
        "nuevos.\n\n"
        "Revisa el dispositivo y su integración. Si has sustituido el dispositivo, "
        "selecciona sus nuevas entidades en el grupo de sensores. Si el valor debe ser "
        "fijo, usa en su lugar la fuente «Valor estático». Si la integración solo se "
        "actualiza cada pocas horas, este aviso aparece entre sus actualizaciones y no "
        "significa que el sensor haya fallado.\n\n"
        "Este aviso desaparece solo cuando el sensor vuelve a informar."
    ),
    "fr": (
        "Irrigation Plus n’a plus de nouvelles de {entities} depuis {since}. Les "
        "dernières valeurs reçues restent utilisées comme si elles étaient actuelles : "
        "les zones qui en dépendent sont calculées avec ces valeurs jusqu’à l’arrivée de "
        "nouvelles mesures.\n\n"
        "Vérifiez l’appareil et son intégration. Si vous avez remplacé l’appareil, "
        "sélectionnez ses nouvelles entités dans le groupe de capteurs. Si la valeur "
        "doit rester fixe, utilisez plutôt la source « Valeur statique ». Si "
        "l’intégration ne se met à jour qu’à quelques heures d’intervalle, cet avis "
        "apparaît entre ses mises à jour et ne signifie pas que le capteur est en "
        "panne.\n\n"
        "Cet avis disparaît de lui-même dès que le capteur envoie de nouveau des mesures."
    ),
    "it": (
        "Irrigation Plus non riceve notizie da {entities} dal {since}. Gli ultimi valori "
        "ricevuti continuano a essere usati come se fossero attuali, quindi le zone che "
        "ne dipendono vengono calcolate con questi valori finché non ne arrivano di "
        "nuovi.\n\n"
        "Controlla il dispositivo e la sua integrazione. Se hai sostituito il "
        "dispositivo, seleziona le sue nuove entità nel gruppo di sensori. Se il valore "
        "deve restare fisso, usa invece la sorgente «Valore statico». Se l’integrazione "
        "si aggiorna solo ogni poche ore, questo avviso compare tra un aggiornamento e "
        "l’altro e non significa che il sensore sia guasto.\n\n"
        "Questo avviso scompare da solo quando il sensore torna a inviare dati."
    ),
    "nl": (
        "Irrigation Plus heeft sinds {since} niets meer van {entities} gehoord. De "
        "laatst gemelde waarden worden nog steeds gebruikt alsof ze actueel zijn, dus "
        "zones die ervan afhangen worden met die waarden berekend tot er nieuwe "
        "binnenkomen.\n\n"
        "Controleer het apparaat en de integratie ervan. Heb je het apparaat vervangen, "
        "kies dan de nieuwe entiteiten ervan in de sensorgroep. Moet de waarde vast zijn, "
        "gebruik dan de bron ‘Vaste waarde’. Werkt de integratie maar om de paar uur "
        "bij, dan verschijnt deze melding tussen haar updates en betekent ze niet dat de "
        "sensor defect is.\n\n"
        "Deze melding verdwijnt vanzelf zodra de sensor weer meldt."
    ),
    "no": (
        "Irrigation Plus har ikke hørt fra {entities} siden {since}. De sist "
        "rapporterte verdiene brukes fortsatt som om de var aktuelle, så soner som er "
        "avhengige av dem, beregnes med disse verdiene til nye kommer inn.\n\n"
        "Sjekk enheten og integrasjonen. Har du byttet ut enheten, velg de nye "
        "entitetene i sensorgruppen. Hvis verdien skal være fast, bruk heller kilden "
        "«Statisk verdi». Oppdateres integrasjonen bare med noen timers mellomrom, vises "
        "denne meldingen mellom oppdateringene og betyr ikke at sensoren har sviktet.\n\n"
        "Denne meldingen forsvinner av seg selv når sensoren rapporterer igjen."
    ),
    "sk": (
        "Irrigation Plus od {since} nedostal nič od {entities}. Naposledy nahlásené "
        "hodnoty sa naďalej používajú, akoby boli aktuálne, takže zóny, ktoré od nich "
        "závisia, sa počítajú s týmito hodnotami, kým neprídu nové.\n\n"
        "Skontroluj zariadenie a jeho integráciu. Ak si zariadenie vymenil, vyber jeho "
        "nové entity v skupine senzorov. Ak má byť hodnota pevná, použi namiesto toho "
        "zdroj „Statická hodnota“. Ak sa integrácia aktualizuje len raz za niekoľko "
        "hodín, toto upozornenie sa zobrazuje medzi jej aktualizáciami a neznamená "
        "poruchu senzora.\n\n"
        "Toto upozornenie zmizne samo, keď senzor znova začne hlásiť hodnoty."
    ),
}

LABELS = IP / "frontend" / "localize" / "languages"
for lang, new in DESCRIPTIONS.items():
    path = IP / "translations" / f"{lang}.json"
    notice = json.loads(path.read_text(encoding="utf-8"))["issues"]["weather_sensor_stale"]
    label = json.loads((LABELS / f"{lang}.json").read_text(encoding="utf-8"))["panels"][
        "mappings"
    ]["cards"]["mapping"]["sources"]["static"]
    if label not in new:
        sys.exit(f"ABORT {lang}: the panel's static-source label {label!r} is not in the text")
    edit(
        path,
        '"description": ' + json.dumps(notice["description"], ensure_ascii=False),
        '"description": ' + json.dumps(new, ensure_ascii=False),
    )

# --- docs: the section JustChr asked for (6-h polling false-alarms) -------------
edit(
    ROOT / "docs" / "configuration-sensor-groups.md",
    "## Deleting a sensor group\n",
    "## When a sensor goes silent\n"
    "Irrigation Plus checks every five minutes whether the sensors of a sensor group "
    "still report. What counts is a sensor's Home Assistant device: as long as any "
    "entity of that device reports, a value that merely stays the same, such as a rain "
    "gauge on a dry day, counts as alive. A sensor without a device counts for itself. "
    "A sensor whose state is `unavailable` or `unknown` counts as silent whatever its "
    "device does. Values from an `input_number` helper never count as silent.\n"
    "\n"
    "Once a sensor has not reported for three hours, Irrigation Plus shows a repair "
    "notice for its sensor group and fires the `irrigation_plus_weather_stale` event "
    "(see [Events](usage-events.md)). When the sensor reports again, the notice clears "
    "itself and a second event marks the end. Meanwhile the calculation keeps using "
    "the sensor's last value.\n"
    "\n"
    "The three hours are fixed. An integration that updates less often, such as a "
    "cloud service polled every six hours, therefore raises the notice between its "
    "updates even though nothing has failed.\n"
    "\n"
    "A template sensor without a device whose value never changes looks silent too. "
    'If a value is meant to be fixed, use the "Static value" source instead.\n'
    "\n"
    "## Deleting a sensor group\n",
)
