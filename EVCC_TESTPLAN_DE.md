# V15 Beta 5 – evcc-Testplan (nur für eine unkritische Testladung)

1. **HA-Backup** erstellen. Prüfen, dass die bisherige V15-Lastabschaltung funktioniert und die bisherige Beta 4-Datei gesichert ist.
2. Bestehende Automationen/Regler, die `select.evcc_go_e_wallbox_max_current` oder `select.evcc_go_e_wallbox_mode` ändern, für diesen Test deaktivieren. Keine zwei Regler parallel.
3. Beta-5-Testpaket installieren, HA neu starten. In **V15 → Konfigurieren** evcc aktivieren und die passenden Entitäten wählen. Die bestehende Integration **nicht entfernen**.
4. Testwerte: Netzsensor wie bisher; evcc-Maximalstrom `select.evcc_go_e_wallbox_max_current`, Modus `select.evcc_go_e_wallbox_mode`, Ladeleistung `sensor.evcc_go_e_wallbox_charge_power` (kW), Phasensensor `sensor.evcc_go_e_wallbox_phases_active` (bei 0 zunächst ohne Sensor arbeiten und feste Phasenzahl 3 einstellen). min/max 6/16 A, Reserve 300 W, stabile Zeit 90 s, Änderungsabstand 30 s. Ladepause **zunächst deaktiviert**.
5. Bestehenden V15-Probelauf mit echten Messwerten nutzen. V15-Diagnose: `evcc_target_current_a`, `evcc_status` und `evcc_available_charge_w` prüfen. Noch keine Stellbefehle.
6. Für eine unkritische Testladung evcc auf `smart` stellen und den **neuen** Schalter „V15 evcc-Ladestromregelung“ aktivieren. Die separate V15-Schalterabschaltung kann deaktiviert bleiben.
7. Prüfen, ob V15 den Maximalstrom bei geänderten Leistungsbedingungen plausibel **reduziert** und erst nach 90 s stabiler Reserve stufenweise wieder **erhöht**. Für den Test eine geeignete Viertelstunde und hohe Messabdeckung abwarten.
8. Anschließend ggf. „Ladepause zulassen“ aktivieren (führt zu Integration-Reload und deaktivierter evcc-Steuerung). Wieder aktivieren, Lastbudget unter 6 A × 3 × 230 V bringen, eine echte Ladepause `smart → off` beobachten. Sinkt die übrige Netzlast ausreichend, sollte V15 nach stabiler Reserve auf `smart` zurückschalten. Keine Zwangsladung `now`.
9. **Fehlertest:** Eingespeiste evcc-Entität zeitweise `unavailable` beziehungsweise die Internet-/Sensordaten kontrolliert unterbrechen. V15 darf dann keine Ladestromerhöhungen auslösen. HA-Neustart: V15 evcc-Regelschalter muss aus sein.
10. **Testende:** V15 evcc-Steuerung deaktivieren, im evcc-Dashboard den Modus wieder auf `smart` und die gewünschte Maximalstromgrenze einstellen, ggf. abgeschaltete externe Regelautomation wieder aktivieren. Keine dauerhaft laufenden Doppelregler.

Bitte nach jedem Teilschritt die V15-Diagnose (insbesondere `evcc_status`, `evcc_last_action`, `evcc_paused_by_v15`) mit dem tatsächlichen evcc-Zustand vergleichen. Bei Unstimmigkeiten die evcc-Steuerung deaktivieren und zur Beta 4 zurückkehren.
