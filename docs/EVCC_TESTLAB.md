# Virtuelles Testlabor für V15 und evcc

**Status:** Automatisierte HA-Integrationstests und interaktive Docker-Praxistests mit virtueller Wallbox erfolgreich. Keine Tests mit echter evcc-/Wallbox-Hardware. Die veröffentlichte Beta 4 auf `main` bleibt unverändert.

## Ziel
V15 mit echten Regelfunktionen, aber ausschließlich virtuellen Home-Assistant-Entitäten und einer virtuellen Wallbox prüfen. Keine Verbindung zur produktiven Installation und keine Hardware-Schaltbefehle.

## Architektur
1. Simulierter Haushalt: Netzleistung = Grundlast + Ladeleistung; negative Grundlast entspricht PV-Überschuss.
2. Simulierter evcc-Ladepunkt: 1/3 Phasen, 6–16 A, Modi `smart` und `off`.
3. V15-Logik: echter Rechen- und Reglercode der Entwicklungsversion.
4. Fake-Home-Assistant: Zustandswerte und aufgezeichnete Stellbefehle statt realer Services.
5. Beschleunigte Zeit: mehrere Viertelstunden in Sekunden; CSV-Protokolle für Messwerte und Entscheidungen.

## Vorgesehene Szenarien
- PV-Einbruch: Strom reduzieren oder das Laden pausieren
- PV-Rückkehr: erst nach stabiler Reserve wieder freigeben, anschließend stufenweise erhöhen
- Hohe Grundlast: keine Freigabe ohne 6-A-Budget
- Netzsensor fehlt oder ist veraltet: keine ungesicherten Befehle
- Benutzer wechselt evcc-Modus: V15 beendet eigene Steuerung
- Neustart und Viertelstundenwechsel: kein Übernehmen alter Steuerberechtigungen
- Nicht bestätigte evcc-Befehle: nach Ablauf der Rückmeldefrist keine weitere Regelung

## Teststufen
- **Stufe A:** Rechenlogik und Controller mit Python-Fakes und beschleunigter Uhr. Lokal erste 63 Tests erfolgreich, darunter vier neue Szenariotests.
- **Stufe B (bestanden):** 14 Integrationstests mit Home Assistant 2026.11 und virtuellen Geräten erfolgreich, einschließlich Service-Aufrufen und Entitätsregistrierung.
- **Stufe C (bestanden):** Separate Docker-Home-Assistant-Instanz mit rein virtuellen Sensoren und virtueller evcc-Wallbox, interaktiv am 12.11.2026 geprüft. Kein echter evcc-Server im Test.
- **Stufe D:** Freiwilliger Praxis-Betatest durch geeignete Tester, erst danach Veröffentlichung.

## Sicherheitsregressionen (10.11.2026)

Acht zusätzliche automatisierte HA-Testfälle validieren eigene Ladepause und kontrolliertes Wiederaufnehmen, fehlendes Ladebudget, manuelle Moduswechsel (`now`/`off`), konkurrierende Maximalstromregelung, 20-s-Rückmeldesicherung, Netzsensor-Ausfall und ausbleibende automatische Wiederaufnahme nach Reload. Die Tests verwenden ausschließlich virtuelle Entitäten und einen lokal abgefangenen `select.select_option`-Service. Der zwischenzeitlich entdeckte Diagnosefehler, der einen Sicherheitsabschaltgrund wieder überschrieb, wurde in Beta 5 auf diesem Zweig korrigiert.

## Sicherheit
Dieser Zweig darf nicht mit dem stabil veröffentlichten Release verwechselt werden. Keine Zugangsdaten, IP-Adressen produktiver Geräte oder automatischen Verbindungen zum Heimnetz verwenden. Simulierte Ergebnisse sind kein Beweis für korrektes Verhalten einer echten Wallbox.

## Stand der zweiten Teststufe (10.11.2026)

Im lokalen Entwicklungspaket `v15_evcc_ha_testlabor_2026_11.zip` sind inzwischen folgende Dateien vorbereitet:

- `qa_ha/test_ha_runtime.py`: echte HA-Instanz per pytest-Fixture, Test der Entitätsregistrierung, Schalter-Aktivierung, Reload-Sperre, Konfigurationsfluss und der evcc-Servicebefehle an virtuelle Ziele
- `qa_ha/requirements.txt` und `pytest.ini`: HA-2026.11-Testabhängigkeiten
- `.github/workflows/ha-runtime-tests.yml`: Vorlage für einen isolierten GitHub-Actions-Test mit Python 3.14
- `lab_ha/compose.yaml` und `lab_ha/config/configuration.yaml`: optionale Home-Assistant-Containerinstanz mit virtuellen Sensoren und Template-Selects
- `lab_ha/README_DE.md`: Inbetriebnahme nur auf einem separaten Testrechner

**Verifiziert:** 63 bestehende Logiktests, statische YAML-/Python-Prüfungen und **14 von 14 Integrationstests in einer echten Home-Assistant-2026.11-Testlaufzeit auf GitHub Actions**, einschließlich eines virtuellen `select.select_option`-Stellbefehls. [Erfolgreicher Testlauf](https://github.com/SchreiterC/ha-v15-lastmanagement/actions/runs/42880718053). **Noch offen:** freiwillige Tests mit echtem evcc und echter Wallbox. Python 3.13 in der lokalen Umgebung reicht nicht aus: HA 2026.11 erfordert Python 3.14.2 oder neuer. Die vollständigen Beta-5- und Testdateien liegen nun **in diesem Entwicklungszweig**. Die HA-Testumgebung verwendet die offizielle Bibliothek `pytest-homeassistant==2026.11.0`. Das veröffentlichte `main` bleibt unberührt.


## Interaktive Docker-Tests (12.11.2026)

Der Tester bestätigte in seiner lokalen Home-Assistant-Docker-Instanz (Port 8124) folgende Szenarien:

1. Nach Ergänzung eines minütlichen `test_heartbeat`-Attributs für die zwei virtuellen Leistungssensoren war die Messabdeckung stabil und die reale V15-Berechnung im Probelauf aktiv: 5,04 kW Netzleistung bei -6.000 W Grundlast, 16 A und drei Phasen, ungefähr 4,46 kW Restbudget und 14 A Zielstrom.
2. Mit aktiver V15-evcc-Regelung wurde der virtuelle Maximalstrom auf 14 A begrenzt (9,66 kW virtuelle Ladeleistung, 3,66 kW Netzbezug).
3. Bei höherem PV-Überschuss erfolgte die Erhöhung von 14 auf 15 und 16 A schrittweise.
4. Bei +1.500 W Grundlast wurde die Ladung automatisch pausiert (Modus `off`).
5. Nach wieder ausreichender Reserve wurde zuerst das Limit auf 6 A gestellt, erst danach der Modus auf `smart` gesetzt und der Maximalstrom wieder erhöht.
6. Ein manueller Wechsel zu `now` wurde respektiert, und V15 deaktivierte seine Steuerung.
7. Eine manuelle Änderung des maximalen Stroms auf 12 A wurde erkannt und respektiert, die V15-Steuerung wurde deaktiviert.
8. Beim Neuladen der V15-Integration blieb die evcc-Steuerung deaktiviert und der zuletzt gesetzte Maximalstrom unverändert.

Diese Ergebnisse sind durch Tester-Rückmeldungen und teilweise Screenshots belegt, nicht durch einen exportierten vollständigen Laufzeitlog. **Nicht durchgeführt:** echte evcc-Netzwerk-/Wallbox-Kommunikation und ein separat bestätigter vollständiger Docker-Containerneustart. Der Test der Wiederanlaufsperre bezog sich auf das **Neuladen der V15-Integration**.
