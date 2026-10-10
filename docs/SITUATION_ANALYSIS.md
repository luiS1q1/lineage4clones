# Situation Analysis: U-Boot `mmc dev 1` Failure on the R36S-V12 Clone (2 RAM Chips)

*Written 2026-10-11, after commit 04027d3. Author: Fo (review pass over the full repository).*

## 1. Where the boot chain stands

| Stage | Component | Status on R36S-V12 clone |
|---|---|---|
| 0 | BootROM | loads idbloader from SD sector 64: **works** |
| 1 | `idbloader.img` (SPL + DDR init) | clone 2-RAM binary from arkos4clone: **works** (red-LED failure of the stock 1-RAM idbloader is solved) |
| 2 | `trust.img` (BL31/OP-TEE) | **works** (integrity check passes, U-Boot starts) |
| 3 | U-Boot | starts, display init works (banner renders), but `mmc dev 1` fails twice -> Error Code 4 fallback banner `U-BOOT (spinor) ...`, 5 s later `power off...` |
| 4 | boot.ini / kernel / Android | **never reached** |

Failure signature, both with the experimental Oct-05 eMMC U-Boot and the stable Sep-01 SD U-Boot:

```
U-BOOT (spinor) : Sep 01 2026 01:59:58
power off...            (about 5 s later)
```

## 2. New evidence from the community (andr36oid/releases issues)

Read in full on 2026-10-11:

* **Issue #110** — *No speaker audio on R36S-V12 clone (dual RAM chip variant)*: a user with the **same board class** (R36S-V12, 2023-08-18 mainboard, 2 RAM chips) has **Android (build 20260316) actually booting**. Their only problem is missing speaker audio. This is proof the port can run on this hardware. Open question: which bootloader/base combination they used.
* **Issue #38** — *powering off before getting to the android setup menu* (R36S-V12, screen V4): same "power off" symptom, but the boot animation played, so U-Boot and kernel had already run. Community fix: **battery state** — boot while charging, or drain the battery fully and write the image again.
* **Issue #112** — *instant PMIC hardware shutdown / flashing red light at u-boot spl stage*: red-LED failure on newer boards, hypothesis DDR3 vs DDR3L and PMIC rail differences. No confirmation yet, and it fails one stage earlier than we do.
* **Issue #104** — *failed to load dtb* (V12, 2x D9PXW RAM): a **later** failure stage; the Android initramfs prints "dtb load fail" because of hardcoded DTB validation. Useful to know as the *next* wall after ours, not the current one.
* **Issue #62** — several clone users fail on stock images ("dbt load failed" file in the BOOT root). Confirms clones need adapted boot files, consistent with our findings.

arkos4clone git history confirms the Oct-05 experimental binary comes from commit `a3c4563` ("Upgrade U-Boot to support installation to eMMC"); U-Boot binaries are **not in the arkos4clone git tree**, they ship inside the release images.

## 3. Hypotheses, ranked

| # | Hypothesis | Evidence for | How to confirm / refute | Assessment |
|---|---|---|---|---|
| H1 | SD-card power rail (`vmmc`, RK817 PMIC) drops out when battery is low; `mmc dev 1` fails voltage negotiation | Our Phase-4 observation (console only alive on charger); issue #38's fix | Boot test **with charger connected** and battery above ~50% | **Most likely, cheapest to test** |
| H2 | The fused `uboot_stable.img` is not the exact binary the working stock card uses (different build/config for the clone) | Banner date Sep 01 2026 01:59:58 matches the file, but we never compared it against the stock card | MD5-compare sectors 16384..24575 of the working stock card against `clone-uboot/uboot_stable.img` | **Decisive 5-minute check** |
| H3 | Embedded U-Boot control DTB has wrong MMC config (vmmc-supply phandle, card detect, bus width) | mmc fails before partition parsing | Needs proper `dtc -I dtb -O dts` on the U-Boot DTBs. Our four extracted blobs are ~6 KB control FDTs padded to 100 KB and could not be fully parsed with the tooling used here | Possible, verify only if H1/H2 fail |
| H4 | `mmc dev 1` devnum/alias mismatch (U-Boot probes the wrong controller) | Would also fail on the stock card if the same binary boots ArkOS there daily | Same as H2 comparison | Unlikely if H2 shows identical binaries |
| H5 | GPT/backup-GPT validation | U-Boot reads the primary GPT at LBA 1; backup GPT sits at the end of the 3.2 GB image and is intact | Remove the hybrid-MBR write and retest | Low, but the hybrid MBR (2 entries, no `0xEE` protective entry, GPT header left at LBA 1) is nonstandard on the Windows side either way |
| H6 | Card incompatibility | SanDisk 32 GB is a known-good brand | Test card in PC reader after flash | Very low |

## 4. Approaches

* **A. Proven bootloader from the working stock card (recommended next step).** The console boots its own ArkOS4Clone card every day, so sectors 64, 16384 and 24576 of *that card* are a known-good bootloader for this exact board. First only **compare** (no flashing): if `uboot_stable.img` is byte-identical to the card's U-Boot, H1 (power rail) jumps to the top and we stop touching the bootloader entirely. If different, fuse the card's binaries instead.
* **B. Charger/battery boot test (do tonight, zero cost).** Boot with the charger connected, battery at least half full. If that still fails: drain the battery completely, re-flash, retry (per issue #38). Never test booting on an empty battery again; it invalidates every result.
* **C. Base image 20260316 + clone bootloader.** Issue #110 shows Android 20260316 booting on the same board class. Rebuild with the newest base instead of 20250902 (newer DTBs, updated battery/healthd). Combine with A's bootloader and B's power conditions.
* **D. Proper U-Boot surgery (only if A-C fail).** Instead of byte-patching (which breaks the header checksum trust.img validates), rebuild `uboot.img` with Rockchip's own tools (rkbin `loaderimage` / u-boot `mkimage`), so the header checksum is recomputed. That opens changing `bootcmd`/`mmcdev` or swapping the embedded control DTB.
* **E. Partition hygiene (do regardless, one variable at a time).** Drop the hybrid-MBR write from `build_image.py` for the next test: the GPT header stays at LBA 1, U-Boot reads GPT first, and the current MBR (2 real entries, no `0xEE` protective entry) only adds a Windows-side conflict. If a hybrid MBR is ever wanted, it must include the `0xEE` entry.
* **F. Upstream help.** Comment on andr36oid #110 (same board, Android boots) to ask which bootloader/base combination was used, and on #38 for the exact power conditions. Only after Luis gives the go-ahead; the repo account signs it.

## 5. Decision

1. **A-compare (5 min):** dump and MD5 the stock card's bootloader regions, compare with the repo files.
2. **B:** boot test with charger connected.
3. If still failing: **C** (20260316 base + card-proven bootloader, charger connected, hybrid MBR disabled per E).
4. Only then **D**.

## 6. Extraction and compare commands (stock card -> PC)

macOS / Linux (card reader, card NOT mounted):

```bash
# find the device (macOS: diskutil list, use /dev/rdiskN; Linux: lsblk, /dev/sdX)
sudo dd if=/dev/rdiskN bs=512 skip=64     count=400   of=stock-idbloader.bin
sudo dd if=/dev/rdiskN bs=512 skip=16384  count=8192  of=stock-uboot.bin
sudo dd if=/dev/rdiskN bs=512 skip=24576  count=8192  of=stock-trust.bin
md5 -q stock-uboot.bin      # macOS (Linux: md5sum)
```

Compare the MD5s with `clone-uboot/uboot_stable.img` (`8e99821672d0...`), `trust.img` and `idbloader.img`.

On Windows the same works in WSL with `/dev/sdX`, or use HDD Raw Copy Tool to image the card first.

## 7. Safety

Every approach here touches **only the SD card**. The console's internal storage (eMMC) is never written, and nothing is flashed onto the device itself. Worst case is an SD card that does not boot, fixed by re-flashing. No brick path exists.
