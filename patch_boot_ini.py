#!/usr/bin/env python3
import os

ini_lines = [
    "odroidgoa-uboot-config",
    "",
    'setenv bootrootfs "root=/dev/mmcblk0p2 fw_devlink=permissive rootfstype=ext4 rootwait init=/init consoleblank=0 swiotlb=1 coherent_pool=1m"',
    "",
    'setenv console "console=tty0 fbcon=rotate:0 console=ttyS2,115200n8 androidboot.console=tty0"',
    "",
    'setenv android "firmware_class.path=/vendor/firmware androidboot.hardware=rk30board androidboot.selinux=permissive"',
    "",
    'setenv android2 "androidboot.revision=${hwrev} androidboot.serialno=${serial#} androidboot.boot_devices=ff370000.dwmmc"',
    "",
    "# Set load addresses",
    'setenv kernel_addr_r "0x02000000"',
    'setenv fdt_addr_r "0x01f00000"',
    "",
    "# If FN pressed",
    "if gpio input c4",
    "then",
    "    load mmc 1:1 ${kernel_addr_r} Image-recovery",
    "else",
    "    load mmc 1:1 ${kernel_addr_r} Image",
    "fi",
    "",
    "load mmc 1:1 ${fdt_addr_r} rk3326-r36s-android.dtb",
    "",
    'setenv bootargs "${bootrootfs} ${android} ${android2} ${console}"',
    "",
    "# Boot",
    "booti ${kernel_addr_r} - ${fdt_addr_r}",
    "",
]

ini_content = "\n".join(ini_lines).encode("utf-8")

for p in ["boot-files/boot.ini-android", "E:/boot.ini", "E:/boot.ini-android"]:
    if os.path.exists(os.path.dirname(p)) or p.startswith("E:"):
        with open(p, "wb") as f:
            f.write(ini_content)
        print("Updated", p)
