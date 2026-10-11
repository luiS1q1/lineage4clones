# Debug diagnostics: getting the real U-Boot error on screen

## Correction to Phase 7 (CHAT_LOG_AND_INSIGHTS.md)
The "write empty ptable error (0x2c97d0)" strings are **OP-TEE / TEE Client API**
messages (`TEEC: ree_fs_new_*`) from the Trusted Execution Environment image,
not partition-table errors. The GPT-remnants root-cause claim is **retracted**:
after wiping sectors 1-63 and using a pure MBR, the failure is unchanged.

## Why we never saw the real error
The embedded control DTB (`u-boot` FDT at uboot.bin 0xfc910, totalsize 6049)
sets `chosen stdout-path = /serial@ff160000`. **Every U-Boot printf goes to the
serial port, never to the screen.** The on-screen banner is drawn directly by
the fallback routine. So "mmc dev 1 failed" was never confirmed; it is one of
several possible failing steps (mmc init, cfgload/boot.ini execution, kernel
load, booti), all invisible because stdout is serial.

Established: SPL reads idbloader/uboot/trust successfully from the same card
(the banner date changes with the fused uboot build), so card read at low level
and power are working.

## Debug build: clone-uboot/uboot_oct05_debug.img
Identical to `uboot_oct05_emmc.img` except the chosen `stdout-path` is patched
to `vidconsole0` (4 copies in the 4 MB image, all patched consistently; header
CRCs recomputed with rkbin `loaderimage`; load addr 0x200000 unchanged). With
this build U-Boot prints its full boot log, including the real error line, to
the screen. The 5 s power-off still runs: film the boot with a phone camera.

To use: replace the uboot file the builder fuses with this one (or flash it at
sector 16384) and boot-test as usual.

## Test A: boot.ini bisect (no rebuild, 3 minutes)
The uboot default env bootcmd is `mmc dev 1; cfgload; run setbootargs; load
mmc 1:1 ... Image ...`. `cfgload` reads `boot.ini` from partition 1 (FAT32) and
executes it. We do not know whether execution reaches `cfgload` at all.

Open the card's BOOT partition in Windows (it is FAT32) and add these lines at
the very top of `boot.ini`:

    setenv stdout vidconsole
    echo
    echo === FO-DEBUG: boot.ini laeuft ===
    echo
    mmc dev 1
    mmc info
    mmc part
    sleep 30

Outcomes:
- Fallback banner appears within ~5 s: `boot.ini` never runs; the failure is at
  or before `mmc dev 1` / `cfgload`.
- Screen stays black ~30 s (then boot continues or banner appears): `boot.ini`
  RUNS; the failure is a later command (load/booti). The error prints above if
  the stdout switch worked.
- `=== FO-DEBUG` shows on screen: vidconsole stdout works, read the whole log.

## Decisive comparison (still open)
Dump the first 32 MB of the working stock ArkOS4Clone card and compare: if its
sector-16384 uboot equals ours, the binary is proven good on this exact board
and the difference is card content (env/boot.ini) or the physical test card.
