# V15 evcc – virtueller Home-Assistant-Teststand

**Entwicklung, nicht für die produktive Anlage installieren.**

## Verifiziert in der lokalen Entwicklungsumgebung

- 63 bestehende unittest-Szenarien/Logiktests erfolgreich (`python -m unittest discover -s tests -q`).
- Python-Dateien einschließlich der neuen `qa_ha`-Tests syntaktisch geprüft.
- Virtuelle HA-Konfiguration und Compose-Datei mit YAML-Parser geprüft.
- Jinja-Templates stichprobenartig gerendert: 16 A x 3 x 230 V = 11.040 W; bei -6.000 W Grundlast: 5.040 W Netzbezug; Modus `off` ergibt 0 W Ladeleistung.

## Auf GitHub mit echter Home-Assistant-Testlaufzeit ausgeführt

- **6 von 6 Integrationstests bestanden** unter Home Assistant 2026.11.0 mit Python 3.14.
- Geprüft: Entitätsregistrierung, sichere Startsperre und Reload, Optionen-Konfigurationsfluss, keine Aktuation ohne Freigabe, Unload und evcc-Maximalstrom per simulierter HA-Service-API.
- GitHub-Actions-Lauf: https://github.com/SchreiterC/ha-v15-lastmanagement/actions/runs/42878847595
- Standard-Prüfungen `python-checks` (63 Tests), `hassfest` und `validate-hacs` ebenfalls erfolgreich.

## Noch nicht ausgeführt

- Docker-Compose-Start und Sichtprüfung der Konfigurationsoberfläche.
- Reale evcc-Netzwerk- und Wallbox-Kommunikation (absichtlich ausgeschlossen).

**Grund:** Die Ausführungsumgebung enthält nur Python 3.13.5 und keinen Docker-Daemon. Home Assistant 2026.11.0 benötigt Python >= 3.14.2. Der Paketindex ist in dieser Umgebung nicht erreichbar. Die GitHub-Actions-Vorlage verwendet Python 3.14 und die offizielle pytest-homeassistant-Version 2026.11.0.

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

Die veröffentlichte Beta 4 bleibt auf `main`. Der Entwicklungszweig `dev/evcc-simulator` dokumentiert das Vorhaben. Das Paket hier enthält die neue Beta-5-Codebasis und den vollständigen Testlabor-Aufbau. **Die vollständige Beta-5-Codebasis und die QA-Dateien sind auf dem Entwicklungszweig. Die 6 HA-Integrationstests haben den GitHub-Actions-Lauf erfolgreich bestanden. Die optionale Docker-Oberfläche und echte Wallbox wurden nicht getestet.**