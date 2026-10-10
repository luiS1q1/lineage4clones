#!/usr/bin/env python3
"""
LineageOS 18.1 (Andr36oid) Disk Image Builder for R36S Clones
(Clone Type 2 Panel 1 with Amplifier / 2 RAM Chips)

This script automates fusing the clone bootloader and updating the BOOT partition
with the patched panel 1 DTB and kernel.
"""

import os
import sys
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

    # 1. Write kernel
    if os.path.exists(kernel_path):
        with open(kernel_path, 'rb') as f:
            kdata = f.read()
        fs.writebytes('/Image', kdata)
        print(f"    [+] Updated /Image ({len(kdata)} bytes)")

    # 2. Write DTB
    if os.path.exists(dtb_path):
        with open(dtb_path, 'rb') as f:
            dtbdata = f.read()
        fs.writebytes('/rk3326-r36s-android.dtb', dtbdata)
        print(f"    [+] Updated /rk3326-r36s-android.dtb ({len(dtbdata)} bytes)")

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
    uboot_path = os.path.join(base_dir, "clone-uboot", "uboot_stable.img")
    trust_path = os.path.join(base_dir, "clone-uboot", "trust.img")
    dtb_path = os.path.join(base_dir, "boot-files", "rk3326-r36s-android.dtb")
    kernel_path = os.path.join(base_dir, "boot-files", "Image")

    img_dir = os.path.join(base_dir, "build-img")
    target_img = os.path.join(img_dir, "lineage-18.1-r36s-clone-type2-amp.img")

    if not os.path.exists(target_img):
        zip_path = os.path.join(img_dir, "lineage-18.1-20250902-2052-r36s-android.img.zip")
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
    patch_boot_partition(target_img, dtb_path, kernel_path)
    print("\n[SUCCESS] Clone image is fully built and ready to flash!")

if __name__ == "__main__":
    main()
