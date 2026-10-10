# Comprehensive Log of Findings & Development History

This document chronicles all insights, experiments, and technical resolutions produced during the adaptation of LineageOS 18.1 (Andr36oid) for the R36S Clone Type 2 (Panel 1 with amplifier, 2 RAM chips).

---

## Session Timeline & Milestones

### Phase 1: Hardware Identification
* **User Context:** The user has an R36S clone console with an external speaker amplifier that booted ArkOS4Clone (`lcdyk0517/arkos4clone`) using `Clone Type 2 Panel 1 With Amplifier`.
* **Verification:** The stock DTB MD5 was confirmed as `c9eb94f10298a567efe0506ca07bbf66`.
* **Hardware Components Resolved:**
  * Screen: Panel 1 (`KD35T133`, 640x480).
  * Audio: RK817 Codec with external amp on `GPIO3_PA7`.
  * Joysticks: AMUX on `GPIO2_PB3`, channels `<2 3 1 0>`.
  * RAM: 2 discrete RAM chips (R36S-V12 clone PCB).

### Phase 2: First Image Build & The Red Blinking Light
* **Action:** Built initial disk image with patched FAT32 `BOOT` partition (`Image` kernel v1.1 + `rk3326-r36s-android.dtb`).
* **Symptom Reported by User:** The screen remained black, and the red LED blinked rapidly 2–3 times per second.
* **Diagnosis:** Rockchip RK3326 DDR memory training failure caused by standard 1-RAM `idbloader.img` running on a 2-RAM-chip board.
* **Fix Applied:** Downloaded `idbloader.img`, `uboot.img`, and `trust.img` from `lcdyk0517/arkos4clone` and fused them into Rockchip boot sectors (LBA 64, 16384, 24576).

### Phase 3: Screen Life & `U-BOOT (spinor)`
* **Symptom Reported by User:** The screen turned on and displayed `U-BOOT (spinor) : Oct 05 2026 07:52:14`, followed ~5 seconds later by `power off...` and shutdown.
* **Key Finding:** 
  1. The 2-RAM `idbloader.img` successfully solved the memory training fault.
  2. The display initialized properly with crisp text output.
* **Deep Reverse Engineering:**
  * Disassembled `uboot.img` using Capstone.
  * Discovered that the U-Boot from commit `a3c4563` (October 5, 2026) was an experimental build designed for eMMC installation that had a strict fallback routine displaying Error Code 4 (`U-BOOT (spinor)`) and powering off when `mmc dev 1` / `${devtype}` negotiation failed.
  * An attempt to patch the jump table in machine code broke the Rockchip loader header integrity checksum, confirming that `trust.img` validates the payload.
  * Located the stable September 1, 2026 U-Boot from `arkos4clone` (`uboot_stable.img`) which was compiled specifically for SD-card booting with native Android boot command support (`bootcmd=boot_android ...`).

### Phase 4: Power Rails & Battery Voltage
* **Observation:** The console exhibited no response on an uncharged/low battery, but sprang to life as soon as the charger was connected.
* **Finding:** In RK3326 handhelds, the RK817 PMIC controls the 3.3V `vmmc` rail for the SD card slot. When battery voltage is low, the PMIC drops the SD card rail during voltage select negotiation, triggering `mmc dev 1` failure. Stable charging current is required for consistent SD initialization.

### Phase 5: Live Boot Logging & Repository Preservation
* **Feature Added:** Configured `console=tty0 loglevel=7` in `boot.ini` and `boot.ini-android`. When the Linux kernel executes, all kernel messages and driver logs scroll live across the LCD screen for real-time visibility.
* **Automation:** Created `build_image.py` to allow one-click generation of the complete flashable 3.2 GB image from local files.
* **Repository State:** Committed all bootloader binaries, DTBs, tools, and documentation to GitHub.

### Phase 6: Rufus Flashing, Partition Mounting, and Boot Test
* **Flashing Process:** The user wrote `lineage-18.1-r36s-clone-type2-amp.img` to a 32 GB SanDisk MicroSD card using Rufus 4.13.2316 in raw MBR mode (status reported green `FERTIG`).
* **Windows Drive Mystery Resolved:**
  * In Windows Explorer, clicking on `USB-Laufwerk (E:)` displayed the prompt: *"Legen Sie einen Datenträger in das USB-Laufwerk (E:) ein."*
  * Investigation revealed that the USB adapter is a multi-card reader (`Generic Flash-Disk`) with two LUNs:
    * `Disk 1`: The 32 GB MicroSD card.
    * `Disk 2`: The empty standard SD card slot (`0 B, No Media`), which Windows permanently assigned as drive letter `E:`.
  * The actual MicroSD card (`Disk 1`) was present and healthy, but Windows marked Partition 1 (`BOOT`) as `IsOffline: True` without a drive letter because the image contained both MBR partition entries in LBA 0 and an original `EFI PART` GPT header in LBA 1, which Windows rejects as a conflicting partition structure.
* **Console Boot Test:**
  * The user inserted the card into slot TF1-OS of the R36S clone console.
  * **Result:** The screen turned on and displayed the same fallback error banner:
    ```
    U-BOOT (spinor) : Sep 01 2026 01:59:58
    ```
    Followed ~5 seconds later by `power off...` and shutdown.
* **Key Insights & Next Focus:**
  * Even with the stable September 1 U-Boot (`uboot_stable.img`), U-Boot fails during `run_command("mmc dev 1")` before it can execute `bootcmd`.
  * GPT layout analysis of the stock LineageOS image revealed:
    * Partition 1: `BOOT` (LBA 32768, 512 MB)
    * Partition 2: `system` (LBA 1081344, 2255 MB)
    * Partition 3: `idbloader` (LBA 64, 7 MB)
    * Partition 4: `uboot` (LBA 16384, 4 MB)
    * Partition 5: `trust` (LBA 24576, 4 MB)
  * In the next step, we must investigate why `mmc dev 1` fails in U-Boot on this hardware (e.g. MMC clock/voltage in U-Boot device tree, backup GPT validation requirement, or MMC bus width/mode).

