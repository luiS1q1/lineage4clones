#!/usr/bin/env python3
"""
Extracts the CPIO initramfs from Image-resizing, patches linuxrc with early diagnostics,
heartbeat LED control (solid steady ON), 10s wait for boot storage, automated GPT restoration,
and partition resizing, embeds stock gpt_head.bin (LBA 0..33),
compresses with gzip (level 9), patches Image-resizing built-in initramfs in place,
and bundles into a standalone U-Boot legacy ramdisk image (uInitrd).
"""

import gzip
import hashlib
import os
import shutil
import struct
import sys
import time
import zipfile
import zlib
from pyfatfs.PyFatFS import PyFatFS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOOT_FILES_DIR = os.path.join(BASE_DIR, "boot-files")
T1_IMG = os.path.join(BASE_DIR, "build-img", "lineage-test-T1.img")
OUT_UINITRD = os.path.join(BOOT_FILES_DIR, "uInitrd")
OUT_IMG_RESIZING = os.path.join(BOOT_FILES_DIR, "Image-resizing")
OUT_GPT_HEAD = os.path.join(BOOT_FILES_DIR, "gpt_head.bin")
E_DRIVE = "E:\\"
E_UINITRD = os.path.join(E_DRIVE, "uInitrd")
E_IMG_RESIZING = os.path.join(E_DRIVE, "Image-resizing")
E_GPT_HEAD = os.path.join(E_DRIVE, "gpt_head.bin")

BOOT_OFFSET_BYTES = 32768 * 512
GZIP_OFFSET = 0xe19dd0
ORIG_GZIP_LEN = 9260659  # Exact length of original gzip stream in Image-resizing

NEW_LINUXRC = """#!/bin/sh

export PATH=/usr/bin:/bin:/usr/sbin:/sbin
/bin/busybox --install -s

/bin/busybox mount -t proc /proc /proc
/bin/busybox mount -t sysfs none /sys

# Set all LEDs (heartbeat LED) to steady solid ON immediately
for led in /sys/class/leds/*; do
    [ -d "$led" ] || continue
    echo none > "$led/trigger" 2>/dev/null || true
    echo 255 > "$led/brightness" 2>/dev/null || echo 1 > "$led/brightness" 2>/dev/null || true
done
if [ -e /sys/class/leds/blue:heartbeat/trigger ]; then
    echo none > /sys/class/leds/blue:heartbeat/trigger 2>/dev/null || true
    echo 255 > /sys/class/leds/blue:heartbeat/brightness 2>/dev/null || echo 1 > /sys/class/leds/blue:heartbeat/brightness 2>/dev/null || true
fi

echo /sbin/mdev >/proc/sys/kernel/hotplug
mdev -s

# Wait up to 10 seconds (100 iterations x 0.1s) for SD card boot partition
BOOTPART=""
BOOTDISK=""
for _ in $(seq 1 100); do
    mdev -s
    if [ -b "/dev/mmcblk0p1" ]; then BOOTPART="/dev/mmcblk0p1"; BOOTDISK="/dev/mmcblk0"; break; fi
    if [ -b "/dev/mmcblk1p1" ]; then BOOTPART="/dev/mmcblk1p1"; BOOTDISK="/dev/mmcblk1"; break; fi
    /bin/busybox sleep 0.1
done

mkdir -p /mnt
if [ -n "$BOOTPART" ]; then
    mount -t vfat "$BOOTPART" /mnt || mount -t auto "$BOOTPART" /mnt
fi

echo "BOOTED_INITRAMFS disk=$BOOTDISK part=$BOOTPART" > /mnt/ALIVE.TXT
dmesg > /mnt/dmesg_early.log 2>&1
cat /proc/partitions > /mnt/partitions_before.log 2>&1
ls -la /sys/class/graphics/ > /mnt/fb_status.log 2>&1
sync

if [ -z "$BOOTDISK" ]; then
    echo "ERROR: Boot disk not found after 100 iterations (10s)!" >> /mnt/ALIVE.TXT
    sync
    sleep 5
    reboot -f
fi

# Check for /dev/fb0 up to 30 iterations (3 seconds)
for _ in $(seq 1 30); do
	[ -e "/dev/fb0" ] && break
	/bin/busybox sleep 0.1
done

# Check display mode without aborting if missing/empty
if [ -e "/sys/class/graphics/fb0/modes" ]; then
    _mode="$(cat /sys/class/graphics/fb0/modes 2>/dev/null)"
    if [ -n "$_mode" ]; then
        echo "Setting framebuffer mode to: $_mode"
        echo "$_mode" > /sys/class/graphics/fb0/mode 2>/dev/null
    fi
fi

NOROMS=0
DEVICE=1
[ -f /mnt/rk3326-r36s-android.dtb ] && DEVICE=1 && echo "R36S Detected"
[ -f /mnt/rk3326-r36plus-android.dtb ] && DEVICE=2 && echo "R36Plus Detected"
[ -f /mnt/rk3326-r50s-android.dtb ] && DEVICE=3 && echo "R50S Detected"
[ -f /mnt/.noroms ] && NOROMS=1 && echo "Will not create ROMS partition!"

if [ $DEVICE = 1 ]; then
    cp /resizing_480.ppm /tmp/resizing.ppm
fi

if [ $DEVICE = 2 ]; then
    cp /resizing_720.ppm /tmp/resizing.ppm
fi

if [ $DEVICE = 3 ]; then
    cp /resizing_854.ppm /tmp/resizing.ppm
fi

if [ -e "/dev/fb0" ]; then
    /sbin/busybox-armv8l fbsplash -s /tmp/resizing.ppm 2>/dev/null || true
fi

busybox sleep 1

# GPT Restoration Phase: Ensure SD card has Stock LineageOS GPT partition table
NEED_GPT_RESTORE=0
if parted -s $BOOTDISK print 2>&1 | grep -qi "msdos"; then
    echo "Detected MBR (msdos) partition table on $BOOTDISK! GPT restoration required." >> /mnt/error.log 2>&1
    NEED_GPT_RESTORE=1
fi
if [ ! -b "${BOOTDISK}p5" ]; then
    echo "Partition 5 (trust) missing! GPT restoration required." >> /mnt/error.log 2>&1
    NEED_GPT_RESTORE=1
fi

if [ "$NEED_GPT_RESTORE" = 1 ]; then
    echo "Starting automatic GPT restoration..." >> /mnt/error.log 2>&1
    if [ -f /mnt/gpt_head.bin ]; then
        cp /mnt/gpt_head.bin /tmp/gpt_head.bin
    fi
    sync
    umount /mnt 2>/dev/null || true
    busybox sleep 1

    GPT_SOURCE=""
    if [ -f /gpt_head.bin ]; then
        GPT_SOURCE="/gpt_head.bin"
    elif [ -f /tmp/gpt_head.bin ]; then
        GPT_SOURCE="/tmp/gpt_head.bin"
    fi

    if [ -n "$GPT_SOURCE" ]; then
        echo "Writing Stock GPT blob (34 sectors) from $GPT_SOURCE to $BOOTDISK..." >> /tmp/gpt_restore.log 2>&1
        dd if="$GPT_SOURCE" of="$BOOTDISK" bs=512 count=34 conv=notrunc >> /tmp/gpt_restore.log 2>&1
        sync
        busybox sleep 1

        echo "Fixing backup GPT at end of disk..." >> /tmp/gpt_restore.log 2>&1
        printf "fix\\n" | parted ---pretend-input-tty "$BOOTDISK" print >> /tmp/gpt_restore.log 2>&1
        sync
        busybox sleep 1

        partprobe "$BOOTDISK" >> /tmp/gpt_restore.log 2>&1
        busybox sleep 1
        mdev -s
        busybox sleep 1
    else
        echo "ERROR: gpt_head.bin not found!" >> /tmp/gpt_restore.log 2>&1
    fi

    mount -t vfat "$BOOTPART" /mnt || mount -t auto "$BOOTPART" /mnt
    if [ -f /tmp/gpt_restore.log ]; then
        cat /tmp/gpt_restore.log >> /mnt/error.log 2>&1
    fi
    echo "GPT restoration phase completed." >> /mnt/error.log 2>&1
    sync
fi

# fsck system
if [ -b "${BOOTDISK}p2" ]; then
    fsck ${BOOTDISK}p2 >> /mnt/error.log 2>&1 || true
fi
busybox sleep 1

# Check if userdata partition (p6) already exists
if [ ! -b "${BOOTDISK}p6" ]; then
    echo "Creating userdata and EASYROMS partitions..." >> /mnt/error.log 2>&1
    TOTAL_SECTORS=$(cat /sys/block/$(basename $BOOTDISK)/size 2>/dev/null || echo 0)
    echo "Total disk sectors: $TOTAL_SECTORS" >> /mnt/error.log 2>&1
    if [ "$TOTAL_SECTORS" -gt 0 ] && [ "$TOTAL_SECTORS" -lt 40000000 ]; then
        echo "Disk size ($TOTAL_SECTORS sectors) under 40M sectors, setting NOROMS=1" >> /mnt/error.log 2>&1
        NOROMS=1
    fi

    # Ensure backup GPT is fixed
    printf "fix\\n" | parted ---pretend-input-tty $BOOTDISK print >> /mnt/error.log 2>&1

    if [ "$NOROMS" = 1 ]; then
        echo "Parted Stage: NOROMS=1" >> /mnt/error.log 2>&1
        parted -s $BOOTDISK mkpart userdata f2fs 5701009s 100% >> /mnt/error.log 2>&1
    else
        echo "Parted Stage: NOROMS=0" >> /mnt/error.log 2>&1
        parted -s $BOOTDISK mkpart userdata f2fs 5701009s 39255440s >> /mnt/error.log 2>&1
        parted -s $BOOTDISK mkpart EASYROMS fat32 39255441s 100% >> /mnt/error.log 2>&1
    fi

    busybox sleep 1
    sync
    partprobe $BOOTDISK >> /mnt/error.log 2>&1
    partprobe >> /mnt/error.log 2>&1
    mdev -s
    busybox sleep 1
    sync

    # Wait up to 5 seconds for p6 to appear
    for _ in $(seq 1 50); do
        [ -b "${BOOTDISK}p6" ] && break
        mdev -s
        busybox sleep 0.1
    done

    echo "Formatting userdata (${BOOTDISK}p6 with f2fs)..." >> /mnt/error.log 2>&1
    mkfs.f2fs ${BOOTDISK}p6 >> /mnt/error.log 2>&1

    if [ "$NOROMS" = 0 ]; then
        for _ in $(seq 1 50); do
            [ -b "${BOOTDISK}p7" ] && break
            mdev -s
            busybox sleep 0.1
        done
        echo "Formatting EASYROMS (${BOOTDISK}p7 with exfat)..." >> /mnt/error.log 2>&1
        mkfs.exfat ${BOOTDISK}p7 -n EASYROMS >> /mnt/error.log 2>&1
    fi
    sync
    busybox sleep 2
else
    echo "userdata partition (${BOOTDISK}p6) already exists." >> /mnt/error.log 2>&1
fi

# Dump post-resize diagnostics
cat /proc/partitions > /mnt/partitions_after.log 2>&1
dmesg > /mnt/dmesg_final.log 2>&1
sync

echo "Switching to Android Boot" >> /mnt/error.log 2>&1
if [ -f /mnt/boot.ini ]; then
    mv /mnt/boot.ini /mnt/boot.ini-resize
fi
if [ -f /mnt/boot.ini-android ]; then
    cp /mnt/boot.ini-android /mnt/boot.ini
fi
sync

if [ $DEVICE = 1 ]; then
    cp /resized_480.ppm /tmp/resized.ppm
fi
if [ $DEVICE = 2 ]; then
    cp /resized_720.ppm /tmp/resized.ppm
fi
if [ $DEVICE = 3 ]; then
    cp /resized_854.ppm /tmp/resized.ppm
fi

if [ -e "/dev/fb0" ]; then
    /sbin/busybox-armv8l fbsplash -s /tmp/resized.ppm 2>/dev/null || true
fi

sync
busybox sleep 3
umount /mnt 2>/dev/null || true
umount /proc 2>/dev/null || true
umount /sys 2>/dev/null || true

busybox reboot -f 2>/dev/null || reboot -f 2>/dev/null || true
busybox sleep 2
echo b > /proc/sysrq-trigger 2>/dev/null || true
""".replace("\r\n", "\n").encode("utf-8")


def build_uimage_header(payload: bytes) -> bytes:
    ih_magic = 0x27051956
    ih_time = int(time.time())
    ih_size = len(payload)
    ih_load = 0
    ih_ep = 0
    ih_dcrc = zlib.crc32(payload) & 0xFFFFFFFF
    ih_os = 5  # IH_OS_LINUX
    ih_arch = 22  # IH_ARCH_ARM64
    ih_type = 3  # IH_TYPE_RAMDISK
    ih_comp = 0  # IH_COMP_NONE (let Linux kernel decompressor unpack directly)
    ih_name = b"uInitrd\x00".ljust(32, b"\x00")

    hdr_zero = struct.pack(
        ">IIIIIIIBBBB32s",
        ih_magic, 0, ih_time, ih_size, ih_load, ih_ep, ih_dcrc,
        ih_os, ih_arch, ih_type, ih_comp, ih_name,
    )
    ih_hcrc = zlib.crc32(hdr_zero) & 0xFFFFFFFF
    final_hdr = struct.pack(
        ">IIIIIIIBBBB32s",
        ih_magic, ih_hcrc, ih_time, ih_size, ih_load, ih_ep, ih_dcrc,
        ih_os, ih_arch, ih_type, ih_comp, ih_name,
    )
    return final_hdr


def get_base_resizing_image() -> bytes:
    # Check backup in boot-files first
    bak_path = os.path.join(BOOT_FILES_DIR, "Image-resizing.bak")
    if os.path.exists(bak_path):
        print(f"[*] Reading base Image-resizing from backup: {bak_path}")
        with open(bak_path, "rb") as f:
            return f.read()

    # Check E:\Image-resizing
    if os.path.exists(E_IMG_RESIZING):
        print(f"[*] Reading base Image-resizing from SD drive: {E_IMG_RESIZING}")
        with open(E_IMG_RESIZING, "rb") as f:
            return f.read()

    # Check T1 image
    if os.path.exists(T1_IMG):
        print(f"[*] Reading base Image-resizing from {T1_IMG} (offset {BOOT_OFFSET_BYTES})...")
        fs = PyFatFS(T1_IMG, offset=BOOT_OFFSET_BYTES)
        data = fs.readbytes("/Image-resizing")
        fs.close()
        return data

    raise FileNotFoundError("Base Image-resizing kernel not found!")


def extract_or_get_gpt_blob() -> bytes:
    gpt_path = OUT_GPT_HEAD
    if os.path.exists(gpt_path):
        with open(gpt_path, "rb") as f:
            data = f.read()
            if len(data) == 34 * 512:
                return data

    # Extract from stock zip
    zip_path = os.path.join(BASE_DIR, "build-img", "lineage-18.1-20250902-2052-r36s-android.img.zip")
    if os.path.exists(zip_path):
        print(f"[*] Extracting stock GPT blob (34 sectors) from {zip_path}...")
        with zipfile.ZipFile(zip_path) as z:
            with z.open("lineage-18.1-20250902-2052-r36s-android.img") as f:
                data = f.read(34 * 512)
                with open(gpt_path, "wb") as out:
                    out.write(data)
                print(f"    [+] Saved {len(data)} bytes to {gpt_path}")
                return data

    raise FileNotFoundError("Could not locate or extract stock gpt_head.bin!")


def insert_or_replace_file_in_cpio(cpio_data: bytes, filename: str, file_bytes: bytes, mode: int = 0o100755) -> bytes:
    pos = 0
    found_idx = None
    trailer_pos = None

    while pos < len(cpio_data):
        if cpio_data[pos : pos + 6] != b"070701":
            break
        header = cpio_data[pos : pos + 110]
        namesize = int(header[94:102], 16)
        filesize = int(header[54:62], 16)
        name_start = pos + 110
        name = cpio_data[name_start : name_start + namesize - 1].decode("utf-8", errors="replace")
        name_padded = (110 + namesize + 3) & ~3
        file_start = pos + name_padded
        file_padded = (filesize + 3) & ~3
        next_pos = file_start + file_padded

        if name == filename:
            found_idx = (pos, next_pos)
        if name == "TRAILER!!!":
            trailer_pos = pos
            break
        pos = next_pos

    name_bytes = filename.encode("ascii") + b"\x00"
    name_pad = (4 - ((110 + len(name_bytes)) % 4)) % 4
    data_pad = (4 - (len(file_bytes) % 4)) % 4

    hdr = (
        b"070701"
        + b"00000001"
        + f"{mode:08X}".encode("ascii")
        + b"00000000"
        + b"00000000"
        + b"00000001"
        + b"00000000"
        + f"{len(file_bytes):08X}".encode("ascii")
        + b"00000000"
        + b"00000000"
        + b"00000000"
        + b"00000000"
        + f"{len(name_bytes):08X}".encode("ascii")
        + b"00000000"
    )
    new_entry = hdr + name_bytes + (b"\x00" * name_pad) + file_bytes + (b"\x00" * data_pad)

    if found_idx is not None:
        p_start, p_end = found_idx[0], found_idx[1]
        return cpio_data[:p_start] + new_entry + cpio_data[p_end:]
    elif trailer_pos is not None:
        return cpio_data[:trailer_pos] + new_entry + cpio_data[trailer_pos:]
    else:
        raise RuntimeError("TRAILER!!! not found in CPIO archive!")


def create_uinitrd():
    img_resizing = bytearray(get_base_resizing_image())
    print(f"    [+] Successfully loaded Image-resizing ({len(img_resizing)} bytes)")

    print(f"[*] Decompressing gzip stream starting at offset {hex(GZIP_OFFSET)}...")
    decomp = zlib.decompressobj(16 + zlib.MAX_WBITS)
    cpio_data = decomp.decompress(bytes(img_resizing[GZIP_OFFSET:]))
    consumed_gz_len = len(img_resizing) - GZIP_OFFSET - len(decomp.unused_data)
    print(f"    [+] Decompressed CPIO archive: {len(cpio_data)} bytes (consumed {consumed_gz_len} gzip bytes)")

    # 1. Patch linuxrc in CPIO
    print("[*] Patching 'linuxrc' in CPIO archive...")
    patched_cpio = insert_or_replace_file_in_cpio(cpio_data, "linuxrc", NEW_LINUXRC, mode=0o100755)
    print(f"    [+] Successfully updated linuxrc ({len(NEW_LINUXRC)} bytes)")

    # 2. Embed stock gpt_head.bin in CPIO
    gpt_blob = extract_or_get_gpt_blob()
    print(f"[*] Embedding stock 'gpt_head.bin' ({len(gpt_blob)} bytes) into CPIO archive...")
    patched_cpio = insert_or_replace_file_in_cpio(patched_cpio, "gpt_head.bin", gpt_blob, mode=0o100644)
    print(f"    [+] Successfully embedded gpt_head.bin into CPIO")

    print(f"    [+] Patched CPIO archive size: {len(patched_cpio)} bytes")

    # Traverse patched CPIO archive to verify integrity
    print("[*] Verifying integrity of patched CPIO archive...")
    p = 0
    entries = 0
    trailer_found = False
    found_linuxrc = False
    found_gpt = False
    while p < len(patched_cpio):
        if patched_cpio[p : p + 6] != b"070701":
            break
        h = patched_cpio[p : p + 110]
        ns = int(h[94:102], 16)
        fs = int(h[54:62], 16)
        np = (110 + ns + 3) & ~3
        fp = (fs + 3) & ~3
        nm = patched_cpio[p + 110 : p + 110 + ns - 1].decode("utf-8", errors="replace")
        entries += 1
        p += np + fp
        if nm == "linuxrc":
            found_linuxrc = True
        elif nm == "gpt_head.bin":
            found_gpt = True
        elif nm == "TRAILER!!!":
            trailer_found = True
            break

    if not trailer_found:
        raise RuntimeError("CPIO validation failed: TRAILER!!! not reached!")
    if not found_linuxrc:
        raise RuntimeError("CPIO validation failed: linuxrc not found!")
    if not found_gpt:
        raise RuntimeError("CPIO validation failed: gpt_head.bin not found!")
    print(f"    [+] Verification passed: {entries} entries traversed (linuxrc OK, gpt_head.bin OK, TRAILER!!! OK)")

    # Compress with gzip level 9 for maximum compactness
    print("[*] Compressing modified CPIO archive with gzip (level 9)...")
    gz_data = gzip.compress(patched_cpio, compresslevel=9)
    print(f"    [+] Gzip level 9 compression complete: {len(gz_data)} bytes")

    # 3. Patch Image-resizing in place directly at GZIP_OFFSET
    if len(gz_data) <= ORIG_GZIP_LEN:
        pad_size = ORIG_GZIP_LEN - len(gz_data)
        replacement = gz_data + (b"\x00" * pad_size)
        img_resizing[GZIP_OFFSET : GZIP_OFFSET + ORIG_GZIP_LEN] = replacement
        print(f"    [+] Patched Image-resizing embedded initramfs ({len(gz_data)} bytes + {pad_size} pad bytes)")

        # Verify decompression of patched Image-resizing
        d_val = zlib.decompressobj(16 + zlib.MAX_WBITS)
        val_cpio = d_val.decompress(bytes(img_resizing[GZIP_OFFSET:]))
        assert val_cpio == patched_cpio, "Patched Image-resizing decompression verification failed!"
        print("    [+] Verified patched Image-resizing embedded initramfs decompresses cleanly!")

        # Write to boot-files/Image-resizing
        with open(OUT_IMG_RESIZING, "wb") as f:
            f.write(img_resizing)
        print(f"    [+] Written patched Image-resizing to {OUT_IMG_RESIZING}")

        if os.path.exists(E_DRIVE):
            with open(E_IMG_RESIZING, "wb") as f:
                f.write(img_resizing)
            print(f"    [+] Synchronized patched Image-resizing to {E_IMG_RESIZING}")
    else:
        print(f"    [!] Warning: Gzip size {len(gz_data)} > original {ORIG_GZIP_LEN}, skipped in-place kernel patch")

    # 4. Build standalone uInitrd
    print("[*] Wrapping in 64-byte U-Boot legacy uImage header...")
    final_hdr = build_uimage_header(gz_data)
    uinitrd_data = final_hdr + gz_data

    os.makedirs(os.path.dirname(OUT_UINITRD), exist_ok=True)
    with open(OUT_UINITRD, "wb") as f:
        f.write(uinitrd_data)
    print(f"    [+] Generated standalone uInitrd: {OUT_UINITRD} ({len(uinitrd_data)} bytes)")

    if os.path.exists(E_DRIVE):
        with open(E_UINITRD, "wb") as f:
            f.write(uinitrd_data)
        print(f"    [+] Synchronized uInitrd to {E_UINITRD}")
        with open(E_GPT_HEAD, "wb") as f:
            f.write(gpt_blob)
        print(f"    [+] Synchronized gpt_head.bin to {E_GPT_HEAD}")

    print("\n[SUCCESS] Custom uInitrd and Image-resizing ready!")


if __name__ == "__main__":
    create_uinitrd()
