# Lineage4Clones

Port-Projekt: LineageOS 18.1 (andr36oid) auf R36S-Clone-Boards bringen, die bisher keinen Android-Support haben. Ziel-Board als erstes: **R36S-V12 Clone mit 2 RAM-Chips** ([Handhelds Wiki](https://handhelds.wiki/R36S_Clones#2_RAM_Chip_Clone_R36S-V12)).

## Warum das gehen sollte

- [andr36oid/releases](https://github.com/andr36oid/releases) baut LineageOS 18.1 bereits fuer die R36S-Familie (R36S, R50S, R46H): Kernel, Android-Schicht und Emulatoren existieren.
- [arkos4clone](https://github.com/lcdyk0517/arkos4clone) und [dArkOSRE](https://github.com/southoz/dArkOSRE-R36) haben fuer Clone-Boards (inkl. V12-Varianten und Panels) funktionierende DTBs und Kerneltreiber auf Linux-Seite erarbeitet.
- Kernstueck des Ports ist die DTB-Ebene (Display-Panel, RAM, GPIO, WLAN) plus DDR-Init.

## Plan

1. Board identifizieren: DTB der Stock-Karte durchs [DTB-Tool](https://lcdyk0517.github.io/dtbTools.html), dazu dmesg eines ArkOS-Clone-Boots.
2. Erster Versuch: andr36oid-Image flashen, BOOT-Partitions-DTBs gegen Clone-Varianten tauschen.
3. Iterieren: schwarzes Bild = Panel-Timing, kein Boot = RAM-Init.
4. Läuft es: WLAN, Joystick, Akku einzeln abarbeiten.

## Sicherheit

Das Geraet bootet komplett von der SD-Karte. Es wird nichts am internen Speicher angefasst: Schlimmster Fall ist eine nicht bootende Karte, neu flashen und weiter.

## Status

- [ ] Stock-Karte ausgelesen (DTB identifiziert)
- [ ] dmesg-Log gesichert
- [ ] Erster Boot-Versuch mit getauschten DTBs
