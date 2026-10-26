#!/usr/bin/env python3
"""
Updates mounted SD card (E:\) with standalone uInitrd, patched DTB, and fallback boot.ini.
"""

import ctypes
import hashlib
import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_UINITRD = os.path.join(BASE_DIR, "boot-files", "uInitrd")
SRC_DTB = os.path.join(BASE_DIR, "boot-files", "rk3326-r36s-android.dtb")
TARGET_DRIVE = "E:\\"
DST_UINITRD = os.path.join(TARGET_DRIVE, "uInitrd")
DST_DTB = os.path.join(TARGET_DRIVE, "rk3326-r36s-android.dtb")
DST_BOOT_INI = os.path.join(TARGET_DRIVE, "boot.ini")

BOOT_INI_CONTENT = """odroidgoa-uboot-config

setenv bootrootfs "fw_devlink=permissive rootfstype=ext4 rootwait init=/init consoleblank=0 swiotlb=1 coherent_pool=1m"

setenv console "console=ttyS2,115200n8 androidboot.console=tty0 rdinit=/linuxrc console=tty0"

setenv android "firmware_class.path=/vendor/firmware androidboot.hardware=rk30board androidboot.selinux=permissive"

setenv android2 "androidboot.revision=${hwrev} androidboot.serialno=${serial#} androidboot.boot_devices=ff3770000.dwmmc"

# Set load addresses
setenv kernel_addr_r "0x02000000"
setenv initrd_addr_r "0x01100000"
setenv fdt_addr_r "0x01f00000"

load mmc 1:1 ${kernel_addr_r} Image
load mmc 1:1 ${initrd_addr_r} uInitrd
load mmc 1:1 ${fdt_addr_r} rk3326-r36s-android.dtb

setenv bootargs "${bootrootfs} ${android} ${android2} ${console}"

fatwrite mmc 1:1 0x01f00000 UBOOT_OK.TXT 0x40
lcdputs "U-BOOT: Starting Kernel (0x01100000)..."
booti ${kernel_addr_r} ${initrd_addr_r} ${fdt_addr_r}
fatwrite mmc 1:1 0x01f00000 BOOTI_RET.TXT 0x40
lcdputs "U-BOOT: booti returned! Trying Image-resizing..."
load mmc 1:1 ${kernel_addr_r} Image-resizing
load mmc 1:1 ${fdt_addr_r} rk3326-r36s-android.dtb
booti ${kernel_addr_r} - ${fdt_addr_r}
fatwrite mmc 1:1 0x01f00000 BOTH_RET.TXT 0x40
lcdputs "ERROR: Both booti calls returned!"
""".replace("\r\n", "\n")


def file_checksums(filepath):
    with open(filepath, "rb") as f:
        data = f.read()
    return len(data), hashlib.md5(data).hexdigest(), hashlib.sha256(data).hexdigest()


def update_e_drive():
    print(f"[*] Checking if {TARGET_DRIVE} is mounted...")
    if not os.path.exists(TARGET_DRIVE):
        print(f"[!] Drive {TARGET_DRIVE} is not mounted.")
        return False

    # 1. Clean marker txt files from previous runs
    for marker in ["UBOOT_OK.TXT", "BOOTI_RET.TXT", "BOTH_RET.TXT", "ALIVE.TXT"]:
        p = os.path.join(TARGET_DRIVE, marker)
        if os.path.exists(p):
            os.remove(p)
            print(f"    [-] Removed old marker {p}")

    # 2. Copy DTB
    print(f"[*] Copying {SRC_DTB} to {DST_DTB}...")
    shutil.copy2(SRC_DTB, DST_DTB)
    dtb_size, dtb_md5, dtb_sha = file_checksums(DST_DTB)
    print(f"    [+] {DST_DTB} written ({dtb_size} bytes)")
    print(f"        MD5:    {dtb_md5}")
    print(f"        SHA256: {dtb_sha}")

    # 3. Copy uInitrd
    print(f"[*] Copying {SRC_UINITRD} to {DST_UINITRD}...")
    shutil.copy2(SRC_UINITRD, DST_UINITRD)
    uinitrd_size, uinitrd_md5, uinitrd_sha = file_checksums(DST_UINITRD)
    print(f"    [+] {DST_UINITRD} written ({uinitrd_size} bytes)")
    print(f"        MD5:    {uinitrd_md5}")
    print(f"        SHA256: {uinitrd_sha}")

    # 4. Update boot.ini
    print(f"[*] Updating {DST_BOOT_INI}...")
    with open(DST_BOOT_INI, "wb") as f:
        data = BOOT_INI_CONTENT.encode("ascii")
        f.write(data)
        f.flush()
        os.fsync(f.fileno())

    boot_size, boot_md5, boot_sha = file_checksums(DST_BOOT_INI)
    print(f"    [+] {DST_BOOT_INI} updated ({boot_size} bytes)")
    print(f"        MD5:    {boot_md5}")
    print(f"        SHA256: {boot_sha}")

    # Flush volume buffers on Windows
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateFileW(
            r"\\.\E:",
            0x10000000 | 0x40000000,
            0x00000001 | 0x00000002,
            None,
            3,
            0,
            None,
        )
        if handle != -1:
            kernel32.FlushFileBuffers(handle)
            kernel32.CloseHandle(handle)
            print("    [+] Flushed E: volume buffers successfully via FlushFileBuffers")
        else:
            print("    [*] File synced (volume handle returned -1)")
    except Exception as ex:
        print(f"    [*] FlushFileBuffers note: {ex}")

    print(f"[SUCCESS] Drive {TARGET_DRIVE} updated and synced successfully!")
    return True


if __name__ == "__main__":
    update_e_drive()
