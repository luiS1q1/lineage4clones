# Stage 1 Forensics & Reverse-Engineering Report: R36S Clone Boot Chain

**Target Hardware:** R36S Clone Type 2 (Mainboard `R36S-V12`, 2 discrete RAM chips, Panel 1 `KD35T133` / `ST7701S`, Audio Amp `GPIO3_PA7`, Joysticks AMUX `GPIO2_PB3`).  
**Working Reference:** `dArkOS4Clone-20261008.img` (boots reliably and reproducibly on this exact console with the same TF1 MicroSD card).

---

## 1. Cryptographic Bootloader Hash Matrix

| Component | Disk Sector | Byte Offset | Size | Verified Working ArkOS MD5 | Standalone Repo Binary | Match Status |
|---|---|---|---|---|---|---|
| `idbloader` (SPL + DDR) | 64 | 0x8000 | 176,452 B (spans 345 sectors) | `065c4e4e3e77414f636cbcfd7ee88a0b` (file) / `9832387ef83261e9cbe2901962066d7b` (345 sec padded) | `clone-uboot/idbloader.img` | **100% Exact Match** |
| `uboot` (U-Boot proper) | 16384 | 0x800000 | 4,194,304 B (8,192 sectors) | `a1a164e2451f5d0f3743f700a463de11` | `clone-uboot/uboot_oct05_emmc.img` | **100% Exact Match** |
| `trust` (ATF / OP-TEE) | 24576 | 0xc00000 | 4,194,304 B (8,192 sectors) | `ba8fd9c133787ae54cc75fc35858eff3` | `clone-uboot/trust.img` | **100% Exact Match** |

*Note:* In earlier builds, `clone-uboot/uboot_oct05_debug.img` (`88f5986c7aa91df4d070fe5b4e0ea23e`) was fused instead of `uboot_oct05_emmc.img`. The debug binary patched `stdout-path` from `/serial@ff160000` to `vidconsole0`.

---

## 2. Low-Level Disk Layout (Sectors 0..32,767)

| Region | Sector Range | Working ArkOS (`dArkOS4Clone`) | Stock LineageOS Base | Built LineageOS Image |
|---|---|---|---|---|
| **Sector 0 (LBA 0)** | 0 | Pure MBR (Syslinux bootstrap code + Disk Sig `0x1279d432` + 3 partitions) | Protective MBR (Type `0xee`) | Pure MBR (Zeroed bootstrap + Disk Sig `0x1279d432` + 2 partitions) |
| **Sectors 1..33** | 1..33 | **Cleanly zeroed out (0x00)** | Primary GPT Header (`EFI PART`) & Partition Table | Cleanly zeroed out (0x00) |
| **Sectors 34..63** | 34..63 | Cleanly zeroed out | Cleanly zeroed out | Cleanly zeroed out |
| **idbloader Region** | 64..16383 | Sector 64..408 payload, **sectors 409..16383 are 100% zeroes** | Sector 64..408 payload, dirty sectors at 2048..2060 & 4566 | Sector 64..408 payload, dirty sectors at 2048..2060 & 4566 |
| **U-Boot Region** | 16384..24575 | `uboot_oct05_emmc.img` (`a1a1...`) | Stock 1-RAM U-Boot (`b95d...`) | `uboot_oct05_debug.img` (`88f5...`) |
| **Trust Region** | 24576..32767 | `trust.img` (`ba8f...`) | Stock Trust (`d98d...`) | `trust.img` (`ba8f...`) |

---

## 3. FAT32 BOOT Partition (LBA 32,768 / Offset 16 MiB) BPB Analysis

| Parameter | Working ArkOS | Stock LineageOS Base | Built LineageOS Image | Notes |
|---|---|---|---|---|
| Bytes per Sector | 512 | 512 | 512 | Standard |
| Sectors per Cluster | **1** (512 B) | **8** (4,096 B) | **8** (4,096 B) | Built preserved stock 4KB cluster |
| Reserved Sectors | 32 | 32 | 32 | Standard |
| Number of FATs | 2 | 2 | 2 | FAT1 + FAT2 |
| Hidden Sectors | **32,768** (`0x00008000`) | **0** | **0** | ArkOS points to start LBA 32,768 |
| Total Sectors (32) | 524,286 (256 MB) | 1,048,576 (512 MB) | 1,048,576 (512 MB) | Stock is 512MB |
| File Attribute (Image, DTB) | `0x20` (Archive) | `0x20` (Archive) | `0x00` (Normal) | `pyfatfs` default was `0x00` |

*Filesystem Integrity Check:* All FAT cluster chains in Built (`Image`, `Image-resizing`, `boot.ini`, `rk3326-r36s-android.dtb`) walk cleanly to `0x0ffffff8` without corruption.

---

## 4. Disassembly & Control-Flow Trace of `uboot_oct05_emmc.img`

- **Load Address:** `0x00200000` (code starts at file offset `0x800`).
- **Call Chain Leading to Error Code 4 & Grey Banner:**

```text
board_late_init (0x00203040..0x00203078)
  └── 0x00203070: bl #0x002066dc  [odroid_display_status]
        ├── 0x002066e4: bl #0x2063d0  (probes board ID via ADC/GPIO)
        ├── 0x00206700: bl #0x206444  (inits LCD panel & backlight PWM)
        ├── 0x00206794: adrp x0, "grey"; bl #0x264ee4  (clears screen to grey)
        ├── 0x002067a0: bl #0x2064a4  (checks recovery key combination)
        └── 0x002067c4: bl #0x00206630  [do_test_storage]
              ├── 0x00206640: adrp x19, 0x2bb000
              ├── 0x00206644: add  x19, x19, #0x271   ; "${devtype} dev ${devnum}" (0x002bb271)
              ├── 0x00206648: mov  x0, x19
              ├── 0x0020664c: bl   #0x0022cb48        ; run_command("${devtype} dev ${devnum}", 0)
              │                                       ; Default env: devtype=mmc, devnum=1 -> "mmc dev 1"
              │
              ├── [IF SUCCESS: w0 == 0]:
              │     0x00206650: cbz  w0, #0x206680
              │     0x0020669c: bl   #0x282480        ; fs_exists("mmc", "1:2", "/usr/local/bin/emulationstation/emulationstation")
              │     0x002066a0: cbz  w0, #0x2066d0    ; If NOT found, returns 0 cleanly!
              │     0x002066d8: ret                   ; Returns to board_late_init -> autoboot -> bootcmd
              │
              └── [IF FAILURE: w0 != 0]:
                    0x00206654: mov  w1, #1
                    0x00206658: mov  x0, x19
                    0x0020665c: bl   #0x0022cb48      ; RETRY run_command("${devtype} dev ${devnum}", 0)
                    0x00206660: cbz  w0, #0x206680    ; If retry succeeds, proceed to success path
                    0x00206664: mov  x2, #0           ; Arg 3: NULL
                    0x00206668: mov  w1, #2           ; Arg 2: 2
                    0x0020666c: mov  w0, #4           ; Arg 1: w0 = 4 (ERROR CODE 4)
                    0x00206670: bl   #0x00206efc      ; show_bmp(4, 2, NULL)
                    0x0020667c: b    #0x00206de8      ; odroid_wait_pwrkey()
```

### Display Function `show_bmp(4, 2, NULL)` at `0x002070e8`:
- Checks `cmp w22, #4` -> matches Error Code 4.
- Sets background color to `"grey"` (`0x002c9869`).
- Sets text color to `"white"` (`0x002bb2bf`).
- Formats banner: `"U-BOOT (spinor) : %s %s"` with `"Oct 05 2026"` and `"07:52:14"`.
- Prints banner to video console via `vidconsole_printf`.

### Shutdown Loop `odroid_wait_pwrkey` at `0x00206dfc`:
- Initializes 501-iteration loop counter (`mov x19, #0x1f5`).
- Prints `"Wait power key"`, then `"power off..."` on screen.
- Executes 10 ms delay loop (`bl #0x2a2c58`) 501 times $\rightarrow$ **exactly 5.01 seconds**.
- At loop exit: `adrp x0, "poweroff"`; `bl #0x0022cb48` $\rightarrow$ **hard poweroff**.

---

## 5. Reverse-Engineering Insights

1. **Root Cause of Error Code 4:**
   Error Code 4 is triggered **exclusively** when `mmc dev 1` fails twice during early storage probing in `board_late_init`.
2. **EmulationStation Check is Non-Fatal:**
   If `mmc dev 1` succeeds, U-Boot checks for `/usr/local/bin/emulationstation/emulationstation` on `mmc 1:2`. If absent, instruction `0x002066a0` (`cbz w0, #0x2066d0`) immediately branches to clean return `0`. Boot continues normally to `bootcmd`.
3. **Partition Table Formatting:**
   `mmc dev 1` initializes the MMC controller and reads the card CID/CSD. Partition table parsing (MBR vs GPT) occurs downstream during `cfgload` / `fatload`.
4. **Device Tree Mapping & UHS Voltage Negotiation:**
   In U-Boot FDT aliases:
   - `mmc0 = /dwmmc@ff390000` (eMMC, 8-bit bus)
   - `mmc1 = /dwmmc@ff370000` (MicroSD slot, 4-bit bus)
   `uboot_oct05_debug_nouhs.img` was created specifically because clone boards frequently fail UHS-I 1.8V voltage negotiation (`sd-uhs-sdr12/25/50/104`), causing `mmc dev 1` to fail with `"Card did not respond to voltage select!"`.
