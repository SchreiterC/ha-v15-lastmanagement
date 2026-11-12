# V15 Lastmanagement 0.3.5 Beta 5 – evcc-Pilot

**Vorabversion. Die neue evcc-Steuerung wurde mit virtuellen Home-Assistant-Entitäten getestet, jedoch noch nicht mit einer echten evcc-Installation und Wallbox.** Die Begrenzung von Viertelstunden-Lastspitzen ist nicht geeicht oder garantiert.

## Neu in Beta 5

- **Optionale evcc-Ladestromsteuerung:** Die bestehenden evcc-Entitäten (Maximalstrom, Modus, Ladeleistung und optional Phasenzahl) werden in V15 ausgewählt. Keine direkte evcc-API-Verbindung notwendig.
- **Konservatives 15-Minuten-Ladebudget:** V15 senkt den erlaubten Ladestrom bei Bedarf und erhöht ihn erst nach stabiler Reserve in 1-A-Schritten.
- **Optionale Ladepause:** Reicht das Budget für 6 A nicht aus, kann V15 nach ausdrücklicher Freigabe von `smart` auf `off` schalten. Bei erneuter Freigabe setzt V15 **zuerst 6 A** und wechselt erst danach zurück zu `smart`.
- **Eigenständiger Freigabeschalter und Zielstromsensor:** evcc wird nicht automatisch aktiviert. Nach einem Neustart oder Neuladen bleibt die evcc-Regelung ausgeschaltet.
- **Konflikt- und Messwertschutz:** Bei externen Änderungen von Lademodus/Maximalstrom, fehlender Stellbestätigung oder ungültigen Messwerten stoppt V15 weitere evcc-Befehle.
- **Bestandsfunktionen bleiben erhalten:** Abschaltung und optionale Wiedereinschaltung unkritischer Lasten werden nicht durch die evcc-Erweiterung ersetzt.
- Deutsche und englische Konfigurationsfelder einschließlich Hilfetexten.

## Installation / Update (Home Assistant 2026.11 oder neuer)

1. [V15 im Home Assistant Marketplace öffnen](https://my.home-assistant.io/redirect/marketplace_repository/?owner=SchreiterC&repository=ha-v15-lastmanagement&category=integration). Bei Bedarf das öffentliche Repository über **Marketplace → Add from link** ergänzen.
2. Für diese Vorabversion auf der Marketplace-Geräteseite die standardmäßig deaktivierte Entität **Pre-release** aktivieren und deren Schalter einschalten.
3. Auf **0.3.5b5** aktualisieren und Home Assistant vollständig neu starten. **Bestehende V15-Integration nicht löschen.**
4. Die evcc-Anbindung bei Bedarf über **V15 Lastmanagement → Konfigurieren** ausdrücklich einrichten. Ohne diesen Schritt arbeitet V15 wie bisher.
5. Zunächst den **Probelauf ohne Schalten** mit echten Messwerten prüfen. Die evcc-Livesteuerung erst nach Prüfung der Entitäten, Lademodi und Konflikte mit anderen Automationen bewusst einschalten.

**Wichtig:** Bereits durch V15 veränderte Stromlimits oder Ladepausen werden nach Deaktivierung/Neuladen nicht automatisch zurückgesetzt. Den Zustand gegebenenfalls manuell in evcc kontrollieren.

## Teststand und Grenzen

- 63 Logiktests und 14 Home-Assistant-Integrationstests in GitHub Actions erfolgreich.
- Acht interaktive Docker-Praxisszenarien mit **virtueller** Wallbox bestanden: Zielstromberechnung, Begrenzung, Erhöhung, Pause, Wiederaufnahme, manueller `now`-Wechsel, konkurrierende Maximalstromänderung und Reload-Sperre.
- **Noch nicht getestet:** echte evcc-/Wallbox-Kommunikation, Hardware-Verzögerungen und ein vollständiger physischer Ladezyklus. Keine Garantie, eine vertraglich relevante Viertelstunden-Leistungsgrenze einzuhalten.

Details: [README](https://github.com/SchreiterC/ha-v15-lastmanagement#neu-in-beta-5-optionale-evcc-ladestrombegrenzung) · [Changelog](https://github.com/SchreiterC/ha-v15-lastmanagement/blob/main/CHANGELOG.md) · [Teststatus](https://github.com/SchreiterC/ha-v15-lastmanagement/blob/main/TESTLAB_STATUS.md)

---

## English summary

**Beta 5 introduces optional evcc charging-current control through existing Home Assistant entities.** It limits the maximum current against a conservative 15-minute grid budget, supports opt-in charging pauses and controlled resumption, and stops controlling evcc when manual changes or measurement issues are detected. Control is always opt-in and remains disabled after a reload.

Automated logic and Home Assistant runtime tests passed, along with interactive Docker tests using a **virtual** charging point. **No real evcc server or wallbox has been tested yet.** This is a pre-release and not a certified demand-limit controller.
