# V15 Lastmanagement 0.3.8 – Programmzeiten im Dashboard

## Deutsch

Reguläres Release auf Basis von 0.3.7. Der PV-optimierte Home-Connect-Programmstart bleibt optional und experimentell.

- Drei neue, rein lesende Sensoren: geplanter Programmstart, erwartetes Programmende und Programmstatus.
- Vor dem Start ergibt sich die Endzeit aus der PV-Planung und der konfigurierten Programmdauer; bei laufendem Programm wird der gültige Home-Connect-Endzeitpunkt verwendet, sofern verfügbar.
- Optionale Solarprognose für den Folgetag. Die angezeigte Startzeit bleibt eine bedingte Schätzung.
- Dashboard-Beispiel mit verbleibender Zeit und voraussichtlicher Fertigstellungszeit in der README.
- Keine zusätzliche Startfreigabe oder Änderung der Neustart-Sicherheitsregeln durch die neuen Sensoren.

**Aktualisierung:** V15 im Marketplace auf 0.3.8 aktualisieren, Home Assistant neu starten und die Entitäten des V15-Geräts prüfen. Die Folgetagsprognose kann optional in den Integrationsoptionen ausgewählt werden. Die neuen Sensoren erscheinen bei konfiguriertem PV-Programmstart. Wenn die Endzeit nicht sinnvoll ermittelt werden kann, bleibt sie unbekannt.

Die Programmzeiten sind Prognosen, keine garantierten Start- oder Fertigstellungszeiten.

## English

Regular release based on 0.3.7. PV-optimized Home Connect program start remains optional and experimental.

- Three new read-only sensors for estimated program start, estimated finish and program status.
- Before starting, the estimate uses the PV schedule and configured duration; while running, it uses a valid Home Connect finish timestamp when available.
- Optional next-day solar forecast. The displayed schedule remains conditional.
- Dashboard example in the README showing time remaining and estimated completion.
- No additional start authorization or change to restart safety rules from the new sensors.

**Update:** Install 0.3.8 via the Marketplace, restart Home Assistant and inspect the V15 device entities. The next-day forecast is optional in the integration options. The timing sensors are created when PV program start is configured. If no meaningful finish time is available, it remains unknown.

Program times are estimates, not guaranteed start or finish times.
