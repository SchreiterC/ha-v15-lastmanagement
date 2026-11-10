# Virtuelles Testlabor für V15 und evcc

**Status:** Entwicklungsplanung und lokaler Prototyp. Die veröffentlichte Beta 4 auf `main` bleibt unverändert.

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
- **Stufe B:** Home-Assistant-Integrationstests mit realem HA-Testframework und simulierten Geräten; dadurch auch Service- und Entitätsregistrierung prüfen.
- **Stufe C (optional):** Getrennte Home-Assistant-/evcc-Containerinstanz mit rein virtueller Hardware.
- **Stufe D:** Freiwilliger Praxis-Betatest durch geeignete Tester, erst danach Veröffentlichung.

## Sicherheit
Dieser Zweig darf nicht mit dem stabil veröffentlichten Release verwechselt werden. Keine Zugangsdaten, IP-Adressen produktiver Geräte oder automatischen Verbindungen zum Heimnetz verwenden. Simulierte Ergebnisse sind kein Beweis für korrektes Verhalten einer echten Wallbox.

## Stand der zweiten Teststufe (10.11.2026)

Im lokalen Entwicklungspaket `v15_evcc_ha_testlabor_2026_11.zip` sind inzwischen folgende Dateien vorbereitet:

- `qa_ha/test_ha_runtime.py`: echte HA-Instanz per pytest-Fixture, Test der Entitätsregistrierung, Schalter-Aktivierung, Reload-Sperre, Konfigurationsfluss und der evcc-Servicebefehle an virtuelle Ziele
- `qa_ha/requirements.txt` und `pytest.ini`: HA-2026.11-Testabhängigkeiten
- `.github/workflows/ha-runtime-tests.yml`: Vorlage für einen isolierten GitHub-Actions-Test mit Python 3.14
- `lab_ha/compose.yaml` und `lab_ha/config/configuration.yaml`: optionale Home-Assistant-Containerinstanz mit virtuellen Sensoren und Template-Selects
- `lab_ha/README_DE.md`: Inbetriebnahme nur auf einem separaten Testrechner

**Verifiziert:** 63 bestehende Tests und statische YAML-/Python-Prüfungen. **Noch offen:** die neuen Tests in echter HA-Laufzeit ausführen und die Containeroberfläche prüfen. Python 3.13 in der lokalen Umgebung reicht nicht aus: HA 2026.11 erfordert Python 3.14.2 oder neuer. Die vollständigen Beta-5- und Testdateien liegen nun **in diesem Entwicklungszweig**. Die HA-Testumgebung verwendet die offizielle Bibliothek `pytest-homeassistant==2026.11.0`. Das veröffentlichte `main` bleibt unberührt.
