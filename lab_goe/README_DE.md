# V15 Beta 6: virtuelles go-e-Docker-Testlabor

Dieses Labor startet **zwei getrennte Container**: Home Assistant 2026.11 auf `http://127.0.0.1:8125` und eine vollständig **virtuelle** lokale go-e-HTTP-API v2 auf `http://127.0.0.1:8126`. Es gibt weder eine Verbindung zum echten go-e Charger noch zu evcc oder Victron.

**Entwicklungsstand, keine veröffentlichte Beta 6.** Das reale V15-Modul wird gegen einen simulierten Charger getestet. Wie bei Beta 5 sind dessen Antwortzeiten und Fehlerfälle nicht identisch mit realer Hardware.

## Einrichtung unter Windows mit Docker Desktop

1. Die komplette Repository-Verzeichnisstruktur des Zweigs `dev/goe-beta6` entpacken. Die Ordner `lab_goe` und `custom_components` müssen nebeneinander liegen.
2. In PowerShell in `lab_goe` wechseln und `docker compose up -d` ausführen.
3. Im Browser `http://127.0.0.1:8125` öffnen. Ein **neues Testkonto** erstellen, keine vorhandene Home-Assistant-Sicherung übernehmen.
4. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** `V15 Lastmanagement` konfigurieren:
   - Netzleistung: `sensor.v15_test_goe_netzleistung`
   - Grenzwert: **5 kW**, Reserve: **0,5 kW**
   - evcc-Wallboxsteuerung: **Nein**
   - Direkte go-e-Wallboxsteuerung: **Ja**
   - Lokale go-e-IP: **172.28.201.10** (dies ist die Adresse des **Fake-Chargers** im Docker-Netzwerk)
   - Andere Wallbox-Regler deaktiviert: **Ja – nur im vollständig virtuellen Testlabor**
   - Phasen: **3**, min. **6 A**, max. **16 A**, Reserve **300 W**
   - Stabilität: **90 s**, Stellabstand: **30 s**
   - Ladepause zulassen: **Ja – nur im virtuellen Testlabor**
5. Unter **V15** zunächst **Demo Aus**, **Probelauf Ein**, **go-e-Ladestromregelung Aus** einstellen. Die reale Netzsensorlogik nutzt im Labor ausschließlich die künstlichen Lasten.

## Testdaten und Sollverhalten

| Simulierte Grundlast | go-e-Sollstrom | Erwarteter Netzbezug |
|---|---|---|
| -6.000 W | 16 A | 5.040 W |
| -6.000 W | 14 A | 3.660 W |
| -9.000 W | 16 A | 2.040 W |
| +1.500 W | 16 A | 12.540 W (vor Ladepause) |
| +1.500 W | go-e pausiert | 1.500 W |

Die Grundlast kann über die Entität `input_number.v15_goe_grundlast_w` geändert werden.

Bei stabilen Messwerten und ausreichender Viertelstundenabdeckung berechnet V15 ein Zielstromlimit. Anschließend kann ausschließlich **im Testlabor** der Probelauf deaktiviert und **V15 go-e-Ladestromregelung** aktiviert werden. Das ermöglicht die Reduzierung von 16 A auf etwa 14 A. Mit -9.000 W Grundlast sollte V15 schrittweise auf 16 A erhöhen. Bei +1.500 W Grundlast kann der Fake-Charger pausiert und nach erneutem PV-Überschuss wieder freigegeben werden.

## API des Fake-Chargers

Der **Fake-Charger** ist unter `http://127.0.0.1:8126` auf **dem Test-PC** erreichbar, jedoch nicht die echte Wallbox:

- `http://127.0.0.1:8126/lab/state` – aktueller virtueller go-e-Zustand
- `http://127.0.0.1:8126/lab/set?amp=12` – simuliert einen konkurrierenden Eingriff in den Sollstrom
- `http://127.0.0.1:8126/lab/set?frc=2` – simuliert eine fremde erzwungene Freigabe (V15 muss sich deaktivieren)
- `http://127.0.0.1:8126/lab/reset` – virtuellen go-e auf 16 A und Neutral (`frc=0`) zurücksetzen

Der Regler selbst darf **nie** `frc=2` senden. V15 benutzt ausschließlich `frc=1` für seine eigene Ladepause und `frc=0` für deren Freigabe. Externe gleichzeitige Regler sind in dieser Testumgebung *simulierte Konflikte*, im echten Betrieb wären sie vorher zu deaktivieren.

## Sicherheit und Ende des Tests

- Keine IP, Tokens oder Zugangsdaten eines realen Chargers verwenden. Keinerlei echte evcc-/go-e-/Victron-Integration installieren.
- Die Oberfläche ist nur am lokalen Windows-Rechner freigegeben (`127.0.0.1`). Das Docker-Netzwerk ist **nicht vollständig vom Heimnetz isoliert**. Für eine echte Netzisolation wären zusätzliche Firewall-Regeln nötig.
- Die statische Testnetz-IP **172.28.201.10** und das Subnetz **172.28.201.0/24** können mit bestehenden Docker-Netzen kollidieren. In diesem Fall ist eine passende private freie Docker-Subnetzadresse erforderlich.
- Zum Stoppen im Ordner `lab_goe` `docker compose down` ausführen. Den Testaccount und alle gespeicherten Testdaten nur im zugehörigen `lab_goe/config`-Ordner belassen bzw. bei Bedarf dort löschen. Die produktive Home-Assistant-Konfiguration niemals verändern.
