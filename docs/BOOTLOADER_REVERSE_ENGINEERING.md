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
