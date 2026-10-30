# Lineage4Clones

Custom LineageOS 18.1 (Andr36oid) port and bootloader adaptation for **R36S Clones** (specifically **Clone Type 2 Panel 1 with Amplifier** / 2-RAM-chip boards).

> **Status / Hinweis:** Das Projekt funktioniert im Grunde (Dual-Boot dArkOS & LineageOS 18.1). Da es jedoch verschiedene Hardware-Revisionen bei R36S-Clones gibt, können vereinzelt noch Bugs oder Unregelmäßigkeiten auftreten (z. B. bei Audio-Lautstärkeregelung oder Tastenbelegungen).  
> *(The project is basically functional, but minor bugs or quirks may still occur depending on clone revisions.)*

---

## Hardware Compatibility Profile
* **Target Device:** R36S Clone (R36S-V12 PCB)
* **RAM Layout:** **2 Discrete RAM Chips** (Dual-channel DDR3)
* **Display Panel:** Panel 1 (`KD35T133`, 640x480 @ 60 Hz)
* **Audio:** RK817 with external speaker amplifier on `GPIO3_PA7`
* **Controls:** AMUX multiplexer on `GPIO2_PB3`, channels `<2 3 1 0>`
* **Stock DTB MD5:** `c9eb94f10298a567efe0506ca07bbf66` (Matching ArkOS4Clone Type 2 Panel 1 with Amp)

---

## Repository Structure
```text
Lineage4Clones/
├── build_image.py             # One-click disk image builder & bootloader fuser
├── boot-files/                # Linux kernel and Device Tree Blobs (DTBs)
│   ├── Image                  # K4uanGP v1.1 kernel with AMUX channel mapping
│   ├── rk3326-r36s-android.dtb # Patched DTB (Panel 1 + Amplifier on GPIO3_PA7)
│   ├── rk3326-r36s-android-amp.dtb
│   ├── rg351v-kernel.dtb
│   └── arkos_clone_type2.dtb  # Reference stock ArkOS4Clone DTB
├── clone-uboot/               # 2-RAM Clone-adapted Bootloader Binaries
│   ├── idbloader.img          # 2-RAM DDR initialization binary (Sector 64)
│   ├── uboot_stable.img       # Stable SD-card U-Boot binary (Sector 16384)
│   ├── trust.img              # ARM Trusted Firmware BL31 / OP-TEE (Sector 24576)
│   ├── uboot_oct05_emmc.img   # Experimental eMMC U-Boot build (reference)
│   └── dtb/                   # Extracted U-Boot device tree binaries
├── docs/                      # In-depth technical documentation
│   ├── HARDWARE_PROFILE.md    # Detailed device specifications & pinouts
│   ├── BOOTLOADER_REVERSE_ENGINEERING.md # Disassembly analysis of U-Boot & DDR init
│   └── CHAT_LOG_AND_INSIGHTS.md # Chronological debugging insights and history
└── README.md                  # This file
```

---

## Building the Image

Because complete disk images are > 3 GB (exceeding GitHub's 100 MB file limit), you can build the ready-to-flash image locally in seconds:

1. Download the base release zip from the Andr36oid releases (e.g. `lineage-18.1-20250902-2052-r36s-android.img.zip`) and place it inside `build-img/`.
2. Run the automated builder:
   ```bash
   python build_image.py
   ```
3. The script will:
   * Fuse `idbloader.img` at sector 64 (`0x40`).
   * Fuse `uboot_stable.img` at sector 16384 (`0x4000`).
   * Fuse `trust.img` at sector 24576 (`0x6000`).
   * Update the FAT32 `BOOT` partition with `rk3326-r36s-android.dtb` and `Image`.
   * Enable live on-screen boot logging (`console=tty0 loglevel=7`) in `boot.ini`.
4. Flash the resulting `build-img/lineage-18.1-r36s-clone-type2-amp.img` using Rufus or BalenaEtcher.

---

## Troubleshooting & Key Discoveries

### 1. Rapid Red LED Blinking (2–3 Hz) at Boot
* **Cause:** Standard LineageOS images use a single-RAM `idbloader.img`. On 2-RAM boards, memory training faults immediately.
* **Fix:** Fusing `clone-uboot/idbloader.img` solves memory training on 2-RAM clone boards.

### 2. `U-BOOT (spinor)` Display Banner & 5s Shutdown
* **Cause:** When U-Boot fails to detect or power the SD card (`mmc dev 1`), it displays Error Code 4 as a fallback banner and powers off.
* **Power Requirement:** The SD card power rail (`vmmc-supply`) is regulated by the RK817 PMIC. If the console battery is low or uncharged, the rail drops out during voltage select negotiation. Always charge the console with a standard 5V 1A/2A charger before booting.

### 3. Live On-Screen Boot Logging
`boot.ini` is configured with `console=tty0 loglevel=7`. When the Linux kernel executes, all boot messages scroll across the console screen in real time, making any kernel panic or mount error immediately visible.

---

## Credits & Attribution
* **Base Firmware:** [Andr36oid (LineageOS 18.1 for R36S)](https://github.com/andr36oid/releases)
* **Kernel & Panel Support:** [K4uanGP](https://github.com/K4uanGP/android_kernel_gameconsole_r36s)
* **Clone Bootloader & DTB Reference:** [lcdyk0517 / arkos4clone](https://github.com/lcdyk0517/arkos4clone)
* **Port Adaptation & Reverse Engineering:** Pair-programmed with **Antigravity**.
