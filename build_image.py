#!/usr/bin/env python3
"""
LineageOS 18.1 (Andr36oid) Disk Image Builder for R36S Clones
(Clone Type 2 Panel 1 with Amplifier / 2 RAM Chips)

Delta-Bisect Modes:
  Mode T1:
    Pure stock GPT layout + fused clone bootloader binaries (sectors 64, 16384, 24576).
    MBR (sector 0), GPT (sectors 1-63), and FAT32 are left 100% untouched.
    Output: build-img/lineage-test-T1.img

  Mode T2:
    Fresh base + fused clone bootloaders + clean MBR + zeroed sectors 1-63.
    FAT32 BOOT partition left untouched.
    Output: build-img/lineage-test-T2.img

  Mode T3:
    Mode T2 + patched FAT32 BOOT partition:
    - Kernel Image copied to /Image and /Image-resizing
    - Panel 1 + Amp DTB copied to /rk3326-r36s-android.dtb
    - boot.ini patched with root=/dev/mmcblk0p2 and live on-screen console
    - Archive attribute 0x20 set on modified files
    Output: build-img/lineage-test-T3.img
"""

import argparse
import hashlib
import os
import shutil
import struct
import sys
import zipfile

# Sector constants (Rockchip RK3326 standard layout: 512-byte sectors)
SECTOR_SIZE = 512
IDB_SEEK = 64        # 32 KiB
UBOOT_SEEK = 16384   # 8  MiB
TRUST_SEEK = 24576   # 12 MiB
BOOT_OFFSET_BYTES = 16777216  # 32768 sectors * 512 = 16 MiB

# Expected cryptographic hashes from verified dArkOS4Clone release
EXPECTED_HASHES = {
    "Sector 64 (raw idbloader 176452B)": "065c4e4e3e77414f636cbcfd7ee88a0b",
    "Sector 64..408 (345 sectors idbloader)": "9832387ef83261e9cbe2901962066d7b",
    "Sector 16384..24575 (uboot)": "a1a164e2451f5d0f3743f700a463de11",
    "Sector 24576..32767 (trust)": "ba8fd9c133787ae54cc75fc35858eff3",
}

def extract_fresh_base(zip_path, target_img):
    """
    Extracts a pristine copy of the stock LineageOS image from zip directly to target_img.
    """
    print(f"[*] Extracting fresh base image to: {target_img}")
    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"Base image zip not found at: {zip_path}")

    # Ensure parent directory exists
    os.makedirs(os.path.dirname(os.path.abspath(target_img)), exist_ok=True)

    with zipfile.ZipFile(zip_path, 'r') as z:
        img_names = [n for n in z.namelist() if n.endswith('.img')]
        if not img_names:
            raise RuntimeError(f"No .img found in base zip: {zip_path}")
        src_name = img_names[0]
        print(f"    [+] Streaming '{src_name}' from zip...")
        with z.open(src_name) as src, open(target_img, 'wb') as dst:
            shutil.copyfileobj(src, dst, length=8 * 1024 * 1024)

    img_size = os.path.getsize(target_img)
    print(f"    [+] Fresh base extracted ({img_size} bytes)")
    return target_img

def fuse_bootloader(image_path, idb_path, uboot_path, trust_path):
    """
    Fuses the 3 clone bootloader binaries into their designated sector offsets.
    """
    print(f"[*] Fusing clone bootloader into: {image_path}")
    with open(idb_path, 'rb') as f:
        idb = f.read()
    with open(uboot_path, 'rb') as f:
        ub = f.read()
    with open(trust_path, 'rb') as f:
        tr = f.read()

    with open(image_path, 'r+b') as f:
        # Sector 64: idbloader.img
        f.seek(IDB_SEEK * SECTOR_SIZE)
        f.write(idb)
        remainder = (SECTOR_SIZE - (len(idb) % SECTOR_SIZE)) % SECTOR_SIZE
        if remainder:
            f.write(b'\x00' * remainder)
        print(f"    [+] Wrote idbloader.img at sector {IDB_SEEK} ({len(idb)} bytes + {remainder} padding bytes)")

        # Sector 16384: uboot.img
        f.seek(UBOOT_SEEK * SECTOR_SIZE)
        f.write(ub)
        print(f"    [+] Wrote uboot.img at sector {UBOOT_SEEK} ({len(ub)} bytes)")

        # Sector 24576: trust.img
        f.seek(TRUST_SEEK * SECTOR_SIZE)
        f.write(tr)
        print(f"    [+] Wrote trust.img at sector {TRUST_SEEK} ({len(tr)} bytes)")

def write_clean_mbr(image_path):
    """
    Applies clean MBR to Sector 0 and zeroes out GPT sectors 1-63.
    Matches the working dArkOS4Clone layout.
    """
    print(f"[*] Writing clean MBR to sector 0 and zeroing GPT sectors 1-63 in: {image_path}")
    with open(image_path, 'r+b') as f:
        # 1. Zero out sectors 1 to 63 (complete removal of EFI PART and GPT partition array)
        f.seek(SECTOR_SIZE)
        f.write(b'\x00' * (63 * SECTOR_SIZE))
        print("    [+] Zeroed sectors 1-63 (GPT headers completely removed)")

        # 2. Write Sector 0 MBR matching dArkOS4Clone layout
        f.seek(0)
        mbr = bytearray(f.read(SECTOR_SIZE))

        # Disk signature (from dArkOS4Clone: 0x1279d432)
        mbr[440:444] = b'\x12\x79\xd4\x32'
        mbr[444:446] = b'\x00\x00'

        # Partition 1: BOOT (FAT32), active=0x00, type=0x0b, start=32768, num=1048576 (512 MB)
        part1 = struct.pack('<B3sB3sII',
            0x00,
            b'\x40\x01\x40',
            0x0b,               # FAT32 CHS
            b'\xfe\xc2\xff',
            32768,
            1048576
        )
        # Partition 2: system (Linux EXT4), active=0x00, type=0x83, start=1081344, num=4619665 (~2.2 GB)
        part2 = struct.pack('<B3sB3sII',
            0x00,
            b'\xfe\xc2\xff',
            0x83,               # Linux native
            b'\xfe\xc2\xff',
            1081344,
            4619665
        )

        mbr[446:462] = part1
        mbr[462:478] = part2
        mbr[478:494] = b'\x00' * 16
        mbr[494:510] = b'\x00' * 16
        mbr[510:512] = b'\x55\xaa'

        f.seek(0)
        f.write(mbr)
        print("    [+] Clean MBR written: Partition 1 (FAT32, 512 MB), Partition 2 (EXT4, 2.2 GB)")

def patch_boot_partition(image_path, dtb_path, kernel_path):
    """
    Patches FAT32 BOOT partition cleanly:
    - Preserves /Image-resizing (25 MB stock first-boot resizer with embedded initramfs)
    - Preserves stock /boot.ini (boots Image-resizing from ramdisk on first boot)
    - Writes Clone Type 2 Panel 1 DTB to /rk3326-r36s-android.dtb
    - Writes AMUX-supported kernel to /Image (used by boot.ini-android after first boot resize)
    - Sets Archive attribute 0x20 on modified entries
    """
    print(f"[*] Patching FAT32 BOOT partition in: {image_path}...")
    try:
        from pyfatfs.PyFatFS import PyFatFS
    except ImportError:
        print("[!] pyfatfs not installed. Installing via pip...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyfatfs"])
        from pyfatfs.PyFatFS import PyFatFS

    fs = PyFatFS(image_path, offset=BOOT_OFFSET_BYTES)

    # 1. Write kernel ONLY to /Image (used by boot.ini-android on normal boots)
    # DO NOT touch /Image-resizing (which contains the 25 MB first-boot resizing ramdisk)!
    if os.path.exists(kernel_path):
        with open(kernel_path, 'rb') as f:
            kdata = f.read()
        if fs.exists('/Image'):
            fs.remove('/Image')
        fs.create('/Image')
        fs.writebytes('/Image', kdata)
        print(f"    [+] Updated /Image with patched kernel ({len(kdata)} bytes)")
        if fs.exists('/Image-resizing'):
            res_entry = fs.fs.root_dir.get_entry('Image-resizing')
            print(f"    [*] Preserved stock /Image-resizing intact ({res_entry.filesize} bytes)")
    else:
        print(f"    [!] Warning: Kernel binary not found at {kernel_path}")

    # 2. Write Clone Type 2 Panel 1 + Amp DTB
    if os.path.exists(dtb_path):
        with open(dtb_path, 'rb') as f:
            dtbdata = f.read()
        if fs.exists('/rk3326-r36s-android.dtb'):
            fs.remove('/rk3326-r36s-android.dtb')
        fs.create('/rk3326-r36s-android.dtb')
        fs.writebytes('/rk3326-r36s-android.dtb', dtbdata)
        print(f"    [+] Updated /rk3326-r36s-android.dtb with Clone Panel 1 DTB ({len(dtbdata)} bytes)")
    else:
        print(f"    [!] Warning: DTB file not found at {dtb_path}")

    # 3. Stock boot.ini and boot.ini-android are left 100% intact:
    # Stock boot.ini boots Image-resizing from ramdisk without root=/dev/mmcblk0p2.
    # Stock boot.ini-android already contains root=/dev/mmcblk0p2 for subsequent boots.
    print("    [*] Preserved stock /boot.ini and /boot.ini-android intact (avoids ramdisk collision)")

    # 4. Set Archive attribute (0x20) on modified files
    target_entries = ['Image', 'rk3326-r36s-android.dtb']
    for fname in target_entries:
        if fs.exists('/' + fname):
            entry = fs.fs.root_dir.get_entry(fname)
            entry.attr = 0x20
            print(f"    [+] Set archive attribute (0x20) on /{fname}")

    fs.fs.update_directory_entry(fs.fs.root_dir)
    fs.close()
    print("[+] BOOT partition successfully patched and closed!")

def verify_image(image_path, mode, expected_uboot_md5=None):
    """
    Verifies image size, partition layout, and cryptographic sector hashes.
    """
    print(f"\n{'=' * 72}")
    print(f"[*] VERIFICATION RECORD FOR {os.path.basename(image_path)} (Mode {mode})")
    print(f"{'=' * 72}")

    size = os.path.getsize(image_path)
    print(f"[*] Total image size: {size} bytes ({size / (1024 * 1024):.2f} MB)")
    if size != 3221225472:
        print(f"[!] WARNING: Expected image size 3221225472 bytes, got {size}")

    with open(image_path, 'rb') as f:
        # Sector 0 MBR check
        f.seek(0)
        mbr = f.read(SECTOR_SIZE)
        has_mbr_sig = (mbr[510:512] == b'\x55\xaa')
        disk_sig = mbr[440:444].hex()
        part1_type = hex(mbr[450])
        part2_type = hex(mbr[466])

        # Sector 1 GPT header check
        f.seek(SECTOR_SIZE)
        gpt_header = f.read(SECTOR_SIZE)
        has_gpt_sig = (gpt_header[:8] == b'EFI PART')

        # Sectors 1-63 zero check
        f.seek(SECTOR_SIZE)
        sectors_1_63 = f.read(63 * SECTOR_SIZE)
        sectors_1_63_zeroed = (sectors_1_63 == b'\x00' * (63 * SECTOR_SIZE))

        # Sector 64 raw idbloader (176452 bytes)
        f.seek(IDB_SEEK * SECTOR_SIZE)
        idb_raw = f.read(176452)
        idb_raw_md5 = hashlib.md5(idb_raw).hexdigest()

        # Sector 64..408 (345 sectors = 176640 bytes)
        f.seek(IDB_SEEK * SECTOR_SIZE)
        s64_408 = f.read(345 * SECTOR_SIZE)
        s64_408_md5 = hashlib.md5(s64_408).hexdigest()

        # Sector 16384..24575 (8192 sectors uboot)
        f.seek(UBOOT_SEEK * SECTOR_SIZE)
        s_uboot = f.read(8192 * SECTOR_SIZE)
        uboot_md5 = hashlib.md5(s_uboot).hexdigest()

        # Sector 24576..32767 (8192 sectors trust)
        f.seek(TRUST_SEEK * SECTOR_SIZE)
        s_trust = f.read(8192 * SECTOR_SIZE)
        trust_md5 = hashlib.md5(s_trust).hexdigest()

    print("[*] Partition & Layout Verification:")
    if mode == "T1":
        print(f"    - MBR Signature (0x55AA): {'VALID' if has_mbr_sig else 'INVALID'}")
        print(f"    - Primary GPT Header (LBA 1 'EFI PART'): {'PRESENT (Stock GPT intact)' if has_gpt_sig else 'MISSING'}")
        print(f"    - Sectors 1-63 zeroed: {sectors_1_63_zeroed} (Expected: False for pure GPT)")
    else:  # T2, T3
        print(f"    - MBR Signature (0x55AA): {'VALID' if has_mbr_sig else 'INVALID'}")
        print(f"    - MBR Disk Signature: 0x{disk_sig} (Expected: 0x1279d432)")
        print(f"    - MBR Part 1 Type: {part1_type} (Expected: 0x0b FAT32)")
        print(f"    - MBR Part 2 Type: {part2_type} (Expected: 0x83 EXT4)")
        print(f"    - Primary GPT Header (LBA 1 'EFI PART'): {'REMOVED' if not has_gpt_sig else 'WARNING: Remnant present!'}")
        print(f"    - Sectors 1-63 zeroed: {'YES (Clean layout)' if sectors_1_63_zeroed else 'NO (Error!)'}")

    print("[*] Cryptographic Sector Hashes:")
    exp_idb_raw = EXPECTED_HASHES["Sector 64 (raw idbloader 176452B)"]
    exp_s64_408 = EXPECTED_HASHES["Sector 64..408 (345 sectors idbloader)"]
    exp_uboot = expected_uboot_md5 or EXPECTED_HASHES["Sector 16384..24575 (uboot)"]
    exp_trust = EXPECTED_HASHES["Sector 24576..32767 (trust)"]

    print(f"    - Sector 64 raw (176452B):   {idb_raw_md5} -> {'MATCH [OK]' if idb_raw_md5 == exp_idb_raw else 'MISMATCH'}")
    print(f"    - Sector 64..408 (345 sec):  {s64_408_md5} -> {'MATCH [OK]' if s64_408_md5 == exp_s64_408 else 'MISMATCH'}")
    print(f"    - Sector 16384..24575 uboot: {uboot_md5} -> {'MATCH [OK]' if uboot_md5 == exp_uboot else 'MISMATCH'}")
    print(f"    - Sector 24576..32767 trust: {trust_md5} -> {'MATCH [OK]' if trust_md5 == exp_trust else 'MISMATCH'}")

    if mode == "T3":
        print("[*] FAT32 BOOT Partition Inspection:")
        try:
            from pyfatfs.PyFatFS import PyFatFS
            fs = PyFatFS(image_path, offset=BOOT_OFFSET_BYTES)
            for fname in ['Image', 'Image-resizing', 'rk3326-r36s-android.dtb', 'boot.ini']:
                if fs.exists('/' + fname):
                    entry = fs.fs.root_dir.get_entry(fname)
                    print(f"    - /{fname}: size={entry.filesize} bytes, attr={hex(entry.attr)} ({'ARCHIVE 0x20 OK' if entry.attr == 0x20 else 'MISMATCH'})")
            if fs.exists('/boot.ini'):
                bini = fs.readtext('/boot.ini')
                has_resizing = 'Image-resizing' in bini
                is_stock_bootrootfs = 'root=/dev/mmcblk0p2' not in bini
                print(f"    - /boot.ini loads Image-resizing: {'YES [OK]' if has_resizing else 'MISSING'}")
                print(f"    - /boot.ini preserves stock ramdisk: {'YES [OK]' if is_stock_bootrootfs else 'MODIFIED'}")
            fs.close()
        except Exception as e:
            print(f"    [!] Failed to inspect FAT32 partition: {e}")

    print(f"{'=' * 72}\n")

def build_mode(mode, base_dir, uboot_override=None):
    """
    Executes image build for specified mode (T1, T2, or T3).
    """
    img_dir = os.path.join(base_dir, "build-img")
    zip_path = os.path.join(img_dir, "lineage-18.1-20250902-2052-r36s-android.img.zip")

    idb_path = os.path.join(base_dir, "clone-uboot", "idbloader.img")
    # Verified working ArkOS clone binary is default (NOT debug!)
    uboot_path = uboot_override or os.path.join(base_dir, "clone-uboot", "uboot_oct05_emmc.img")
    trust_path = os.path.join(base_dir, "clone-uboot", "trust.img")

    dtb_path = os.path.join(base_dir, "boot-files", "rk3326-r36s-android.dtb")
    kernel_path = os.path.join(base_dir, "boot-files", "Image")

    target_img = os.path.join(img_dir, f"lineage-test-{mode}.img")

    print(f"\n>>> STARTING BUILD FOR DELTA-BISECT MODE {mode} <<<")
    print(f"Target image:  {target_img}")
    print(f"U-Boot binary: {uboot_path}")

    # Step 1: Always extract fresh base
    extract_fresh_base(zip_path, target_img)

    # Step 2: Fuse clone bootloaders (All modes T1, T2, T3)
    fuse_bootloader(target_img, idb_path, uboot_path, trust_path)

    # Step 3: Mode-specific operations
    if mode == "T1":
        print("[*] Mode T1: Keeping pure stock MBR/GPT and stock FAT32 partition untouched.")
    elif mode == "T2":
        print("[*] Mode T2: Writing clean MBR and zeroing sectors 1-63. FAT32 remains stock.")
        write_clean_mbr(target_img)
    elif mode == "T3":
        print("[*] Mode T3: Writing clean MBR, zeroing sectors 1-63, and patching FAT32.")
        write_clean_mbr(target_img)
        patch_boot_partition(target_img, dtb_path, kernel_path)
    else:
        raise ValueError(f"Unknown mode: {mode}")

    # Compute expected uboot hash if custom uboot was used
    expected_ub = None
    if uboot_override:
        with open(uboot_override, 'rb') as f:
            expected_ub = hashlib.md5(f.read()).hexdigest()

    # Step 4: Verification
    verify_image(target_img, mode, expected_uboot_md5=expected_ub)
    print(f"[SUCCESS] Mode {mode} image successfully built: {target_img}\n")
    return target_img

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    parser = argparse.ArgumentParser(
        description="LineageOS 18.1 Image Builder & Stage 2 Delta-Bisect for R36S Clones",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Delta-Bisect Modes:
  T1: Pure Stock Layout + Clone Bootloader
      Extracts fresh base from zip. Fuses idbloader (s64), uboot (s16384), trust (s24576).
      Leaves MBR (sector 0), GPT (sectors 1-63), and FAT32 100% untouched.
      Output: build-img/lineage-test-T1.img

  T2: Bootloader + Clean MBR / Zeroed Sectors 1-63
      Fresh base + clone bootloader + clean MBR + zeroed sectors 1-63. FAT32 untouched.
      Output: build-img/lineage-test-T2.img

  T3: Bootloader + Clean MBR + Patched FAT32
      Mode T2 + patched FAT32 (Kernel Image, DTB, boot.ini with root=/dev/mmcblk0p2, attr 0x20).
      Output: build-img/lineage-test-T3.img

  ALL:
      Builds all three images (T1, T2, T3) sequentially.
"""
    )
    parser.add_argument(
        "--test", "-t", "--mode", "-m",
        dest="test_mode",
        choices=["T1", "T2", "T3", "ALL"],
        default=None,
        help="Select Delta-Bisect test mode: T1, T2, T3, or ALL (default: builds T1 with usage instructions)"
    )
    parser.add_argument(
        "--uboot",
        default=None,
        help="Optional path to custom uboot image (defaults to clone-uboot/uboot_oct05_emmc.img)"
    )

    args = parser.parse_args()

    if args.test_mode is None:
        print("=" * 72)
        print("LineageOS 18.1 Image Builder - Delta-Bisect Stage 2")
        print("No --test mode specified. Defaulting to Mode T1.")
        print()
        print("Usage:")
        print("  python build_image.py --test T1   -> Build Mode T1 (Stock layout + clone bootloaders)")
        print("  python build_image.py --test T2   -> Build Mode T2 (T1 + clean MBR & zeroed sectors 1-63)")
        print("  python build_image.py --test T3   -> Build Mode T3 (T2 + patched FAT32 kernel/DTB/boot.ini)")
        print("  python build_image.py --test ALL  -> Build all three test images")
        print("=" * 72 + "\n")
        modes_to_build = ["T1"]
    elif args.test_mode.upper() == "ALL":
        modes_to_build = ["T1", "T2", "T3"]
    else:
        modes_to_build = [args.test_mode.upper()]

    for mode in modes_to_build:
        build_mode(mode, base_dir, uboot_override=args.uboot)

if __name__ == "__main__":
    main()
