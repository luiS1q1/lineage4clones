#!/usr/bin/env python3
r"""
Clean up E:\ and configure E:\boot.ini and E:\boot.ini-android for LineageOS 18.1:
- Remove previous test logs (ALIVE.TXT, error.log, etc.) from E:\ for a fresh resize run.
- Write the new true 4.19 Clone DTB to boot-files/rk3326-r36s-android.dtb and E:\rk3326-r36s-android.dtb (UHS-I disabled).
- Synchronize gpt_head.bin (LBA 0..33) to E:\gpt_head.bin.
- Synchronize patched Image-resizing and uInitrd to E:\.
- Set E:\boot.ini to the resizing bootloader configuration (booting Image-resizing + uInitrd + 4.19 DTB).
- Set E:\boot.ini-android to the native Android boot configuration (booting Image directly with root=/dev/mmcblk0p2).
- Flush E:\ volume buffers.
"""

import os
import sys
import hashlib
import shutil
import ctypes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOOT_FILES_DIR = os.path.join(BASE_DIR, "boot-files")
SRC_DTB = os.path.join(BOOT_FILES_DIR, "rk3326-r36s-android.dtb")
SRC_UINITRD = os.path.join(BOOT_FILES_DIR, "uInitrd")
SRC_IMG_RESIZING = os.path.join(BOOT_FILES_DIR, "Image-resizing")
SRC_GPT_HEAD = os.path.join(BOOT_FILES_DIR, "gpt_head.bin")

E_DRIVE = "E:\\"
E_DTB = os.path.join(E_DRIVE, "rk3326-r36s-android.dtb")
E_UINITRD = os.path.join(E_DRIVE, "uInitrd")
E_IMG_RESIZING = os.path.join(E_DRIVE, "Image-resizing")
E_GPT_HEAD = os.path.join(E_DRIVE, "gpt_head.bin")
E_BOOT_INI = os.path.join(E_DRIVE, "boot.ini")
E_BOOT_INI_ANDROID = os.path.join(E_DRIVE, "boot.ini-android")
E_BOOT_INI_RESIZE = os.path.join(E_DRIVE, "boot.ini-resize")


BOOT_INI_CONTENT = """odroidgoa-uboot-config

setenv bootrootfs "rdinit=/linuxrc fw_devlink=permissive consoleblank=0 swiotlb=1 coherent_pool=1m"

setenv console "console=tty0 fbcon=rotate:0 console=ttyS2,115200n8 androidboot.console=tty0"

setenv android "firmware_class.path=/vendor/firmware androidboot.hardware=rk30board androidboot.selinux=permissive"

setenv android2 "androidboot.revision=${hwrev} androidboot.serialno=${serial#} androidboot.boot_devices=ff370000.dwmmc"

# Set load addresses (0x04000000 is safely above 25MB Image-resizing at 0x02000000)
setenv kernel_addr_r "0x02000000"
setenv initrd_addr_r "0x04000000"
setenv fdt_addr_r "0x01f00000"

load mmc 1:1 ${kernel_addr_r} Image-resizing
load mmc 1:1 ${initrd_addr_r} uInitrd
load mmc 1:1 ${fdt_addr_r} rk3326-r36s-android.dtb

setenv bootargs "${bootrootfs} ${android} ${android2} ${console}"

lcdputs "U-BOOT: Starting LineageOS 18.1..."
booti ${kernel_addr_r} ${initrd_addr_r} ${fdt_addr_r}
""".replace("\r\n", "\n")


BOOT_INI_ANDROID_CONTENT = """odroidgoa-uboot-config

setenv bootrootfs "root=/dev/mmcblk0p2 fw_devlink=permissive rootfstype=ext4 rootwait init=/init consoleblank=0 swiotlb=1 coherent_pool=1m"

setenv console "console=tty0 fbcon=rotate:0 console=ttyS2,115200n8 androidboot.console=tty0"

setenv android "firmware_class.path=/vendor/firmware androidboot.hardware=rk30board androidboot.selinux=permissive"

setenv android2 "androidboot.revision=${hwrev} androidboot.serialno=${serial#} androidboot.boot_devices=ff370000.dwmmc"

# Set load addresses
setenv kernel_addr_r "0x02000000"
setenv fdt_addr_r "0x01f00000"

# If FN pressed
if gpio input c4
then
    load mmc 1:1 ${kernel_addr_r} Image-recovery
else
    load mmc 1:1 ${kernel_addr_r} Image
fi

load mmc 1:1 ${fdt_addr_r} rk3326-r36s-android.dtb

setenv bootargs "${bootrootfs} ${android} ${android2} ${console}"

# Boot
booti ${kernel_addr_r} - ${fdt_addr_r}
""".replace("\r\n", "\n")


def update():
    print("=" * 72)
    print("Updating E:\\ SD Card for Native LineageOS 18.1 Boot & Resizing")
    print("=" * 72)

    if not os.path.exists(E_DRIVE):
        raise RuntimeError("Drive E:\\ is not accessible!")

    # 1. Clean previous run logs and temporary test files from E:\
    logs_and_temps = [
        "ALIVE.TXT",
        "dmesg_early.log",
        "dmesg_final.log",
        "error.log",
        "fb_status.log",
        "partitions_before.log",
        "partitions_after.log",
        "rebootfailed.log",
        "Image-arkos",
        "arkos.dtb",
        "UBOOT_OK.TXT",
    ]
    for item in logs_and_temps:
        path = os.path.join(E_DRIVE, item)
        if os.path.exists(path):
            os.remove(path)
            print(f"[-] Cleaned old file from E:\\: {item}")

    # 2. Synchronize true 4.19 Clone DTB to boot-files and E:\
    if not os.path.exists(SRC_DTB):
        raise FileNotFoundError(f"Source DTB not found at {SRC_DTB}. Run build_lineage_dtb.py first!")

    with open(SRC_DTB, "rb") as f:
        dtb_data = f.read()

    with open(E_DTB, "wb") as f:
        f.write(dtb_data)

    dtb_sha = hashlib.sha256(dtb_data).hexdigest()
    print(f"[+] Synchronized {E_DTB}: {len(dtb_data)} bytes (sha256: {dtb_sha})")

    # 3. Synchronize gpt_head.bin
    if os.path.exists(SRC_GPT_HEAD):
        shutil.copyfile(SRC_GPT_HEAD, E_GPT_HEAD)
        print(f"[+] Synchronized {E_GPT_HEAD}: {os.path.getsize(E_GPT_HEAD)} bytes")

    # 4. Synchronize patched Image-resizing
    if os.path.exists(SRC_IMG_RESIZING):
        shutil.copyfile(SRC_IMG_RESIZING, E_IMG_RESIZING)
        print(f"[+] Synchronized {E_IMG_RESIZING}: {os.path.getsize(E_IMG_RESIZING)} bytes")

    # 5. Synchronize uInitrd
    if os.path.exists(SRC_UINITRD):
        shutil.copyfile(SRC_UINITRD, E_UINITRD)
        print(f"[+] Synchronized {E_UINITRD}: {os.path.getsize(E_UINITRD)} bytes")

    # 6. Reset E:\boot.ini to resizing boot configuration
    with open(E_BOOT_INI, "w", newline="\n") as f:
        f.write(BOOT_INI_CONTENT)
    print(f"[+] Updated {E_BOOT_INI} (resizing bootloader) ({len(BOOT_INI_CONTENT)} bytes)")

    # Save local copy in boot-files
    with open(os.path.join(BOOT_FILES_DIR, "boot.ini"), "w", newline="\n") as f:
        f.write(BOOT_INI_CONTENT)

    # 7. Write LineageOS boot.ini-android
    with open(E_BOOT_INI_ANDROID, "w", newline="\n") as f:
        f.write(BOOT_INI_ANDROID_CONTENT)
    print(f"[+] Updated {E_BOOT_INI_ANDROID} (native Android boot) ({len(BOOT_INI_ANDROID_CONTENT)} bytes)")

    # Save local copy in boot-files
    with open(os.path.join(BOOT_FILES_DIR, "boot.ini-android"), "w", newline="\n") as f:
        f.write(BOOT_INI_ANDROID_CONTENT)

    # Also save backup boot.ini-resize on E:\
    with open(E_BOOT_INI_RESIZE, "w", newline="\n") as f:
        f.write(BOOT_INI_CONTENT)
    print(f"[+] Updated {E_BOOT_INI_RESIZE} ({len(BOOT_INI_CONTENT)} bytes)")

    # 8. Flush drive buffers
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateFileW(
            r"\\.\E:",
            0x40000000 | 0x80000000,  # GENERIC_READ | GENERIC_WRITE
            1 | 2,                     # FILE_SHARE_READ | FILE_SHARE_WRITE
            None,
            3,                         # OPEN_EXISTING
            0,
            None
        )
        if handle != -1 and handle != 0xFFFFFFFFFFFFFFFF:
            kernel32.FlushFileBuffers(handle)
            kernel32.CloseHandle(handle)
            print("[+] Successfully flushed E:\\ volume buffers via Win32 API")
        else:
            print("[*] Note: Volume handle returned code, relying on standard OS flush")
    except Exception as e:
        print(f"[*] Note on Win32 flush: {e}")

    print("\n[+] E:\\ contents after cleanup and update:")
    for item in sorted(os.listdir(E_DRIVE)):
        full_path = os.path.join(E_DRIVE, item)
        size = os.path.getsize(full_path) if os.path.isfile(full_path) else "<DIR>"
        print(f"    - {item:28s} {str(size):>12s}")

    print("=" * 72)
    print("E:\\ is clean, configured for resizing, and ready to boot!")
    print("=" * 72)


if __name__ == "__main__":
    update()
