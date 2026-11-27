# V15 Lastmanagement 0.3.7 – PV-Programmstart, Neustart-Wiederherstellung und österreichische Netzentgelte

**Reguläres Release von V15 Lastmanagement.** Die neue Home-Connect-Startsteuerung und die österreichische Kostenanzeige sind weiterhin **optionale, experimentelle Funktionen**. Bestehende Installationen behalten ihre bisherige Konfiguration. Die gewohnte Lastabschaltung, das vorsichtige Wiedereinschalten, die evcc-Anbindung und Home Connect Pause/Fortsetzen bleiben erhalten.

## Neu: PV-optimierter Home-Connect-Geschirrspülerstart (experimentell)

- Eigenständige, freiwillig aktivierbare Startsteuerung für Home-Connect-Geschirrspüler über die offizielle Home-Assistant-Integration.
- Ermittlung eines voraussichtlich günstigen Startfensters anhand der 15-Minuten-Solarprognose (`wh_period_15m`) über die geschätzte Programmdauer.
- Konfigurierbar: frühester und spätester Start, Laufzeit, Mindest-PV-Ertrag, geschätzte Leistung, zusätzliche Sicherheitsreserve und Dauer einer stabilen Leistungsreserve.
- Vor jedem Versuch Prüfung von gewähltem Geschirrspülprogramm, geschlossener Tür, Fernstart, Fernsteuerung, Konnektivität, aktueller Netzleistung und zuverlässigem V15-Viertelstundenbudget.
- **Einmalige bewusste Freigabe** über einen `input_boolean`. Dieser wird **vor** dem Home-Connect-Startbefehl ausgeschaltet. Keine automatische Wiederholung nach einem fehlgeschlagenen Start. Bestätigung des Betriebszustands `run` und Home-Assistant-Meldung bei Problemen.
- Ein echter Start mit einem NEFF-Home-Connect-Geschirrspüler wurde erfolgreich getestet. Andere Geräte und Modelle sind nicht automatisch freigegeben; bitte individuell prüfen.

**Wichtig:** Vor der Aktivierung eine eventuell bisher verwendete Home-Assistant-Startautomation für dasselbe Gerät deaktivieren. Die Home-Connect-Cloud kann keine sofortige Schaltung garantieren. Verbrauchsspitzen während eines späteren Heizabschnitts sind nicht sicher vorhersagbar.

## Neu: Betriebszustände nach Neustart optional fortsetzen

Zwei getrennte, standardmäßig deaktivierte Optionen:

1. **Lastabschaltung nach Neustart fortsetzen:** Der V15-Schalter für die aktive Lastabschaltung wird nur dann wieder aktiviert, wenn er zuvor eingeschaltet war. Erst gültige und ausreichend vollständige Messwerte erlauben weitere Schalthandlungen.
2. **PV-Startsteuerung nach Neustart fortsetzen:** Der entsprechende V15-Schalter kann ebenfalls wieder aktiviert werden. Eine **alte Startfreigabe wird ausdrücklich nicht übernommen**. Nach vollständigem Home-Assistant-Start muss der Freigabe-Helfer zuerst AUS und dann neu EIN geschaltet werden.

Die Zuständigkeit für vor dem Neustart abgeschaltete Geräte wird nicht übernommen. Die evcc-Livesteuerung bleibt nach einem Neustart weiterhin separat freizugeben.

## Neu: Österreichische Netz-Leistungsentgelte (unverbindliche Vorschau)

Rein informative, **optionale** Sensoren für Anschlüsse auf Netzebene 7:

- **V15 Monatsspitze (lokal beobachtet)**: höchste ausreichend vollständig erfasste Viertelstunden-Netzbezugsleistung des laufenden Monats.
- **V15 Leistungsentgelt (Modell, netto)**: berechnetes monatliches Leistungsentgelt auf Basis der beobachteten Spitze.
- **V15 Leistungsentgelt bei Zielspitze (Differenz, Modell)**: **hypothetischer** Unterschied bei einer niedrigeren Spitze, **keine nachgewiesene Ersparnis**.

Tarifauswahl für **14 österreichische Netzbereiche** einschließlich der separaten Bereiche Graz, Linz, Innsbruck, Klagenfurt und Kleinwalsertal. Wahlweise:

- **Unverbindliche Tarifvorschau**: die **zweistufigen** NE7-Preise aus dem **E-Control-Begutachtungsentwurf der SNE-T-V 2027 vom 29. Oktober 2026**. Diese Preise entsprechen **nicht automatisch** den tatsächlich geltenden Tarifen und insbesondere **nicht den angekündigten Übergangs-/Einheitspreisen einzelner Netzbereiche**.
- **Eigene Tarifwerte**: Cent je kW und Monat für die beiden Leistungsstufen sowie die Mindestverrechnungsleistung selbst einstellen.

Die tatsächlichen Gebühren und Einführungstermine hängen von der rechtskräftigen Verordnung und vom jeweiligen Netzbereich ab. Für die Übergangsphase sind Änderungen in Begutachtung. Die Anzeige **ersetzt keine Stromrechnung** und berücksichtigt nicht alle Netzentgeltbestandteile, Steuern oder Umsatzsteuer. Unvollständige Viertelstunden, fehlende historische Werte und Netzbetreiber-Abweichungen können zu einer zu niedrigen beobachteten Spitze führen. Die erfasste Monatsspitze wird lokal über Neustarts gespeichert. Diese Sensoren verändern die V15-Laststeuerung **nicht**.

Quellen: [E-Control: SNE-T-V 2027 – Begutachtung](https://www.e-control.at/de/begutachtungsentwurf-systemnutzungstarife-verordnung-2027) · [E-Control: Tarifgrundlagen](https://www.e-control.at/de/konsumenten/faq-neue-tarifstruktur) · [SNE-G-V, BGBl. II Nr. 299/2026](https://www.ris.bka.gv.at/Dokumente/BgblAuth/BGBLA_2026_II_299/BGBLA_2026_II_299.html)

## Verbesserungen

- Deutsche und englische Übersetzungen der zusätzlichen Optionen und erläuternde Hilfetexte.
- Robustere Erkennung der Home-Connect-Entitäten mit konkreter Fehlerdiagnose.
- Zusätzliche Tests für PV-Planung, Neustartzustände, Gerätesicherheitsprüfungen, Viertelstundenmessung und Tarifrechnung.
- Kennzeichnung und Dokumentation der Einschränkungen experimenteller Funktionen.

## Aktualisierung

1. Im **Home Assistant Marketplace** V15 Lastmanagement auf **0.3.7** aktualisieren und Home Assistant vollständig neu starten.
2. Bestehende V15-Einstellungen bleiben erhalten. Neue Funktionen sind **optional**.
3. Unter **Einstellungen → Geräte & Dienste → V15 Lastmanagement → Konfigurieren** die gewünschten Optionen aktivieren.
4. Für PV-Programmstart den vorgesehenen Home-Connect-Geschirrspüler und den einmaligen Freigabe-Helfer auswählen. Die bisherige Startautomation für dasselbe Gerät deaktivieren.
5. Nach der Konfiguration einen kontrollierten Test mit der eigenen Anlage durchführen.

## English summary

**V15 Lastmanagement 0.3.7** adds an experimental, opt-in Home Connect dishwasher PV start based on 15-minute solar forecasts and V15 demand headroom, including one-shot manual authorization and confirmation. Two independent, default-OFF options restore the previously enabled live shedding and PV start controller switches after Home Assistant restarts; old dishwasher start authorization is **never** reused. An optional, informational Austrian grid-level-7 monthly capacity charge preview covers 14 network areas, or custom rates. The regional values reflect a **nonbinding October 2026 consultation draft**, not necessarily the effective 2027 transitional rates. Locally measured peaks and modeled charges may differ from invoices and are never guaranteed savings. Existing load control, evcc and Home Connect pause/resume remain available.
