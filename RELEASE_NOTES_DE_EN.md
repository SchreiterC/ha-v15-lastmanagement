# V15 Lastmanagement – Beta 4 (v0.3.5b4)

## Deutsch

Diese Beta enthält Verbesserungen am Einrichtungsdialog der automatischen Wiedereinschaltung.

- Einheitliche deutsche Beschriftungen für Abschaltung und Wiedereinschaltung.
- Verständliche Erläuterungen unmittelbar an den Einstellungsfeldern.
- Auf der zweiten Seite wird erklärt, warum für jeden ausgewählten Schalter eine **konservativ geschätzte maximale Leistungsaufnahme in Watt** eingetragen werden muss. Die ausgewählten Schalter werden zusätzlich aufgelistet.
- Englische Übersetzungen ebenfalls ergänzt und abgestimmt.
- Die bisherige Abschalt- und Wiedereinschaltlogik, Konfiguration und Entitäten wurden **nicht verändert**.

**Hinweis:** Die deutschen Dialogtexte und die automatische Wiedereinschaltung wurden in einer realen Home-Assistant-Installation erfolgreich erprobt. Weitere Sicherheitstests (insbesondere Messwertausfall und Neustart) stehen noch aus. Bitte nach dem Update Home Assistant neu starten und die Einstellungen erneut öffnen. Bei Anzeigeproblemen ein [GitHub Issue](https://github.com/SchreiterC/ha-v15-lastmanagement/issues) erstellen.

Die aktive Laststeuerung ist weiterhin experimentell. Teste nur mit unkritischen Verbrauchern.

---

## English

This beta improves the setup and options screens for automatic load restoration.

- Clear German labels for load shedding and restoration settings.
- Informative per-field help texts.
- The second page explains why a **conservative maximum power estimate in watts** is required for each selected switch, and lists the selected switches.
- English translations reviewed and aligned with German.
- No changes to load shedding, restoration logic, configuration values, or existing entities.

**Note:** The German dialogs and automatic load restoration have been successfully tested in one live Home Assistant installation. Additional safety tests (particularly stale measurements and restarts) are pending. Restart Home Assistant after updating, then reopen the options. Please report issues on [GitHub](https://github.com/SchreiterC/ha-v15-lastmanagement/issues).

Live load control remains experimental. Use only non-critical test loads.
