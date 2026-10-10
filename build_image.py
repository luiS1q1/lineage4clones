#!/usr/bin/env python3
"""
LineageOS 18.1 (Andr36oid) Disk Image Builder for R36S Clones
(Clone Type 2 Panel 1 with Amplifier / 2 RAM Chips)

This script automates fusing the clone bootloader, creating a Hybrid MBR,
and updating the BOOT partition with the patched panel 1 DTB and kernel.
"""

import os
import sys
import struct
import zipfile
import shutil

# Offsets in 512-byte sectors (Rockchip RK3326 standard layout)
IDB_SEEK = 64        # 32 KiB
UBOOT_SEEK = 16384   # 8  MiB
TRUST_SEEK = 24576   # 12 MiB
BOOT_OFFSET_BYTES = 16777216  # 32768 sectors * 512 = 16 MiB

def fuse_bootloader(image_path, idb_path, uboot_path, trust_path):
    print(f"[*] Fusing clone bootloader into: {image_path}")
    with open(idb_path, 'rb') as f:
        idb = f.read()
    with open(uboot_path, 'rb') as f:
        ub = f.read()
    with open(trust_path, 'rb') as f:
        tr = f.read()

    with open(image_path, 'r+b') as f:
        f.seek(IDB_SEEK * 512)
        f.write(idb)
        print(f"    [+] Wrote idbloader.img at sector {IDB_SEEK} ({len(idb)} bytes)")

        f.seek(UBOOT_SEEK * 512)
        f.write(ub)
        print(f"    [+] Wrote uboot.img at sector {UBOOT_SEEK} ({len(ub)} bytes)")

        f.seek(TRUST_SEEK * 512)
        f.write(tr)
        print(f"    [+] Wrote trust.img at sector {TRUST_SEEK} ({len(tr)} bytes)")

def write_clean_mbr(image_path):
    print("[*] Writing clean MBR to sector 0 and wiping GPT sectors 1-63...")
    with open(image_path, 'r+b') as f:
        # 1. Zero out sectors 1 to 63 (complete removal of EFI PART and GPT partition array)
        f.seek(512)
        f.write(b'\x00' * (63 * 512))
        print("    [+] Zeroed sectors 1-63 (GPT headers completely removed)")

        # 2. Write Sector 0 MBR matching dArkOS4Clone layout
        f.seek(0)
        mbr = bytearray(f.read(512))

        # Disk signature (from dArkOS4Clone)
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
    print("[*] Patching FAT32 BOOT partition...")
    try:
        from pyfatfs.PyFatFS import PyFatFS
    except ImportError:
        print("[!] pyfatfs not installed. Installing via pip...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyfatfs"])
        from pyfatfs.PyFatFS import PyFatFS

    fs = PyFatFS(image_path, offset=BOOT_OFFSET_BYTES)

    # 1. Write kernel to both /Image and /Image-resizing (used on first boot)
    if os.path.exists(kernel_path):
        with open(kernel_path, 'rb') as f:
            kdata = f.read()
        if fs.exists('/Image'):
            fs.remove('/Image')
        fs.create('/Image')
        fs.writebytes('/Image', kdata)
        print(f"    [+] Created & updated /Image ({len(kdata)} bytes)")

        if fs.exists('/Image-resizing'):
            fs.remove('/Image-resizing')
        fs.create('/Image-resizing')
        fs.writebytes('/Image-resizing', kdata)
        print(f"    [+] Created & updated /Image-resizing ({len(kdata)} bytes)")

    # 2. Write DTB
    if os.path.exists(dtb_path):
        with open(dtb_path, 'rb') as f:
            dtbdata = f.read()
        if fs.exists('/rk3326-r36s-android.dtb'):
            fs.remove('/rk3326-r36s-android.dtb')
        fs.create('/rk3326-r36s-android.dtb')
        fs.writebytes('/rk3326-r36s-android.dtb', dtbdata)
        print(f"    [+] Created & updated /rk3326-r36s-android.dtb ({len(dtbdata)} bytes)")

    # 3. Enable live on-screen logs in boot.ini
    if fs.exists('/boot.ini'):
        bini = fs.readtext('/boot.ini')
        if 'console=tty0' not in bini:
            bini_new = bini.replace('console=ttyS2,115200n8', 'console=tty0 console=ttyS2,115200n8 loglevel=7')
            fs.writetext('/boot.ini', bini_new)
            print("    [+] Enabled on-screen live log in /boot.ini")

    if fs.exists('/boot.ini-android'):
        bini_a = fs.readtext('/boot.ini-android')
        if 'console=tty0' not in bini_a:
            bini_a_new = bini_a.replace('console=ttyS2,115200n8', 'console=tty0 console=ttyS2,115200n8 loglevel=7')
            fs.writetext('/boot.ini-android', bini_a_new)
            print("    [+] Enabled on-screen live log in /boot.ini-android")

    fs.close()
    print("[+] BOOT partition successfully patched!")

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    idb_path = os.path.join(base_dir, "clone-uboot", "idbloader.img")
    # Use verified clone U-Boot (identical to working dArkOS4Clone release)
    uboot_path = os.path.join(base_dir, "clone-uboot", "uboot_oct05_emmc.img")
    trust_path = os.path.join(base_dir, "clone-uboot", "trust.img")
    dtb_path = os.path.join(base_dir, "boot-files", "rk3326-r36s-android.dtb")
    kernel_path = os.path.join(base_dir, "boot-files", "Image")

    img_dir = os.path.join(base_dir, "build-img")
    target_img = os.path.join(img_dir, "lineage-18.1-r36s-clone-type2-amp.img")

    # If the image was modified previously, extract fresh base if zip exists
    zip_path = os.path.join(img_dir, "lineage-18.1-20250902-2052-r36s-android.img.zip")
    if not os.path.exists(target_img):
        if os.path.exists(zip_path):
            print(f"[*] Extracting base image from {zip_path}...")
            with zipfile.ZipFile(zip_path) as z:
                z.extractall(img_dir)
            extracted = [f for f in os.listdir(img_dir) if f.endswith('.img') and f != "lineage-18.1-r36s-clone-type2-amp.img"][0]
            shutil.move(os.path.join(img_dir, extracted), target_img)
        else:
            print(f"[!] Target image {target_img} not found and no base zip present!")
            sys.exit(1)

    fuse_bootloader(target_img, idb_path, uboot_path, trust_path)
    write_clean_mbr(target_img)
    patch_boot_partition(target_img, dtb_path, kernel_path)
    print("\n[SUCCESS] Clone image is fully built and ready to flash!")

if __name__ == "__main__":
    main()
