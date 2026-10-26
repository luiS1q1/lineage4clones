import fdt, os, shutil, ctypes

# 1. Patch DTB to disable /dmc and /dfi
dtb_path = 'boot-files/rk3326-r36s-android.dtb'
with open(dtb_path, 'rb') as f:
    d = fdt.parse_dtb(f.read())

if d.exist_node('/dmc'):
    d.get_node('/dmc').set_property('status', 'disabled')
    print('[+] /dmc set to disabled')

if d.exist_node('/dfi@ff610000'):
    d.get_node('/dfi@ff610000').set_property('status', 'disabled')
    print('[+] /dfi@ff610000 set to disabled')

with open(dtb_path, 'wb') as f:
    f.write(d.to_dtb())
print('[+] Saved patched DTB')

shutil.copy2(dtb_path, 'E:/rk3326-r36s-android.dtb')
print('[+] Copied to E:/rk3326-r36s-android.dtb')

# 2. Update E:\boot.ini with clean bootargs (no rootwait, no init=/init, clean rdinit=/linuxrc)
boot_ini_content = """odroidgoa-uboot-config

setenv bootargs "rdinit=/linuxrc console=tty0 fbcon=rotate:0 earlyprintk swiotlb=1 coherent_pool=1m firmware_class.path=/vendor/firmware androidboot.hardware=rk30board androidboot.selinux=permissive"

# Set load addresses
setenv kernel_addr_r "0x02000000"
setenv initrd_addr_r "0x01100000"
setenv fdt_addr_r "0x01f00000"

load mmc 1:1 ${kernel_addr_r} Image
load mmc 1:1 ${initrd_addr_r} uInitrd
load mmc 1:1 ${fdt_addr_r} rk3326-r36s-android.dtb

fatwrite mmc 1:1 0x01f00000 UBOOT_OK.TXT 0x40
lcdputs "U-BOOT: Booting Linux with DMC disabled..."
booti ${kernel_addr_r} ${initrd_addr_r} ${fdt_addr_r}
"""

with open('E:/boot.ini', 'wb') as f:
    f.write(boot_ini_content.replace('\r\n', '\n').encode('ascii'))
    f.flush()
    os.fsync(f.fileno())
print('[+] Updated E:/boot.ini')

if os.path.exists('E:/UBOOT_OK.TXT'):
    os.remove('E:/UBOOT_OK.TXT')
    print('[+] Cleared E:/UBOOT_OK.TXT')

# Flush volume buffers
try:
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateFileW(
        r'\\.\E:',
        0x10000000 | 0x40000000,
        0x00000001 | 0x00000002,
        None, 3, 0, None
    )
    if handle != -1:
        kernel32.FlushFileBuffers(handle)
        kernel32.CloseHandle(handle)
        print('[+] Flushed E: volume buffers successfully')
except Exception as ex:
    print('[*] Flush:', ex)
