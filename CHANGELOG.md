# Versionshistorie

## 0.3.5 – Erstes reguläres Release (2026-11-13)

- Erste reguläre, nicht als Prerelease gekennzeichnete Veröffentlichung von V15 Lastmanagement. Version 0.3.5 basiert funktional auf Beta 5 (`0.3.5b5`).
- **Regulärer Funktionsumfang:** Überwachung fester 15-Minuten-Zeitfenster, Netzbezug und Leistungsprognose, konservatives Restbudget, priorisierte Abschaltung konfigurierter unkritischer Verbraucher, optionale sichere Wiedereinschaltung selbst abgeschalteter Verbraucher, Diagnose und Probelauf.
- **Experimentell, weiterhin nur als Pilot:** optionale evcc-Ladestromsteuerung samt Ladepause und Wiederaufnahme. Separat einzurichten und ausdrücklich zu aktivieren. Bislang mit virtuellen Home-Assistant-/evcc-Entitäten, **nicht mit realer evcc-/Wallbox-/Fahrzeughardware** getestet. Keine Freigabe für ungeprüften produktiven Betrieb.
- Für die bisherige Beta 5: 63 Logiktests und 14 Home-Assistant-Integrationstests sowie acht virtuelle Docker-Praxisszenarien erfolgreich. Die Release-Prüfungen werden für 0.3.5 erneut ausgeführt.
- Installations- und Updatehinweise für den **Home Assistant Marketplace** aktualisiert. Für 0.3.5 ist keine Aktivierung der Pre-release-Option notwendig.
- Bestehende Konfigurationen und Entitätskennungen bleiben erhalten. Keine automatischen Last- oder evcc-Steuerfreigaben nach Neustart/Reload.
- **Sicherheitsgrenze:** V15 ist keine geeichte oder garantierte Viertelstunden-Spitzenleistungsbegrenzung. Vorsicht bei Messwertqualität, Netzverzögerungen, Konfigurationsfehlern und kritischen Lasten.

## 0.3.5b5 – Beta 5: optionale evcc-Ladestromsteuerung (2026-11-12)

- **Neu:** Optionale Anbindung an die bestehenden evcc-Entitäten von Home Assistant mit separatem Einrichtungsdialog, eigener ausdrücklicher Steuerfreigabe und Zielstromsensor.
- Automatische Anpassung des maximalen Ladestroms anhand des konservativen Viertelstundenbudgets. Stromsenkung unmittelbar, Erhöhung stufenweise nach stabiler Leistungsreserve.
- **Optional:** Ladepause unterhalb der dreiphasigen Mindestladeleistung und kontrollierte Wiederaufnahme (erst auf 6 A begrenzen, danach nach `smart` schalten).
- Sicherheitsmechanismen gegen veraltete/unvollständige Messwerte, ausbleibende Servicebestätigung, Änderungen durch externe Automationen oder manuelle Eingriffe sowie ungewollte Wiederaufnahme nach Reload.
- Bestehende Abschalt- und Wiedereinschaltfunktionen bleiben erhalten. evcc-Funktion muss bewusst eingerichtet und nach jedem Neustart/Reload erneut aktiviert werden.
- Deutsche und englische Beschriftungen und Hilfetexte für die neuen Optionen.
- **Tests:** 63 Logiktests und 14 Home-Assistant-Integrationstests in GitHub Actions bestanden. Zusätzlich acht interaktive Szenarien in separater Docker-HA-Instanz mit virtueller Wallbox erfolgreich geprüft, inklusive Ladepause, Neustart der Integration und externer Eingriffe.
- **Einschränkung:** Noch kein Test der tatsächlichen evcc-Netzwerkkommunikation oder einer echten Wallbox. Pilot/Prerelease, nicht für ungeprüften produktiven Betrieb.
- Installationshinweise für Home Assistant 2026.11 über den integrierten Marketplace aktualisiert.

## 0.3.5b4 – Beta 4: Deutschsprachige Einstellungen und Hilfetexte (2026-11-10)

- Einheitliche deutsche und englische Bezeichnungen für die Abschalt- und Wiedereinschaltoptionen.
- Erläuterungen direkt an allen Feldern der Erstkonfiguration und der Optionen (`data_description`).
- Zweiter Dialog mit Hinweis auf Watt, maximal zu erwartende Geräteleistung und mögliche Einschaltspitzen. Die ausgewählten Schalter werden im Beschreibungstext genannt.
- Übersetzungen unter `translations/de.json` und `translations/en.json` vollständig abgestimmt; `strings.json` als englische Quellvorlage.
- Keine Änderungen an der Abschalt-/Rückschaltlogik und den bestehenden Entitätskennungen.

## 0.3.5b3 – Beta 3: automatische Wiedereinschaltung (2026-11-05)

- **Optionale Rückschaltung:** V15 darf von ihm selbst abgeschaltete und bestätigt ausgeschaltete Schalter wieder einschalten, wenn die prognostizierte Viertelstundenlast und das begrenzte Restbudget dafür Raum lassen.
- Leistungsaufnahme **je Schalter** über einen zusätzlichen Schritt des Konfigurationsdialogs einstellbar.
- Konfigurierbare Mindestausschaltdauer, Dauer stabiler Leistungsreserve und zusätzlicher Watt-Puffer.
- Kein automatischer Einschaltvorgang innerhalb der letzten 90 Sekunden einer Viertelstunde.
- Nur ein Schalter gleichzeitig, Rückschaltung in umgekehrter Abschaltreihenfolge; nach jeder Rückschaltung mindestens 60 s Abstand.
- Keine Rückschaltung bei ungültigen Messwerten, fehlender Messabdeckung, Demo oder Probelauf; kein Einschalten fremd/manuell ausgeschalteter Geräte.
- Sicherheitsverhalten: Nach Neustart, Update oder Konfigurations-Reload wird die Live-Steuerung deaktiviert und die bisherige Abschalthistorie nicht rekonstruiert.
- Neuer Sensor „V15 Verwaltete Abschaltungen“; Diagnose um Rückschaltstatus erweitert. Alle früheren `unique_id` bleiben bestehen.
- Zusätzliche Unit-Tests für Rückschaltbedingungen und simulierte Schalterereignisse.
- Die automatische Rückschaltung ist **nicht** in Home Assistant praktisch verifiziert. Weiterhin öffentliche Beta, keine abrechnungsgenaue Leistungsbegrenzung.

## 0.3.5b2 – GitHub-Metadaten-Korrekturen (2026-11-04)

- Integration Manifest für HACS- und Hassfest-Prüfung korrekt sortiert und Repository-Links/Codeowner ergänzt.
- Regelungslogik unverändert gegenüber Beta 1.

## 0.3.5b1 – öffentliche Beta-Vorlage (2026-11-04)

- Projektstruktur für HACS und GitHub, Branding und Tests ergänzt.
- Viertelstunden- und Abschaltlogik aus 0.3.4 übernommen.

## 0.3.4

- Restbudget auf Grenzwert abzüglich Reserve begrenzt; Ausgabe bei ungenügender Messabdeckung unterdrückt.
