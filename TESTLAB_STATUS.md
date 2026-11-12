# V15 evcc – virtueller Home-Assistant-Teststand

**Entwicklung, nicht für die produktive Anlage installieren.**

## Verifiziert in der lokalen Entwicklungsumgebung

- 63 bestehende unittest-Szenarien/Logiktests erfolgreich (`python -m unittest discover -s tests -q`).
- Python-Dateien einschließlich der neuen `qa_ha`-Tests syntaktisch geprüft.
- Virtuelle HA-Konfiguration und Compose-Datei mit YAML-Parser geprüft.
- Jinja-Templates stichprobenartig gerendert: 16 A x 3 x 230 V = 11.040 W; bei -6.000 W Grundlast: 5.040 W Netzbezug; Modus `off` ergibt 0 W Ladeleistung.

## Auf GitHub mit echter Home-Assistant-Testlaufzeit ausgeführt

- **14 von 14 Integrationstests bestanden** unter Home Assistant 2026.11.0 mit Python 3.14.
- Geprüft: Entitätsregistrierung, sichere Startsperre und Reload, Optionen-Konfigurationsfluss, keine Aktuation ohne Freigabe, Unload und evcc-Maximalstrom per simulierter HA-Service-API.
- Acht zusätzliche Sicherheitsfälle: V15-eigene Ladepause, Wiederfreigabe nach stabiler Leistungsreserve, dauerhaft fehlendes Ladebudget, manuelles `now`, konkurrierende Strombegrenzung, fehlende Befehlsbestätigung, manueller `off`-Modus ohne V15-Eigentum, Netzsensor-Ausfall während einer Pause und Wiederanlaufsperre nach Reload (ein Test ist parametrisiert).
- GitHub-Actions-Lauf: https://github.com/SchreiterC/ha-v15-lastmanagement/actions/runs/42880718053
- Standard-Prüfungen `python-checks` (63 Tests), `hassfest` und `validate-hacs` ebenfalls erfolgreich.

## Interaktiver Docker-Praxistest: bestanden (12.11.2026)

Ein Tester hat die Entwicklungsfassung in einer separaten lokalen Docker-Home-Assistant-Instanz (Port 8124) ausschließlich mit virtuellen Sensoren und einer virtuellen evcc-Wallbox getestet. Die Ergebnisse wurden während des Tests durch Screenshots und Rückmeldungen des Testers bestätigt; es liegt **kein vollständiger exportierter Testlog** vor.

- **Messdaten statt Demo:** Nach Korrektur der Testlabor-Templates um ein minütliches `test_heartbeat`-Attribut wurden die künstlichen Netz- und Ladeleistungswerte als aktuelle Messungen erkannt. Bei -6.000 W Grundlast, 16 A und drei Phasen: 5.040 W Netzbezug, ungefähr 4,46 kW Restbudget und 14 A berechneter Zielstrom, Messabdeckung > 99 %.
- **Aktive Begrenzung:** Der virtuelle Maximalstrom wurde von 16 auf 14 A reduziert. Ladeleistung 9.660 W und Netzbezug 3.660 W.
- **Schrittweise Freigabe:** Nach Erhöhung des simulierten PV-Überschusses auf -9.000 W wurde der Maximalstrom selbstständig von 14 über 15 auf 16 A erhöht.
- **Ladepause:** Bei +1.500 W Grundlast wurde die virtuelle Ladung automatisch pausiert (Modus `off`, Ladeleistung 0 W).
- **Wiederaufnahme:** Nach Rückkehr des PV-Überschusses wurde zunächst der Maximalstrom auf 6 A gesenkt, dann von `off` auf `smart` gewechselt und anschließend stufenweise erhöht.
- **Manueller Moduswechsel:** Der Wechsel des virtuellen evcc-Modus auf `now` wurde respektiert und die V15-evcc-Regelung deaktiviert.
- **Konkurrierende Stromvorgabe:** Eine manuelle Änderung des virtuellen Maximalstroms auf 12 A wurde respektiert und die V15-evcc-Regelung deaktiviert.
- **Integration-Reload:** Nach erneutem Aktivieren der evcc-Regelung und anschließendem Neuladen der V15-Integration blieb die Regelung aus. Der virtuelle Maximalstrom wurde nicht erneut durch V15 geändert.

**Grenze der Prüfung:** Die Tests erfolgten mit virtuellen Home-Assistant-Entitäten, nicht mit echtem evcc-Server, Wallbox oder Fahrzeug. Ein vollständiger Docker-Containerneustart wurde in dieser interaktiven Testserie nicht gesondert bestätigt; getestet wurde das Neuladen der Integration.

## Noch offen

- Praxistest der evcc-Anbindung mit echter Wallbox/echtem evcc in einer kontrollierten Testumgebung.
- Optional: kompletter Docker-Containerneustart und Prüfung des Wiederanlaufverhaltens. Die separate Reload-Sperre ist bereits bestätigt.

**Hinweis zur Testumgebung:** Die frühere lokale Entwicklungsumgebung hatte keinen Docker-Daemon und nur Python 3.13.5. Der Docker-Praxistest erfolgte später separat auf dem Rechner des Testers. Die automatisierten HA-Laufzeittests auf GitHub Actions liefen mit Python 3.14.

## Tests

### Schnelltests (ohne Home Assistant)

```sh
python -m unittest discover -s tests -q
```

### Home-Assistant-Integrationstests (GitHub Actions bzw. separate Python 3.14.2+-Umgebung)

```sh
python -m pip install -r qa_ha/requirements.txt
python -c "import homeassistant; import pytest; raise SystemExit(pytest.main(['-q', 'qa_ha']))"
```

Testfälle: Entitäten und Diagnose, Sperre nach HA-Neustart, Probelauf ohne Aktuation, echte Optionen-Seite, Auswertung von Sensorereignissen und V15-Ladestromreduzierung über die echte HA-Service-API mit virtuellen Zielentitäten.

### Visuelles Testlabor

Siehe `lab_ha/README_DE.md`.

## Branch-Strategie

Die veröffentlichte Beta 4 bleibt auf `main`. Der Entwicklungszweig `dev/evcc-simulator` dokumentiert das Vorhaben. Das Paket hier enthält die neue Beta-5-Codebasis und den vollständigen Testlabor-Aufbau. **Die vollständige Beta-5-Codebasis und die QA-Dateien liegen auf dem Entwicklungszweig. 14 automatisierte HA-Integrationstests und die interaktiven virtuellen Docker-Praxistests sind bestanden. Ein Test mit echter evcc-/Wallbox-Hardware steht aus.**