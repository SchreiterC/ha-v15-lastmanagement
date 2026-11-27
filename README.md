> **Version 0.3.6:** Home Connect Pause/Resume is an experimental, opt-in feature. Existing evcc support from v0.3.5 remains available. Use only with noncritical, pause-capable appliances and test in dry run first. The Home Connect cloud cannot guarantee real-time load shedding. Only a V15-confirmed pause may be resumed automatically; restarts clear ownership. Configure a conservative max resumption wattage for every selected PauseProgram button. No StopProgram and no StartProgram calls.

# V15 Lastmanagement für Home Assistant

## Austrian grid-capacity charge preview (optional, beta)

From the next V15 beta, users can enable **Netz-Leistungsentgelte (unverbindliches
Modell)** in the V15 options. Supported: the 14 Austrian electricity network
areas (nine federal-state network areas plus **Klagenfurt, Linz, Graz,
Innsbruck and Kleinwalsertal**). Not every grid area is identical to the
administrative boundaries of its federal state.

Choose the source of the estimate:

- **Draft 2027**: region-specific rates for grid level 7 from the E-Control
  consultation proposal published **29 October 2026**. These are **not
  enacted tariffs** and may be modified. The operator-dependent
  tariff-transition date is **not known automatically**, and the proposed
  progressive charges must not be presented as payable in 2026 or as the
  customer's actual 2027 network bill.
- **Own tariff**: enter two monthly capacity rates (cents/kW/month for the
  first 10 kW and above 10 kW), plus a minimum billed kW. The default
  2 kW minimum follows §6 SNE-G-V for regular grid-level-7 connections;
  different contracts, mini-connections and transition rules can differ.

The optional read-only sensors are:

- **V15 Monatsspitze (lokal beobachtet)**, kW, maximum of *completed*
  and sufficiently covered 15-minute local grid-import periods.
- **V15 Leistungsentgelt (Modell, netto)**, EUR/month, based on this
  observed maximum and the chosen draft/manual rate.
- **V15 Leistungsentgelt bei Zielspitze (Differenz, Modell)**, EUR/month:
  a **hypothetical** comparison of observed peak versus V15 target, **not
  realized savings**. No claim is made that V15 achieved the target.

A complete interval is accepted only with at least 855 of 900 measured
seconds (95% coverage), and the highest observed monthly 15-minute
average survives Home Assistant restarts using the HA storage facility.
Unobserved quarters, power sensor failures, integration activation midmonth
and retrospective load history cannot be reconstructed; consequently
the observed peak may **understate** the invoiced maximum. The values exclude
work-price components, energy tax, network losses, VAT and other fees.
They are not a substitute for the network operator's smart-meter portal
or invoice. No network billing service is called, and none of these
sensors changes the existing V15 load-shedding logic.

**Sources**:
[E-Control tariff consultation (29 Oct 2026)](https://www.e-control.at/de/konsumenten/begutachtungsentwurf-systemnutzungstarife-verordnung-2027),
[SNE-T-V 2027 draft, §5(1) NE7](https://www.wko.at/oe/news/0339-hue-snt-v-2027-begutachtungsentwurf.pdf),
[SNE-G-V §6 (tiered rates and 2 kW minimum)](https://www.ris.bka.gv.at/eli/bgbl/ii/2026/299/P6/NOR40281083).

## Optional restoration of live mode after restart (development preview)

Two independent, **default-OFF** options are available in the V15 setup and
options screen:

- `restore_live_control_on_restart`: restore **V15 Aktive Lastabschaltung**
  only if it was ON before the restart or reload. Fresh meter measurements,
  minimum coverage and all normal shedding interlocks are still required.
  No previously shed device is claimed or restored by V15 after a restart.
- `restore_pv_start_on_restart`: restore the **V15 PV-Programmstart** live
  switch only if it was ON previously. **This does not restore permission to
  start the dishwasher.** After HA is fully running, the designated
  `input_boolean` must be observed OFF, and then deliberately set ON again.
  A helper left ON from an earlier session is never a valid start request.

If an option is OFF, its corresponding live switch remains OFF after restart,
and the existing conservative simulation mode defaults to ON. The separate
evcc controller still requires manual activation after restart. Synthetic
demonstration mode is not restored. Explicitly enabling either live mode
deactivates simulation. The opt-in restoration follows HA's `RestoreEntity`
state store, which records switch state and may be unavailable before the
first successful save of a restorable entity.

**For testing:** after upgrading the development branch, first configure these
options, manually enable the desired live switches and then reload or restart
Home Assistant. Check that the intended live switches recover, and verify
that the old dishwasher authorization cannot trigger a start.

## Development preview: PV-optimized Home Connect dishwasher start (0.3.7b3 / planned 0.3.7)

**Unreleased / experimental beta 0.3.7b3:** development branch `feature/pv-program-timestamps`.
Version 0.3.6 and its existing switch / evcc / pause-resume behavior remain unchanged.
No guaranteed compliance with utility billing demand peaks.

This opt-in extension uses the existing Home Connect integration and a user-created
`input_boolean` as a **one-shot authorization**. It only accepts dishwasher
programs and checks the Home Connect operation state (`ready`), closed/locked door,
remote start, remote control, selected program, valid V15 metering and 15-minute
headroom before sending `home_connect.start_selected_program` for the selected
Home Assistant device. It does not auto-select or change the program.

The forecast sensor must supply `wh_period_15m`: a mapping from ISO-8601
timestamps to **Wh per 15-minute interval** (e.g. Open-Meteo Solar Forecast
`energy_production_today`). The scheduler compares expected solar yield over the
configurable **whole cycle**, rather than using a single daily total or peak.
It makes no claim to forecast *net* surplus: other future household loads are unknown.
After the configured deadline, the solar threshold is waived for 15 minutes,
but V15 headroom, selected program, authorization and all appliance interlocks remain mandatory.

**Activation / safety:**

1. In V15 options enable the experimental PV start, choose a Home Connect
   **dishwasher Selected Program** entity, one `input_boolean`, the solar
   forecast sensor, the earliest/latest time and conservative cycle watts.
2. Turn **V15 PV-Programmstart** ON separately *after each restart*.
   This is independent of the V15 active load shedding and evcc switches.
3. At the dishwasher select the program, close its door, enable remote start
   and deliberately turn the chosen input boolean ON once per load.
4. V15 switches the helper OFF **before** sending the Home Connect command.
   It then waits up to three minutes for the appliance to report `run`.
   Failed or unconfirmed starts require manual checking and **fresh** authorization.
5. Disable any existing Home Assistant dishwasher start automation first, so
   two controllers cannot independently issue `StartSelectedProgram`.
6. Start with a test appliance and conservative power assumptions. Cloud command
   delay is not suitable for real-time load shedding, and later heating peaks
   are not guaranteed to fit the quarter-hour billing cap.

Missing or stale V15 readings, insufficient measurement coverage, unavailable
Home Connect sensors, unconfirmed door/remote states and demo/simulation modes
block all real starts. The new feature is disabled on restart or reload; the
core V15 load management remains unchanged.

### Program timing / Programmzeiten (0.3.7b3)

Three read-only entities are added when PV start is configured:
**V15 PV-Programmstart geplant**, **V15 PV-Programmende erwartet** and
**V15 PV-Programmstatus**. The end timestamp uses the configured duration
before starting, and the Home Connect finish timestamp during a running program.
Select an optional tomorrow forecast sensor with the same `wh_period_15m`
attribute. After today's deadline plus 15 minutes, tomorrow is previewed;
without sufficient PV data the configured deadline is used. All estimates
remain conditional on appliance readiness, authorization and V15 headroom.
No control policy or restart authorization is changed.

Dashboard header example (verify entity IDs on your installation):

```jinja
{% set status = states('sensor.v15_lastmanagement_v15_pv_programmstatus') %}
{% set end = as_datetime(states('sensor.v15_lastmanagement_v15_pv_programmende_erwartet'), none) %}
{% if end is not none %}
**Geschirrspüler fertig: ca. {{ as_local(end).strftime('%d.%m., %H:%M') }} Uhr**
{% elif status == 'running' %}
**Geschirrspüler läuft – Endzeit wird ermittelt**
{% elif status == 'paused' %}
**Geschirrspüler pausiert**
{% elif status == 'starting' %}
**Geschirrspüler: Startbestätigung ausständig**
{% elif status == 'finished' %}
**Geschirrspüler fertig**
{% elif status in ['not_ready', 'fresh_arm_required', 'disabled', 'simulation'] %}
**Geschirrspüler: Freigabe oder Startbereitschaft prüfen**
{% endif %}
```

The timestamp attribute `source` is `pv_forecast`, `deadline` or
`home_connect`. Missing or paused finish times remain unknown.




![V15 Logo](custom_components/v15_lastmanagement/brand/logo.png)

**Reguläres Release 0.3.5. Keine zertifizierte oder garantierte Begrenzung abrechnungsrelevanter Lastspitzen.**

V15 beobachtet den Netzbezug in festen Viertelstunden (00/15/30/45), schätzt die voraussichtliche Viertelstundenleistung und kann bei drohender Überschreitung ausgewählte **unkritische** Home-Assistant-Schalter abschalten. Eine **optionale automatische Wiedereinschaltung** ist enthalten.

## Funktionen

- Frei wählbarer Leistungssensor (W/kW), Vorzeichenumkehr und maximale Messwertalterung.
- 15-Minuten-Durchschnitt, Prognose, Verbrauch, Messabdeckung und konservatives Restbudget.
- Individuell konfigurierbare Leistungsgrenze und Reserve.
- Priorisierte Abschaltung mehrerer `switch`-Entitäten.
- Optionales Wiedereinschalten in umgekehrter Abschaltreihenfolge, wenn die Reserve nachweisbar ausreicht.
- Simulation mit echten Messwerten ohne Schaltung und Demo mit künstlichen Messwerten.
- Diagnose mit verwalteten Abschaltungen, Rückschaltkandidat und Wartegrund.
- Ohne evcc: bisherige 14 Entitäten. Mit evcc: zwei zusätzliche Entitäten (evcc-Regelschalter und Zielstromsensor). Die bisherigen `unique_id`s bleiben unverändert.

<!-- ha-marketplace:exclude-start -->
## Installation und Update über den Home Assistant Marketplace

[![Im Home Assistant Marketplace öffnen](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=SchreiterC&repository=ha-v15-lastmanagement&category=integration)

**Voraussetzung:** Home Assistant 2026.11 oder neuer. V15 ist noch nicht im allgemeinen Marketplace-Katalog gelistet und wird daher als benutzerdefiniertes Repository hinzugefügt.

1. [V15 Lastmanagement im Marketplace öffnen](https://my.home-assistant.io/redirect/marketplace_repository/?owner=SchreiterC&repository=ha-v15-lastmanagement&category=integration). Alternativ unter **Einstellungen → Marketplace → Add from link** das Repository `https://github.com/SchreiterC/ha-v15-lastmanagement` hinzufügen. Für benutzerdefinierte Repositories ist eine GitHub-Verbindung im Marketplace erforderlich.
2. **Reguläre Version wählen:** Version **0.3.5** installieren. Die Option **Pre-release** ist dafür **nicht erforderlich**. Wer nur reguläre Releases verwenden möchte, lässt die Pre-release-Option ausgeschaltet.
3. **V15 Lastmanagement** im Marketplace installieren bzw. auf **0.3.5** aktualisieren.
4. Home Assistant vollständig neu starten.
5. Bei Neuinstallation V15 unter **Einstellungen → Geräte & Dienste** einrichten. Bestehende Installationen **nicht löschen**. Die 13 bisherigen Entitäten behalten ihre Identität, zusätzlich erscheint „V15 Verwaltete Abschaltungen“.
6. Bei einem Upgrade von Beta 2: **V15 → Konfigurieren/Optionen** öffnen, um die neuen Wiedereinschaltoptionen zu setzen. Standardmäßig bleibt die Wiedereinschaltung deaktiviert.

Bereits mit HACS installierte Integrationen werden beim Umstieg auf Home Assistant 2026.11 automatisch in den Marketplace übernommen. V15 muss dafür nicht neu installiert werden.
<!-- ha-marketplace:exclude-end -->

## Status der Funktionen

Die Viertelstundenberechnung, priorisierte Lastabschaltung, optionale Rückschaltung, Simulation und Diagnose bilden die regulär veröffentlichte Kernfunktion. Die **evcc-Steuerung bleibt eine separat einzurichtende, ausdrücklich zu aktivierende experimentelle Funktion**. Für diese Erweiterung stehen Hardware- und Langzeittests noch aus. V15 ersetzt keinen geeichten Netz-/Leistungszähler und garantiert nicht, dass eine vertragliche Viertelstunden-Grenze eingehalten wird.

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


## Experimentell: optionale evcc-Ladestrombegrenzung

**Wichtig: Die evcc-Funktion bleibt auch im regulären Release 0.3.5 experimentell.** Sie wurde mit virtuellen Wallbox-Entitäten in Home Assistant getestet, **noch nicht mit echtem evcc, echter Wallbox oder Fahrzeug**. Ein reguläres Release bedeutet **keine Freigabe dieser Pilotfunktion für den ungeprüften produktiven Betrieb**. Die bestehende Lastabschaltung und -rückschaltung bleiben unverändert. Die evcc-Steuerung wird nicht automatisch eingeschaltet.

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
