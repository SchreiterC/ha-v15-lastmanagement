## v0.3.5b5 – evcc Pilot (nicht veröffentlicht)

- Optionaler evcc-Einrichtungsdialog mit frei wählbaren Home-Assistant-Entitäten.
- Neue, separat aktivierbare evcc-Ladestromsteuerung und Zielstromsensor.
- Dynamische Begrenzung des Maximalstroms, vorsichtige Stromerhöhung und optionales Pausieren/Wiederaufnehmen des Lademodus `smart`.
- Schutz gegen unzuverlässige Messwerte, fehlende Befehlsbestätigung, externe Reglereingriffe und ungewollte Steuerung nach Neustarts.
- Deutsche/englische Feldbeschriftungen und Erklärungen, zusätzliche Unit-Tests.
- Zusätzliche automatisierte Sicherheitsprüfungen für Ladepause, verzögerte Wiederfreigabe, zu wenig Restbudget, manuelle `now`-/`off`-Eingriffe, konkurrierende Ampere-Regler, fehlende Befehlsbestätigung, Messwertausfall und Neustart.
- Korrektur: Der konkrete Grund einer evcc-Sicherheitsabschaltung bleibt in der Diagnose erhalten und wird erst bei erneuter Freigabe zurückgesetzt.
- **14 von 14 Integrationstests mit Home Assistant 2026.11 und virtueller Wallbox erfolgreich; 63 Logiktests, Hassfest und HACS ebenfalls grün.**
- **Pilotstatus: keine echte evcc-/Wallbox-Hardware getestet und keine visuelle Docker-Oberfläche verifiziert.**

# Versionshistorie

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
