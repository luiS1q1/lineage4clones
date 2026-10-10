# Lineage4Clones

Port project: get LineageOS 18.1 (andr36oid) running on R36S clone boards that have no Android support yet. First target board: the **2 RAM Chip Clone R36S-V12** ([Handhelds Wiki](https://handhelds.wiki/R36S_Clones#2_RAM_Chip_Clone_R36S-V12)).

## Why this should work

- [andr36oid/releases](https://github.com/andr36oid/releases) already builds LineageOS 18.1 for the R36S family (R36S, R50S, R46H): kernel, Android layer and emulators exist.
- [arkos4clone](https://github.com/lcdyk0517/arkos4clone) and [dArkOSRE](https://github.com/southoz/dArkOSRE-R36) have already produced working DTBs and kernel drivers for clone boards (including V12 variants and panels) on the Linux side.
- The core of the port is the DTB layer (display panel, RAM, GPIO, WiFi) plus the DDR init.

## Plan

1. Identify the board: run the stock card's DTB through the [DTB tool](https://lcdyk0517.github.io/dtbTools.html), plus save a dmesg from an ArkOS clone boot.
2. First attempt: flash the andr36oid image, swap the BOOT partition DTBs for clone variants.
3. Iterate: black screen = panel timing, no boot = RAM init.
4. Once it boots: work through WiFi, joystick, battery one by one.

## Safety

The device boots entirely from the SD card. Nothing on the internal storage is touched: worst case is a non-booting card, reflash and move on.

## Status

- [x] Stock card read out (DTB identified: Clone Type 2 Panel 1 With Amplifier)
- [x] ArkOS4Clone test successful (confirmed working hardware match)
- [x] Boot files prepared (`boot-files/`: patched kernel Image v1.1 + amplifier DTB)
- [ ] First andr36oid boot test on hardware
