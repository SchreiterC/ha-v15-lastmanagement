# Virtuelles Testlabor fuer V15 und evcc

**Status:** Lokaler Entwicklungsstand v0.3.5b5. Nicht fuer die produktive Home-Assistant-Installation freigegeben.

## Prinzip

- Die Berechnung und die evcc-Zustandslogik sind die echten Python-Module aus `custom_components/v15_lastmanagement/`.
- Ein virtueller Haushalt erzeugt die Netzleistung aus Grundlast und EV-Ladeleistung. Negative Grundlast bildet PV-Ueberschuss ab.
- Eine virtuelle 3-phasige Wallbox kann 6 bis 16 A laden und kennt die Modi `smart`, `off` und `now`.
- Eine Home-Assistant-Attrappe liefert Messwerte und zeichnet `select.select_option` auf. Sie kennt **keinen Netzwerkzugriff und keine produktive Wallbox**.
- Die Uhr kann beschleunigt werden: 15 simulierte Minuten werden in Sekundenbruchteilen durchlaufen.

## Automatisierte Tests

Vom Projektordner aus:

```bash
python3 -m unittest discover -s tests -v
```

Beispielszenarien mit CSV-Ausgabe:

```bash
python3 tools/evcc_virtual_lab.py --scenario pv_drop_and_recovery --output simulation-results
python3 tools/evcc_virtual_lab.py --scenario meter_outage --output simulation-results
python3 tools/evcc_virtual_lab.py --scenario high_background --output simulation-results
python3 tools/evcc_virtual_lab.py --scenario sunny_30min --output simulation-results
```

Die Dateien `*_trace.csv` enthalten Messwerte und Diagnose je simuliertem Zeitschritt. `*_commands.csv` enthalten die von V15 vorgeschlagenen virtuellen evcc-Stellbefehle.

## Szenarien

1. **PV-Einbruch und Wiederkehr:** Bei Lastsprung Ladepause, spaeter Wiederfreigabe in `smart` und stufenweise Erhoehung der Stromgrenze.
2. **Messwertausfall:** Keine weiteren Stellbefehle bei nicht vertrauenswuerdigen Netzsensoren.
3. **Hohe Grundlast:** Wallbox bleibt pausiert, solange 6 A dreiphasig nicht ins Budget passen.
4. **HA-Neustart:** Neue V15-Instanz ist nicht zur Steuerung berechtigt.
5. **Manueller evcc-Eingriff:** Wechsel zu `now` beendet die V15-Regelung.
6. **Viertelstundenwechsel:** Messabdeckung und Schaltentscheidungen werden nach der naechsten Zeitgrenze neu bewertet.

## Grenzen

Dies ist ein **modellbasierter Test**. Es gibt keine reale Wallbox, keine physikalisch exakte PV-Prognose, keine authentische evcc-API-Antwort und keinen vollstaendigen Home-Assistant-Prozess. Insbesondere werden Kommunikationslatenzen, Automationskonflikte, echte Sensorausfaelle und hardwareabhaengige Phasenumschaltungen noch nicht durch diese Tests nachgewiesen.

## Naechste Stufen

1. Python-Tests und Szenariensimulator als eigenen CI-Job auf dem Entwicklungszweig ausfuehren.
2. Getrennte Home-Assistant-Testinstanz mit `pytest-homeassistant-custom-component` und Fake-Entitaeten nutzen; Registrierung, Konfigurationsdialog und echte Service-Aufrufe gegen die HA-Testumgebung pruefen.
3. Optional evcc mit virtuellen Geraeten auf einem isolierten Container/VM-Netz starten.
4. Erst nach diesen Pruefungen und einem freiwilligen Hardware-Betatest eine neue HACS-Version bereitstellen.

**Wichtig:** GitHub-Zweig `dev/evcc-simulator` ist absichtlich vom veroeffentlichten `main` getrennt. Keine produktiven Daten, Tokens, IP-Adressen oder Wallboxzugriffe im Testlabor hinterlegen.
