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
### Phase 7: Exact Sector-by-Sector Verification against Working ArkOS & Clean Rebuild
* **Source Comparison (`dArkOS4Clone-20261008.img`):**
  * Located the local uncompressed 12.4 GB working release `dArkOS4Clone-20261008.img` in user's downloads.
  * Executed direct cryptographic hash comparisons against our repository bootloader files:
    * `idbloader.img` (Sector 64): MD5 `065c4e4e3e77414f636cbcfd7ee88a0b` — **100% byte-for-byte identical**.
    * `trust.img` (Sector 24576): MD5 `ba8fd9c133787ae54cc75fc35858eff3` — **100% byte-for-byte identical**.
    * `uboot.img` (Sector 16384): MD5 `a1a164e2451f5d0f3743f700a463de11` — **100% byte-for-byte identical to our `uboot_oct05_emmc.img`**.
* **Root Cause of the `U-BOOT (spinor)` Fallback Uncovered:**
  * **Partition Structure Mismatch:** In working `dArkOS4Clone`, Sectors 1–63 are **100% zeroed out** (no GPT header whatsoever), and Sector 0 contains a pure MBR partition table.
  * In the previous build of LineageOS, Sector 0 had MBR entries written, but Sectors 1–33 still held the stock GPT header (`EFI PART`) and partition array.
  * Disassembly of U-Boot confirmed function `0x206f60` aborting on `write empty ptable error` (`0x2c97d0`) when encountering contradictory partition headers, triggering Error Routine 4 (`U-BOOT (spinor)`) and 5-second shutdown.
* **Kernel First-Boot Trap Discovered:**
  * In LineageOS FAT32 `BOOT`, `boot.ini` on first boot loads `Image-resizing`, NOT `Image`.
  * `Image-resizing` in the stock image was compiled for single-RAM boards and would crash immediately if executed.
* **Fix & Rebuild Executed:**
  * Zeroed out Sectors 1–63 completely in `build_image.py`.
  * Configured Sector 0 MBR to match working ArkOS (type `0x0b` FAT32 BOOT + type `0x83` Linux system).
  * Fused the verified working clone bootloader (`idbloader.img`, `uboot_oct05_emmc.img`, `trust.img`).
  * Patched the FAT32 BOOT partition:
    * `/Image`: Updated with clone kernel (15.7 MB).
    * `/Image-resizing`: Updated with clone kernel (15.7 MB) to prevent first-boot freeze.
    * `/rk3326-r36s-android.dtb`: Updated with Panel 1 + Amp DTB (92.4 KB).
    * `boot.ini` / `boot.ini-android`: Enabled live on-screen logging (`console=tty0 loglevel=7`).


