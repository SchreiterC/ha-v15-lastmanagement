# V15 Lastmanagement für Home Assistant

![V15 Logo](custom_components/v15_lastmanagement/brand/logo.png)

**Entwicklungsversion 0.3.5b6 (noch nicht veröffentlicht). Keine zertifizierte Begrenzung abrechnungsrelevanter Lastspitzen.**

V15 beobachtet den Netzbezug in festen Viertelstunden (00/15/30/45), schätzt die voraussichtliche Viertelstundenleistung und kann bei drohender Überschreitung ausgewählte **unkritische** Home-Assistant-Schalter abschalten. Ab Beta 3 ist eine **optionale automatische Wiedereinschaltung** möglich.

## Funktionen

- Frei wählbarer Leistungssensor (W/kW), Vorzeichenumkehr und maximale Messwertalterung.
- 15-Minuten-Durchschnitt, Prognose, Verbrauch, Messabdeckung und konservatives Restbudget.
- Individuell konfigurierbare Leistungsgrenze und Reserve.
- Priorisierte Abschaltung mehrerer `switch`-Entitäten.
- **Neu:** Wiedereinschalten in umgekehrter Abschaltreihenfolge, wenn die Reserve nachweisbar ausreicht.
- Simulation mit echten Messwerten ohne Schaltung und Demo mit künstlichen Messwerten.
- Diagnose mit verwalteten Abschaltungen, Rückschaltkandidat und Wartegrund.
- Ohne evcc: bisherige 14 Entitäten. Mit evcc: zwei zusätzliche Entitäten (evcc-Regelschalter und Zielstromsensor). Die bisherigen `unique_id`s bleiben unverändert.

<!-- ha-marketplace:exclude-start -->
## Installation und Update über den Home Assistant Marketplace

[![Im Home Assistant Marketplace öffnen](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=SchreiterC&repository=ha-v15-lastmanagement&category=integration)

**Voraussetzung:** Home Assistant 2026.11 oder neuer. V15 ist noch nicht im allgemeinen Marketplace-Katalog gelistet und wird daher als benutzerdefiniertes Repository hinzugefügt.

1. [V15 Lastmanagement im Marketplace öffnen](https://my.home-assistant.io/redirect/marketplace_repository/?owner=SchreiterC&repository=ha-v15-lastmanagement&category=integration). Alternativ unter **Einstellungen → Marketplace → Add from link** das Repository `https://github.com/SchreiterC/ha-v15-lastmanagement` hinzufügen. Für benutzerdefinierte Repositories ist eine GitHub-Verbindung im Marketplace erforderlich.
2. **Beta-Version aktivieren:** Da derzeit ausschließlich Vorabversionen veröffentlicht sind, unter **Einstellungen → Geräte & Dienste → Marketplace** beim Repository **V15 Lastmanagement** die zunächst deaktivierte Entität **Pre-release** aktivieren und den Schalter einschalten.
3. **V15 Lastmanagement** im Marketplace installieren bzw. auf eine neue Version aktualisieren.
4. Home Assistant vollständig neu starten.
5. Bei Neuinstallation V15 unter **Einstellungen → Geräte & Dienste** einrichten. Bestehende Installationen **nicht löschen**. Die 13 bisherigen Entitäten behalten ihre Identität, zusätzlich erscheint „V15 Verwaltete Abschaltungen“.
6. Bei einem Upgrade von Beta 2: **V15 → Konfigurieren/Optionen** öffnen, um die neuen Wiedereinschaltoptionen zu setzen. Standardmäßig bleibt die Wiedereinschaltung deaktiviert.

Bereits mit HACS installierte Integrationen werden beim Umstieg auf Home Assistant 2026.11 automatisch in den Marketplace übernommen. V15 muss dafür nicht neu installiert werden.
<!-- ha-marketplace:exclude-end -->

## Sprache und Erklärung im Einrichtungsdialog

Die Einstellungsseiten sind auf **Deutsch und Englisch** übersetzt. Die Sprache richtet sich nach der eingestellten Sprache des Home-Assistant-Benutzers. Alle Felder enthalten nun zusätzliche Erläuterungen. Auf der zweiten Seite erklärt V15 die benötigten Leistungswerte in **Watt**, zeigt die ausgewählten Schalter und warnt vor zu kleinen Schätzwerten.

Nach einem manuellen Austausch der Integrationsdateien ist ein **vollständiger Home-Assistant-Neustart** erforderlich. Bei nicht aktualisierten Texten die Seite neu laden (gegebenenfalls Browser-Cache aktualisieren). Bei einem Upgrade über den Marketplace dieselben Schritte nach dem Download ausführen.

## Konfiguration der Wiedereinschaltung

Unter **Einstellungen → Geräte & Dienste → V15 Lastmanagement → Konfigurieren**:

1. Wie bisher Netzsensor, 15-Minuten-Grenze, Reserve und Abschalt-Schalter wählen.
2. **Automatische Wiedereinschaltung erlauben** aktivieren. Ohne diese ausdrückliche Freigabe werden Lasten weiterhin nur abgeschaltet.
3. Mindest-Ausschaltdauer (Standard **180 s**), notwendige stabile Reserve (Standard **90 s**) und zusätzlichen Puffer (Standard **200 W**) wählen.
4. Im nächsten Dialog **für jeden konfigurierten Schalter die konservativ erwartete Leistungsaufnahme in Watt** eintragen. Berücksichtige Anlaufspitzen und die reale Wirkung auf den Netzbezug. Bei zu niedriger Schätzung sind Überschreitungen möglich.
5. Die **V15 Aktive Lastabschaltung** bleibt auch bei aktivierter automatischer Wiedereinschaltung nach jedem HA-Neustart ausgeschaltet. Für echte Schaltvorgänge muss sie gezielt eingeschaltet werden.

Beispiel: Bei 5,0 kW Grenzwert und 0,5 kW Reserve liegt das angezeigte Steuerungsbudget höchstens bei 4,5 kW. Ein Gerät mit eingetragener Leistung von 600 W und 200 W zusätzlichem Puffer darf nur eingeschaltet werden, wenn der aktuelle Netzbezug **und** die verbleibende Viertelstundenenergie genügend Platz für insgesamt weitere 800 W lassen. Der Puffer ist eine zusätzliche Vorsichtsmaßnahme und keine Garantie.

### Wie V15 wieder einschaltet

- Es kommen **ausschließlich Schalter infrage, die V15 in diesem Lauf selbst ausgeschaltet hat und deren OFF-Zustand bestätigt wurde**. Bereits zuvor manuell abgeschaltete Geräte werden nicht eingeschaltet.
- Bei manueller bzw. externer Einschaltung endet die Zuständigkeit von V15 für dieses Gerät.
- Der Netzleistungssensor muss gültig sein. Mindestens 60 Sekunden und 95 % Messabdeckung der laufenden Viertelstunde sind erforderlich. Demo und Probelauf schalten nie.
- Die aktuelle Leistung **plus** eingetragene Geräteleistung **plus** zusätzlichen Puffer muss unter dem konservativ begrenzten Restbudget liegen. Eine gefährdete Viertelstundenprognose blockiert die Wiedereinschaltung.
- Die Reserve muss mindestens 90 Sekunden **durchgehend** ausreichend sein, das Gerät mindestens 180 Sekunden ausgeschaltet (beide Zeiten konfigurierbar).
- In den letzten 90 Sekunden einer Viertelstunde startet V15 keine Rückschaltung, damit die neue Viertelstunde nicht mit einer unkontrolliert frisch zugeschalteten Last beginnt.
- Die Rückschaltung erfolgt einzeln, in **umgekehrter Abschaltreihenfolge**. Nach jeder Rückschaltung wird mindestens 60 Sekunden gewartet, bevor ein weiteres Gerät eingeschaltet werden darf.
- Der Status wird als Text in den Attributen von **V15 Diagnose** angezeigt. Der Sensor **V15 Verwaltete Abschaltungen** zählt die von V15 verwalteten ausgeschalteten Schalter.

**Wichtige Einschränkung bei Neustart, Update und Konfigurationsänderung:** V15 vergisst die in diesem Lauf selbst abgeschalteten Verbraucher bewusst beim Neuladen der Integration und lässt sie ausgeschaltet. Sie werden nicht nachträglich automatisch eingeschaltet. Das verhindert eine unkontrollierte Wiedereinschaltung nach Neustarts. Prüfe sie dann manuell. Auch das Deaktivieren der aktiven Laststeuerung schaltet bereits ausgeschaltete Geräte **nicht** sofort wieder ein.


## Neu in Beta 5: Optionale evcc-Ladestrombegrenzung

**Wichtig: Die evcc-Funktion ist ein gesonderter Pilot. Sie wurde mit virtuellen Wallbox-Entitäten in Home Assistant getestet, jedoch noch nicht an einer echten Wallbox.** Die bestehende Lastabschaltung und -rückschaltung bleiben unverändert. Keine evcc-Steuerung wird automatisch eingeschaltet.

### Voraussetzungen

- Eine laufende evcc-Installation und ihre Home-Assistant-Integration (beispielsweise `marq24/ha-evcc`). V15 verwendet die vorhandenen Entitäten, nicht die direkte evcc-HTTP-API.
- Ein `select` oder `number` für den **maximalen Ladestrom in Ampere**, ein `select` für den **Lademodus** (mit `smart` und `off`) und ein Leistungssensor der Wallbox in **W oder kW**.
- Ein Sensor für die aktiven Phasen (1 oder 3), alternativ eine bewusst festgelegte Phasenzahl von 1 oder 3. Bei einer dreiphasig möglichen Wallbox darf die Ersatz-Phasenzahl nicht 1 sein.
- Alle bestehenden Home-Assistant-Automationen, die denselben evcc-Maximalstrom oder -Modus verändern, für den Test **deaktivieren**. Gleichzeitige Regler können sich widersprechen.

### Einrichtung

1. Unter **V15 Lastmanagement → Konfigurieren** das Kästchen **Optionale evcc-Wallboxsteuerung einrichten** aktivieren.
2. Auf der zusätzlichen Seite evcc-Maximalstrom, Lademodus, Ladeleistung, gegebenenfalls Phasensensor und Grenzwerte auswählen. Für eine typische 3-Phasen-Wallbox zunächst 230 V, 6–16 A, 300 W zusätzlichen Puffer, 90 s stabile Reserve und 30 s Änderungsabstand verwenden.
3. **Ladepause zulassen** zunächst **deaktiviert** lassen. Ohne diese Freigabe kann V15 unterhalb der 6-A-Mindestgrenze nur einen Hinweis anzeigen und maximal auf 6 A reduzieren.
4. Nach dem Neustart den Sensor **V15 evcc Zielstrom** und die Attribute von **V15 Diagnose** prüfen. Der Zielstrom wird auch im Probelauf aus echten Daten berechnet; `unbekannt` bedeutet unter anderem, dass der erlaubte Strom unter 6 A läge oder Messwerte fehlen.
5. Nach dem Probelauf den separaten Schalter **V15 evcc-Ladestromregelung** ausdrücklich einschalten. Es wird nur im evcc-Modus `smart` gesteuert. Das Einschalten beendet den V15-Probelauf. Die bisherige V15-Lastabschaltung ist ein eigener Schalter und muss dafür nicht aktiviert sein.

### Regellogik

- V15 begrenzt den maximal erlaubten evcc-Ladestrom aus dem verfügbaren Viertelstundenbudget, der **tatsächlich gemessenen Wallbox-Ladeleistung** und dem übrigen Netto-Netzbezug. Die allgemeine Sicherheitsreserve wird zusätzlich durch den konfigurierten evcc-Puffer ergänzt.
- Stromsenkungen werden ohne 90-s-Wartezeit angefordert, Erhöhungen erst nach stabiler Reserve und schrittweise um höchstens **1 A** in mindestens **30 s** Abstand. V15 erhöht niemals über die zu Beginn der Steuerung vorgefundene evcc-Maximalstromgrenze.
- Ist selbst die Mindestladeleistung (6 A × Phasenzahl × ca. 230 V) zu hoch, wird **nur bei ausdrücklicher Freigabe** und **nur bei tatsächlich messbarer Ladeleistung** der evcc-Modus von `smart` auf `off` gesetzt. V15 darf ausschließlich **seine eigene Ladepause** nach stabiler Leistungsreserve wieder in `smart` freigeben. Der Modus `now` wird niemals gesetzt.
- Sind normale V15-Abschaltschalter aktiv, werden diese bei Gefährdung zuerst behandelt. V15 verändert nicht gleichzeitig einen Schalter und evcc anhand desselben unbestätigten Netzleistungswertes.
- Bei ungültigen Daten, Messabdeckung unter 95 %, fehlender Bestätigung eines Stellbefehls oder einer externen Änderung des evcc-Modus/Stromlimits werden **keine weiteren evcc-Stellbefehle** ausgeführt. V15 wechselt gegebenenfalls in den deaktivierten Zustand.
- Bei einem HA-Neustart, einer Neukonfiguration oder dem Abschalten des evcc-Regelschalters **werden die von V15 gesetzten evcc-Grenzen und Ladepausen nicht automatisch zurückgesetzt**. Das vermeidet unkontrollierte Leistungssprünge. Bitte im evcc-Dashboard manuell prüfen und gegebenenfalls wieder `smart` und die gewünschte Maximalstromgrenze einstellen.

### Bewusste Einschränkungen

- V15 steuert nur **einen evcc-Ladepunkt** pro Integrationseintrag und verwendet zunächst die Home-Assistant-Entitäten, nicht die native evcc REST-API.
- Keine Phasenumschaltung durch V15, keine Steuerung von Fahrzeug-SoC, Ladeplänen, Solarpriorität oder dynamischen Strompreisen. Diese Aufgaben verbleiben bei evcc.
- Die Berechnung mit 230 V pro Phase ist eine Näherung. Leistungsbegrenzungen sind nicht abrechnungsgenau garantiert.
- Die aktive evcc-Steuerung darf wegen der noch ausstehenden Hardwaretests **nicht ungeprüft in einer produktiven Anlage** eingeschaltet werden.

## In Entwicklung: Beta 6 – direkte go-e-Charger-Anbindung

**Nur Entwicklungszweig `dev/goe-beta6`. Nicht als neue öffentliche Version freigegeben und nicht für den ungeprüften produktiven Betrieb vorgesehen.** Die bisherige evcc-Anbindung aus Beta 5 bleibt erhalten.

### Zwei alternative Wallbox-Anbindungen

- **evcc:** Bestehende Home-Assistant-evcc-Entitäten wie in Beta 5.
- **go-e direkt:** Lokale HTTP-API v2 des go-e Chargers, ohne evcc als Zwischenschicht.

In der V15-Konfiguration ist **nur eine der beiden Anbindungen auswählbar**. Die go-e-Regelung übernimmt dieselbe konservative Viertelstundenbudgetberechnung, Verzögerungen für Stromerhöhungen, Bestätigung nach Stellbefehlen und die bewusste Startsperre nach Neustart/Reload. Neu erscheinen bei go-e die Entitäten **V15 go-e Zielstrom** und **V15 go-e-Ladestromregelung**. Ohne eigene Aktivierung werden keine Schreibbefehle an go-e gesendet.

### Technische Voraussetzungen und Grenzen

1. go-e Charger mit **lokaler HTTP-API v2** (z. B. Gemini flex) im selben lokalen Netz. Die API in der go-e-App aktivieren. Der Beta-6-Prototyp unterstützt nur eine private IPv4-Adresse aus 10/8, 172.16/12 oder 192.168/16, keine Cloud-API, keinen Portwechsel und keine HTTP-Authentifizierung.
2. **evcc und alle anderen Systeme, die denselben Charger steuern, ausdrücklich deaktivieren.** Das Häkchen im V15-Dialog ist lediglich die Bestätigung durch den Benutzer, keine technische Sperre von evcc. Das gilt auch für konkurrierende go-e-Ladepläne.
3. go-e 11 kW als Ausgangswert: **3 Phasen, 6–16 A**, 230 V je Phase, zusätzlicher Puffer 300 W, stabile Reserve 90 s und Änderungsabstand mindestens 30 s. Drei Phasen konfigurieren, wenn die Wallbox grundsätzlich dreiphasig laden kann. V15 schaltet keine Phasen um.
4. Die API liefert `amp` (Sollstrom), `frc` (0 = Neutral, 1 = Aus, 2 = erzwungen Ein), `nrg[11]` (gemessene Gesamtleistung in W) sowie `pnp` (Phasenzahl). V15 schreibt **ausschließlich** `amp` und bei ausdrücklich aktivierter Ladepause `frc=1`. Nach einer V15-eigenen Pause wird nur `frc=0` (Neutral) wiederhergestellt, niemals `frc=2` (erzwungen Ein).
5. Ist das verfügbare Restbudget zu klein, begrenzt V15 zunächst den Strom oder pausiert bei ausdrücklich freigegebener Ladepause. Nach stabiler Reserve wird vor der Wiederaufnahme der Maximalstrom auf 6 A gesenkt. Ein manueller Eingriff in `amp` oder `frc` beendet die V15-Steuerung.
6. Nach Deaktivierung, Ladefehler oder Neustart stellt V15 **weder eine eigene Ladepause noch die vorherige Stromgrenze automatisch zurück**. Bitte die Einstellungen am Charger selbst prüfen.

**Aktueller Teststand:** Automatisierte Python- und Home-Assistant-Laufzeitprüfungen mit simulierten lokalen go-e-API-Antworten. Für die go-e-Direktanbindung gibt es **noch keinen erfolgreichen Hardwaretest**, keine bestätigten Kommunikationslatenzen des realen Chargers und keinen Test mit tatsächlicher Fahrzeugladung. Ein zuverlässiger technisch erzwungener Ausschluss anderer externer Regler ist nicht möglich.

[go-e-API-v2-Dokumentation](https://github.com/goecharger/go-eCharger-API-v2) · [Beta-6-Entwicklungszweig](https://github.com/SchreiterC/ha-v15-lastmanagement/tree/dev/goe-beta6)

## Sicherheit und Grenzen

- **Keine sicherheitskritischen Lasten** schalten (medizinische Geräte, Gefrierschränke mit Risiko des Warenverlusts, Server, Alarmtechnik, Heizungsschutz etc.).
- Die Einschaltentscheidung verwendet **eine geschätzte Leistungsaufnahme pro Schalter**. Ein `switch` liefert nicht zuverlässig die tatsächliche Leistung oder Einschaltspitze. Selbst bei korrekten Schätzungen können PV, Speicher oder andere Lasten unerwartet reagieren.
- Das aktuelle elektrische Restbudget ist ein konservativ gekappter Wert. Die V15-Berechnung ist kein geeichter Viertelstunden-Zähler; keine Garantie für die Einhaltung eines Netzbetreiber-Limits.
- Die Messintegration berücksichtigt nur positiven Netzbezug; Einspeisung wird nicht gegengerechnet.
- Netzlast, Gerätereaktion und Schaltzustände können zeitlich verzögert sein. Nicht bestätigte Schaltvorgänge werden protokolliert, und Wiedereinschaltbefehle werden nicht unbegrenzt wiederholt.
- Bei fehlenden oder veralteten Netzleistungsdaten werden **weder Abschaltung noch Wiedereinschaltung** ausgelöst. Bereits ausgeschaltete Geräte bleiben vorerst aus.
- Gleichzeitige andere Automationen für dieselben Schalter und für denselben evcc-Maximalstrom sind zu vermeiden. Victron-Speicherparameter werden in dieser Version nicht gesteuert.

## Sichere Testreihenfolge

1. Backup erstellen, nur eine unkritische Teststeckdose konfigurieren, mit Probelauf starten.
2. Aktive Lastabschaltung einschalten und bei absichtlich niedrigem Grenzwert die bestätigte Abschaltung beobachten.
3. Zum Test der Wiedereinschaltung **nicht zwischendurch die V15-Einstellungen ändern**, da das die Integration neu lädt und die Liste abgeschalteter Geräte löscht.
4. Die übrige Hauslast außerhalb von V15 senken, bis die Reserve für *Geräteleistung + Puffer* ausreicht. Nach Mindest-Ausschaltdauer und stabiler Reserve muss der Schalter einmalig zurückgeschaltet werden.
5. Danach aktive Lastabschaltung deaktivieren und Grenzwerte wieder auf normale Werte stellen.
6. Testfälle mit ungültigen Messwerten und Neustart separat durchführen. Die bisherige Abschaltung und Wiedereinschaltung wurden in Home Assistant praktisch getestet. Die neue evcc-Anbindung wurde automatisiert und mit einer virtuellen Wallbox in einer separaten Docker-HA-Instanz getestet; ein Test mit echter evcc-/Wallbox-Hardware steht noch aus.

## Fehler und Vorschläge

Bitte ein [GitHub Issue](https://github.com/SchreiterC/ha-v15-lastmanagement/issues) eröffnen und Home-Assistant-Version, V15-Version sowie Diagnose/Protokoll (ohne persönliche Daten und Zugangsdaten) ergänzen.

## Lizenz

MIT für den Quellcode. Das Logo ist eine projektbezogene Grafik.
