# V15 Lastmanagement 0.3.6 – Home Connect (reguläres Release)

V15 Lastmanagement 0.3.6 basiert auf dem bestehenden regulären Release 0.3.5. Die bisherigen Funktionen einschließlich der experimentellen evcc-Anbindung bleiben erhalten.

## Neu: Home Connect (experimentell)

- Optional ausgewählte, kompatible Home-Connect-Waschmaschinen/Trockner/Waschtrockner über die vorhandene Home-Assistant-Integration pausieren und fortsetzen.
- Ausschließlich `PauseProgram` und `ResumeProgram`-Taster; kein `StopProgram`, kein neuer Programmstart und kein Unterbrechen der Stromversorgung.
- Pause wird nur als V15-eigene Aktion erfasst, wenn der Gerätestatus das Pausieren bestätigt.
- Automatisches Fortsetzen nur bei bestätigter V15-Pause, ausreichendem 15-Minuten-Restbudget samt konservativ eingestellter Leistungsaufnahme und Sicherheitsabstand sowie erfüllter Mindestpause/stabiler Leistungsreserve.
- Home-Connect-Befehle werden nach Schalter-Abschaltungen priorisiert; Cloud-Latenz macht sie für eine garantierte Lastspitzenbegrenzung ungeeignet.
- Nach Neustart, Reload, Cloudfehler oder nicht bestätigter Aktion kann manuelles Fortsetzen nötig sein.

**Bitte nur in einer kontrollierten Testumgebung einsetzen.** Home Connect wurde noch nicht mit realen Geräten erfolgreich verifiziert. Die Version selbst ist regulär; die Home-Connect-Funktion bleibt ausdrücklich experimentell. Gleiches gilt für evcc in dieser Version.

## Installation

Home Assistant 2026.11 oder neuer. Über den [Home Assistant Marketplace](https://my.home-assistant.io/redirect/marketplace_repository/?owner=SchreiterC&repository=ha-v15-lastmanagement&category=integration) 0.3.6 installieren, HA vollständig neu starten und die Integration nicht löschen. Zuerst den Probelauf verwenden; aktive Lastabschaltung nach Neustart explizit freigeben.

## English

Version 0.3.6 is a regular release based on 0.3.5 and retains its existing evcc and switch controls. **Experimental, opt-in Home Connect support** uses official Home Assistant PauseProgram and ResumeProgram entities. It only resumes a V15-confirmed pause after conservative measured headroom and stability checks. Cloud-dependent controls cannot guarantee real-time peak limiting. Manual recovery may be needed after restart, cloud outages or command failures. Test only with explicitly authorized, non-critical appliances.
