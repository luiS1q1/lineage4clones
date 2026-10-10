# Bootloader Reverse Engineering & RK3326 Clone Analysis

## 1. The Dual-RAM Bootloader Mismatch (Red Blinking LED)

### Phenomenon
Flashing the official LineageOS 18.1 (Andr36oid) release directly to the console resulted in a completely black screen and a rapidly blinking red LED (2–3 Hz).

### Root Cause
1. On Rockchip RK3326 SoCs, the internal BootROM loads `idbloader.img` from sector 64 (`0x40`) of the storage media.
2. `idbloader.img` contains the DDR initialization blob (`ddr.bin`) and Secondary Program Loader (`spl.bin`).
3. Official Andr36oid releases were packaged with an `idbloader.img` compiled for original single-RAM-chip R36S consoles.
4. On R36S clones equipped with **2 RAM chips** (R36S-V12 board), the single-chip DDR memory training algorithm faults immediately upon execution.
5. The RK817 PMIC / SoC enters a hardware fault state, pulsing the LED rapidly to signal a memory training failure before U-Boot or the display can ever initialize.

### Resolution
Fusing the clone-adapted `idbloader.img` (176,452 bytes) from `lcdyk0517/arkos4clone` at sector 64 successfully initializes the 2-RAM-chip memory controller.

---

## 2. Analysis of the `U-BOOT (spinor)` Display Banner

### Phenomenon
During boot attempts with clone U-Boot binaries, the screen turned on and displayed a grey banner at the top with:
```
U-BOOT (spinor) : <Date> <Time>
```
Followed ~5 seconds later by `power off...` and a complete system shutdown.

### Disassembly Analysis
Using Capstone disassembler on `uboot.img` (AArch64, base address `0x00200000`):

1. **The Display Function (`0x206efc` / `0x2070d0`):**
   * Case 4 (`w22 == 4`) triggers the display of a top header banner with background `"grey"` and text `"white"`.
   * It formats the compiled-in date and time into the template:
     `"U-BOOT (spinor) : %s %s"`
   * The text `(spinor)` is **hardcoded in the U-Boot image** (inherited from Hardkernel ODROID-GO Advance SPI NOR codebase).
   * It is not a hardware detection of an active SPI NOR chip, but a fallback banner displayed when Error Code 4 is triggered.

2. **The Caller (`0x206630` / `0x2065e0`):**
   * Before proceeding to `bootcmd`, U-Boot runs:
     `run_command("mmc dev 1", 0)` (in September build) or `run_command("${devtype} dev ${devnum}", 0)` (in October build).
   * If this command fails twice, U-Boot sets `w0 = 4` (Error Code 4) and calls `0x206efc` to display the banner.
   * Immediately following the banner, U-Boot enters `0x206de8`:
     * It loops 500 times with a 10 ms delay (5 seconds total).
     * It renders the string `"power off..."`.
     * It calls the PMIC poweroff routine to shut the console down.

3. **Why `mmc dev 1` Fails:**
   * In Rockchip U-Boot, `mmc dev 1` probes the primary SD card slot (`/dwmmc@ff370000`).
   * The SD card slot power rail (`vmmc-supply`) is powered by the RK817 PMIC.
   * When battery voltage is low or when power negotiation is unstable, the PMIC fails to provide stable 3.3V power to the SD card during U-Boot voltage select negotiation (`Card did not respond to voltage select!`).
   * Once connected to a stable 5V 1A/2A charger and allowed to reach proper voltage, the PMIC powers the card rail reliably.

4. **Why Direct Binary Patching Failed:**
   * Rockchip loader containers (`LOADER` header) enforce cryptographic checksums / signature blocks.
   * Modifying instructions or jump tables directly in `uboot.img` invalidates the header checksum checked by `trust.img`.
   * When integrity checks fail, the ARM Trusted Firmware (`trust.img`) halts before jumping into U-Boot, resulting in zero power-on response.

---

## 3. Stable Bootloader Configuration (`clone-uboot/`)

The repository includes the proven, intact bootloader binaries:
* `clone-uboot/idbloader.img`: 2-RAM DDR initialization binary.
* `clone-uboot/trust.img`: ARM Trusted Firmware (BL31 / OP-TEE).
* `clone-uboot/uboot_stable.img`: Stable U-Boot built for SD-card booting (`mmc 1`) with native Android boot command support (`bootcmd=boot_android ${devtype} ${devnum};bootrkp;run distro_bootcmd;`).
* `clone-uboot/uboot_oct05_emmc.img`: Experimental eMMC build preserved for reference.

---

## 4. Partition Scheme Analysis & U-Boot `mmc dev 1` Failure

### Stock LineageOS 18.1 Partition Layout
Inspection of the GPT partition header in the stock LineageOS image revealed the following 5 partitions:
1. `BOOT`: Start LBA 32,768, End LBA 1,081,343 (512 MB, FAT32)
2. `system`: Start LBA 1,081,344, End LBA 5,701,008 (~2,255 MB, EXT4)
3. `idbloader`: Start LBA 64, End LBA 16,383 (7.96 MB, Rockchip bootloader Stage 1)
4. `uboot`: Start LBA 16,384, End LBA 24,575 (4 MB, U-Boot Stage 2)
5. `trust`: Start LBA 24,576, End LBA 32,767 (4 MB, ARM Trusted Firmware BL31)

### Hybrid MBR vs. GPT Interaction
1. When fusing an MBR table into Sector 0 while leaving the original `EFI PART` GPT header at Sector 1, host operating systems (like Windows) detect conflicting partition styles, setting partitions to `IsOffline: True`.
2. In U-Boot, `part_efi.c` detects the primary GPT header and attempts to validate the Backup GPT at the end of the physical media.
3. If the backup GPT is absent or invalid, or if the partition structures do not match U-Boot's device map, U-Boot halts with `write empty ptable error` (`0x2c97d0`) and displays Error Code 4 (`U-BOOT (spinor)` banner).

---

## 5. Verification against Working ArkOS & Clean MBR Resolution

### Sector-by-Sector Binary Comparison (`dArkOS4Clone-20261008.img`)
Direct extraction and cryptographic MD5 comparison between the known-working ArkOS image and our repository bootloader files confirmed:
* **Sector 64 (`idbloader.img`):** MD5 `065c4e4e3e77414f636cbcfd7ee88a0b` (176,452 bytes) — Exact Match.
* **Sector 16384 (`uboot.img`):** MD5 `a1a164e2451f5d0f3743f700a463de11` (4,194,304 bytes) — Exact Match to `clone-uboot/uboot_oct05_emmc.img`.
* **Sector 24576 (`trust.img`):** MD5 `ba8fd9c133787ae54cc75fc35858eff3` (4,194,304 bytes) — Exact Match.

### Root Cause Resolution: Eliminating GPT Remnants
1. **ArkOS Reference Structure:** In `dArkOS4Clone`, Sectors 1 through 63 are filled with zeros (`0x00`). The drive is a clean, pure MBR disk.
2. **The Conflict in Hybrid Builds:** Leaving the stock GPT header (`EFI PART`) in LBA 1 triggered U-Boot's internal `ptable error` (`0x2c97d0`), aborting boot before `bootcmd` could execute.
3. **The Clean Build:**
   * Sectors 1–63 are wiped to zero.
   * Sector 0 defines standard MBR partitions (Partition 1: type `0x0b` FAT32 BOOT, Partition 2: type `0x83` Linux system).
   * FAT32 partition has both `/Image` and `/Image-resizing` updated with the clone kernel to avoid any single-RAM first-boot crash.



