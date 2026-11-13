# V15 Lastmanagement 0.3.5 – Erstes reguläres Release

**Erste reguläre Veröffentlichung von V15 Lastmanagement für Home Assistant 2026.11 oder neuer.** Version 0.3.5 basiert auf der geprüften Beta 5 (`0.3.5b5`). Die Kernfunktionen sind regulär verfügbar. Die **optionale evcc-Anbindung bleibt ausdrücklich experimentell**.

## Kernfunktionen

- Überwachung der Netzleistung in festen Viertelstunden (:00/:15/:30/:45), inklusive aktueller Leistung, gemessenem Durchschnitt, Viertelstundenprognose, Messabdeckung und Restbudget.
- Konfigurierbare Leistungsgrenze und Sicherheitsreserve sowie priorisierte Abschaltung ausgewählter **unkritischer** Verbraucher.
- Auf Wunsch automatische Wiedereinschaltung **ausschließlich von Verbrauchern, die V15 selbst abgeschaltet hat**, mit Mindest-Ausschaltdauer, stabiler Reserve und zusätzlichem Leistungsabstand.
- Probelauf ohne Schaltbefehle, künstliche Demo-Messwerte und ausführliche Diagnose.
- Nach jedem Neustart/Neuladen bleibt die aktive Steuerung ausgeschaltet. Bisherige Einstellungen und Entitätskennungen bleiben erhalten.

## Experimentell: evcc-Ladestromregelung

Die in Beta 5 eingeführte Anbindung über bestehende Home-Assistant-evcc-Entitäten ist weiterhin im Paket enthalten:

- Konservatives 15-Minuten-Ladebudget und schrittweise Anpassung des Maximalstroms.
- Optionale Ladepause bei zu geringem Budget sowie kontrollierte Wiederaufnahme.
- Erkennung unzuverlässiger Messwerte, ausbleibender Bestätigung und externer/manueller Regleränderungen.
- Die evcc-Steuerung muss **gesondert eingerichtet und bei jedem Neustart bewusst aktiviert** werden.

**Wichtige Einschränkung:** Die evcc-Erweiterung wurde in automatisierten Home-Assistant-Tests und mit einer virtuellen Wallbox in einem getrennten Docker-Testlabor geprüft. **Ein Test mit echtem evcc-Server, Wallbox und Fahrzeug fehlt.** Die Einstufung als reguläres Release ist **keine Freigabe dieser experimentellen Funktion für den ungeprüften produktiven Betrieb**. Andere Regler, die denselben evcc-Maximalstrom oder Lademodus schreiben, müssen für einen kontrollierten Test deaktiviert werden.

## Teststand

- 63 Logik-/Unittests und 14 Home-Assistant-Integrationstests mit der Beta-5-Codebasis bestanden.
- Acht interaktive Docker-Szenarien mit ausschließlich virtueller Wallbox bestanden (Strombegrenzung, schrittweise Erhöhung, Ladepause, Wiederaufnahme, manuelle Eingriffe und Neuladen der Integration).
- Release-0.3.5-Prüfungen werden vor Veröffentlichung erneut ausgeführt. Gegenüber Beta 5 wurden keine Änderungen an der eigentlichen Regellogik vorgenommen.

## Installation und Update

1. [V15 Lastmanagement im Home Assistant Marketplace öffnen](https://my.home-assistant.io/redirect/marketplace_repository/?owner=SchreiterC&repository=ha-v15-lastmanagement&category=integration). Falls noch nicht vorhanden, das [Repository](https://github.com/SchreiterC/ha-v15-lastmanagement) als benutzerdefiniertes Integrations-Repository hinzufügen.
2. Die **reguläre Version 0.3.5** auswählen und installieren beziehungsweise aktualisieren. **Die Pre-release-Option ist nicht erforderlich.**
3. **Home Assistant vollständig neu starten.** Eine vorhandene V15-Integration **nicht löschen**.
4. Die Konfiguration, Grenzwerte, Reserven und Schalter prüfen. Vor jeder aktiven Steuerung zunächst den **Probelauf ohne Schalten** verwenden.

Die in der Entwicklung befindliche direkte go-e-Anbindung ist **nicht** Bestandteil dieses Releases.

## Sicherheit

V15 ersetzt keinen geeichten Zähler und garantiert **nicht**, dass vertraglich relevante Viertelstunden-Leistungsspitzen stets unter einem Schwellwert bleiben. Keine medizinischen, lebenswichtigen oder sonst sicherheitskritischen Verbraucher mit V15 schalten. Eine automatische Rückschaltung nach Neustart oder Fehler findet nicht statt.

Weitere Informationen: [README](https://github.com/SchreiterC/ha-v15-lastmanagement/blob/main/README.md) · [Changelog](https://github.com/SchreiterC/ha-v15-lastmanagement/blob/main/CHANGELOG.md) · [Teststatus](https://github.com/SchreiterC/ha-v15-lastmanagement/blob/main/TESTLAB_STATUS.md)

---

## English summary

**V15 Lastmanagement 0.3.5 is the first regular GitHub release**, based on Beta 5. Its regular core features include quarter-hour grid-demand monitoring, conservative load shedding and opt-in restoration of loads previously switched off by V15, dry-run mode and diagnostics.

**Experimental evcc control remains opt-in and has not been tested with a real evcc server, wallbox or vehicle.** Successful automated and virtual Docker tests do not certify real hardware behavior. V15 is not a revenue-grade or guaranteed grid-demand limiting system.

Home Assistant 2026.11 or newer is required. Install or update version 0.3.5 through the built-in Marketplace without enabling pre-releases, then restart Home Assistant. Existing integration configuration should be retained. The future direct go-e backend is not included in this release.
