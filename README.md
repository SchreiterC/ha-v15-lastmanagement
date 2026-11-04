# V15 Lastmanagement für Home Assistant

![V15 Logo](custom_components/v15_lastmanagement/brand/logo.png)

**Öffentliche Testversion 0.3.5b1 – nicht als abrechnungsgenauer oder zertifizierter Leistungsbegrenzer verwenden.**

V15 überwacht den Netzbezug in festen, an der Uhrzeit ausgerichteten 15-Minuten-Blöcken (00/15/30/45). Das Projekt stellt sechs Messwertsensoren, einen Diagnosesensor, drei Binärsensoren sowie drei Steuerschalter bereit. Der Anwender wählt einen vorhandenen Leistungssensor und optional schaltbare, unkritische Verbraucher im Einrichtungsdialog.

## Fähigkeiten

- Viertelstundenausrichtung nach lokaler Home-Assistant-Zeit, statt gleitendem Zeitfenster.
- Positive Netzbezugsleistung in W oder kW; umgekehrtes Vorzeichen konfigurierbar.
- Messabdeckung, Durchschnitt, Projektion, Energie, Restbudget und verständliche Diagnose.
- Simulation mit echten Messwerten ohne Eingriff in Geräte.
- Demo mit künstlichen Daten ohne reale Schalthandlungen.
- Optionales, ausdrücklich aktiviertes **einseitiges Abschalten** gewählter `switch`-Entitäten nach Priorität. Kein automatisches Wiedereinschalten.
- Aktive Abschaltung bleibt nach jedem Neustart oder Neuladen ausgeschaltet.

## Installation über HACS (benutzerdefiniertes Repository)

1. In HACS über das Menü **Benutzerdefinierte Repositories** die URL des veröffentlichten GitHub-Repositories eintragen, Kategorie **Integration**.
2. **V15 Lastmanagement** herunterladen und Home Assistant neu starten (insbesondere bei Updates).
3. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** „V15 Lastmanagement“ auswählen. Bei einem bereits vorhandenen Konfigurationseintrag erscheint die Integration unmittelbar.
4. Netzleistungssensor, Grenzwert, Reserve und gegebenenfalls abschaltbare Schalter auswählen.
5. Zuerst die Simulation ohne Schalten testen.

Manuell: den Ordner `custom_components/v15_lastmanagement` in das entsprechende Home-Assistant-Konfigurationsverzeichnis kopieren und Home Assistant neu starten.

## Einstellungen

| Option | Funktion |
|---|---|
| Netzleistungssensor | W/kW; positive Werte müssen Netzbezug anzeigen |
| Grenzwert (kW) | Zielwert für die feste Viertelstunde, standardmäßig 5 kW |
| Reserve (kW) | Sicherheitsabstand zum Zielwert, standardmäßig 0,5 kW |
| Vorzeichen umkehren | Für Netzzähler, deren Netzbezug negative Werte liefert |
| Maximales Sensoralter | Ab welcher Verzögerung Messwerte ungültig werden |
| Abschaltbare Schalter | Optional, in Abschaltreihenfolge; nur `switch`-Entitäten |

## Drei Betriebsmodi

- **V15 Demo mit künstlichen Messwerten**: zeigt einen synthetischen Lastverlauf, schaltet nie reale Verbraucher.
- **V15 Probelauf ohne Schalten**: wertet echte Sensoren aus und beschreibt eine mögliche Abschaltentscheidung; keine Schaltbefehle.
- **V15 Aktive Lastabschaltung**: schaltet bei einer prognostizierten Grenzwertüberschreitung ausgewählte eingeschaltete Schalter ab, sofern Messwerte mindestens 60 Sekunden und zu mindestens 95 % des laufenden Fensters abgedeckt sind. Zwischen Abschaltversuchen liegen mindestens 30 Sekunden. Manuelles Wiedereinschalten erforderlich.

**Nie kritische Verbraucher (medizinische Geräte, Server mit Datenverlustgefahr, Sicherheitsgeräte, Heizungsschutz, etc.) als abschaltbare Lasten konfigurieren.** Keine parallel laufende Steuerung derselben Schalter ohne abgestimmte Prioritäten verwenden.

## Berechnung und Grenzen

- Ein Zeitblock beginnt auf :00, :15, :30 oder :45; die Werte werden beim nächsten Block neu gebildet.
- Messleistung wird aus regelmäßigen Abfragen integriert; die erste unvollständige Viertelstunde und Zeiträume mit Sensorlücken sind nicht abrechnungsgenau.
- Netzbezug wird mit `max(0, Leistung)` berechnet; Einspeisung wird **nicht** dagegen saldiert.
- Prognose nimmt an, dass die aktuelle Netzbezugsleistung bis zum Viertelstundenende konstant bleibt.
- Restbudget ist auf `Grenzwert - Reserve` beschränkt, damit gegen Quartalsende keine extremen rechnerischen Kurzzeitwerte als Steuerungsbudget ausgegeben werden.
- **Kein universeller Spitzenlastschutz mit Echtzeitgarantie.** Lokale Messintervalle, Messabweichungen und Gerätereaktionszeiten können den tatsächlichen Zählerwert abweichen lassen.
- Kein automatisches Wiedereinschalten; keine evcc-Ladestromregelung; keine Victron-Netzladung; keine persistente Rekonstruktion verpasster Messungen.
- Bei Sensorfehlern stoppt die aktive Abschaltung, bereits ausgeschaltete Lasten bleiben ausgeschaltet.

## Vor dem produktiven Einsatz

Die Messwertanzeige und Berechnung wurden an einer realen Installation beobachtet. **Die echte Abschaltung, das Verhalten bei unzuverlässigen Sensoren, der vollständige Viertelstundenwechsel sowie HACS- und CI-Installation müssen in einer Home-Assistant-Testinstallation validiert werden.** Diese Veröffentlichung ist ausdrücklich eine Beta.

## Updates, Rückbau und Datenschutz

Updates der Integrationsdateien erfordern einen Neustart. Zum Entfernen zuerst den V15-Konfigurationseintrag in Home Assistant löschen, anschließend die Integration aus HACS entfernen. Historische Statistikdaten und benutzerdefinierte Dashboards werden dadurch nicht zwangsläufig gelöscht. V15 benötigt keine Cloud-Zugangsdaten und sendet selbst keine Telemetrie; die bereitgestellten Home-Assistant-Entitäten stammen aus der lokalen Installation.

## Technische Details

Domain: `v15_lastmanagement`. Integrationsklasse: `hub`. Konfiguration über UI; keine YAML-Änderungen erforderlich. Die 13 Entitäten behalten bei Updates ihre bisherigen `unique_id`-Werte. Ab Home Assistant 2026.3 unterstützt der lokale Ordner `brand/` die Darstellung von Integrations-Icons. Ältere Versionen können das Logo nicht lokal darstellen.

## Lizenz

Quellcode unter MIT-Lizenz. Das beigefügte V15-Logo ist eine eigens erstellte Projektgrafik; eine gesonderte Kennzeichen- oder Markenfreigabe wird damit nicht behauptet.
