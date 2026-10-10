# Board identification (target device)

Source: stock OS card backup, DTB `rf3536k3ka.dtb` (104.6 KB), run through the
[ArkOS4Clone DTB Identification Tool](https://lcdyk0517.github.io/dtbTools.html) on 2026-10-10.

## Tool results

- File MD5: `c9eb94f10298a567efe0506ca07bbf66`
- File size: 107106 bytes
- Result type: partial match (panel parameters matched, MD5 differs)

### ArkOS4Clone suggestion

- Target system: [ArkOS4Clone](https://github.com/lcdyk0517/arkos4clone)
- Device option to try: **Clone R36S -> Clone Type 2 Panel 1 With Amplifier**
- Battery values in the DTB: designCapacity 3124, designQmax 3436

### Aurknix suggestion

- Target system: [Aurknix / ROCKNIX adaptation](https://github.com/AveyondFly/distribution_rocknix) ([releases](https://github.com/AveyondFly/distribution-nightly/releases))
- Device option to try: **R36S clone, Type 2 without amplifier** ("R36S克隆 种类2不带功放")

## Interpretation

- The stock DTB filename `rf3536k3ka.dtb` matches the known EmuELEC-clone naming scheme.
- Both tools agree the display panel is the same as Clone R36S **Type 2, Panel 1**; they disagree only
  on the amplifier bit (with vs. without). Test both during the first boot attempts.
- Partial match means no known DTB is byte-identical to the stock one, so the exact board variant may
  be a little different. Panel timing is the anchor to start from.

## Port checklist for this board

- [x] Stock card DTB identified (this file)
- [ ] dmesg log from an ArkOS clone boot captured
- [ ] First andr36oid LineageOS boot with swapped DTBs (Type 2 Panel 1, with and without amplifier)
- [ ] Display working
- [ ] Input (buttons, joysticks) working, note right-stick inversion option
- [ ] Audio (amplifier question settles here)
- [ ] WiFi
- [ ] Battery / charging (values above as reference)
