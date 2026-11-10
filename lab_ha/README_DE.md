# V15 – Separate virtuelle Home-Assistant-Instanz

Diese Testumgebung verwendet einen eigenen Home-Assistant-Container mit virtuellen Sensoren und Schaltern. **Sie ist nicht mit der produktiven Anlage verbunden.** Die Portfreigabe erfolgt nur an `127.0.0.1` des Testrechners.

## Start (optional, Windows mit Docker Desktop)

1. Ein Verzeichnis mit dem kompletten Testlabor entpacken; `lab_ha/compose.yaml` und der Ordner `custom_components/v15_lastmanagement` müssen in ihrer Ordnerstruktur erhalten bleiben.
2. In einem Terminal im Verzeichnis `lab_ha` `docker compose up -d` ausführen.
3. Im Browser auf **dem Testrechner** `http://127.0.0.1:8124` öffnen und ein neues, rein lokales Testkonto einrichten.
4. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach `V15 Lastmanagement` suchen.
5. In V15 diese simulierten Entitäten wählen:

| Einstellung | Test-Entität |
|---|---|
| Netzleistung | `sensor.v15_test_netzleistung` |
| evcc Maximalstrom | `select.v15_test_evcc_maximalstrom` |
| evcc Modus | `select.v15_test_evcc_modus` |
| evcc Ladeleistung | `sensor.v15_test_evcc_ladeleistung` |
| evcc Phasen | `sensor.v15_test_phasen` |
| Grenzwert / Reserve | 5 kW / 0,5 kW |
| Regelung | Erst Probelauf, danach in diesem Testlabor live |

Die vorhandenen virtuellen Helfer unter `input_number`/`input_select` ersetzen Haushaltslast, PV-Erzeugung, evcc-Lademodus und Lade-Maximalstrom. Ein geänderter virtueller Maximalstrom bewirkt direkt eine Änderung der virtuellen Ladeleistung. Das ist **kein** realistisches Fahrzeugprotokoll (Ladeverzögerung, Stromrampen, Kommunikationsprobleme fehlen).

## Grenzen und Sicherheit

- Docker Desktop ist **nur für den optionalen visuellen Test** erforderlich; die Python/HA-Testjobs laufen später in GitHub Actions.
- Keine Adresse, Tokens, SSH-Zugänge oder Konfigurationssicherung der echten Anlage übernehmen.
- Kein `network_mode: host`, keine Hardwaregeräte und keine evcc-/Victron-Integration hinzufügen.
- Dieser Container ist absichtlich nicht als dauerhafte Installation gedacht. Sein Netzwerk ist nicht physisch vom LAN getrennt. Es werden jedoch keine echten Integrationen oder Zugangsdaten eingerichtet. Für vollständige Netzisolation müsste zusätzlich die Docker-Netzwerkkommunikation gesperrt werden.
- Beim Stopp unter `lab_ha`: `docker compose down`. Zum vollständigen Entfernen danach den lokalen `lab_ha/config`-Ordner löschen (nicht die produktive Konfiguration).

## Hinweis zu negativen Netzleistungen

Die berechnete virtuelle Ladeleistung berücksichtigt Modus `smart`, 1/3 Phasen und eingestellte Ampere. Die virtuelle Netzleistung addiert diese zur frei wählbaren Haushaltsgrundlast. Negative Grundlast bedeutet virtuellen PV-Überschuss. Die tatsächliche Messdatengüte der Tests entspricht **nicht** einem echten Smart Meter.
