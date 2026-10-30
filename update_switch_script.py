import os

def update_tools():
    script_content = """#!/bin/bash
echo "Switching to LineageOS Android..."
if [ ! -f /boot/boot.ini-android ]; then
    mkdir -p /mnt/boot
    mount /dev/mmcblk0p1 /mnt/boot 2>/dev/null || mount /dev/mmcblk1p1 /mnt/boot 2>/dev/null
    cp -f /mnt/boot/boot.ini-android /mnt/boot/boot.ini
    umount /mnt/boot
else
    cp -f /boot/boot.ini-android /boot/boot.ini
fi
sync
sleep 1
systemctl reboot -f 2>/dev/null || reboot
"""
    dest = r"F:\tools\Switch to Android.sh"
    if os.path.exists(r"F:\tools"):
        with open(dest, "wb") as f:
            f.write(script_content.replace("\r\n", "\n").encode("utf-8"))
        print(f"Updated {dest}")

if __name__ == "__main__":
    update_tools()
