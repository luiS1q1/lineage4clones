#!/usr/bin/env python3
"""
Build True Native LineageOS 18.1 (Linux 4.19) Device Tree Blob (rk3326-r36s-android.dtb)
for R36S Clone Type 2 Panel 1 with Amp.

Preserves 100% of the Linux 4.19 architecture (/vop@ff460000, /vop@ff470000, /iommu@ff470f00,
/mpp-srv, /vdpu, /vepu, /hevc, etc.) from the official LineageOS Panel 1 DTB while adapting
all hardware pinout / panel / audio / joystick / power parameters for Clone Type 2 Panel 1 with Amp:
1. /aliases: No mmc0/mmc1 swap aliases
2. /dsi@ff450000/panel@0:
   - reset-gpios = <&gpio3 27 1> ([141, 27, 1], GPIO3_PD3)
   - compatible = ["elida,kd35t133", "simple-panel-dsi"]
   - panel-init-sequence = 370-byte working clone sequence from rk3326-r36s-android.dtb.bak
   - display-timings: timing0, timing1, timing2 updated to clone timings (30MHz, 640x480, 150/40/135, 20/6/12)
   - power-supply = <&vcc18_lcd0> (phandle 189)
   - width-mm = 153, height-mm = 85, dsi,flags = 3587
   - delays: prepare=20, reset=20, init=20, enable=120, disable=20, unprepare=20
3. /vcc18_lcd0:
   - Fixed regulator for LCD logic power on GPIO3_PA3 ([141, 3, 0], active-high)
   - regulator-boot-on, regulator-always-on, min/max=1800000 uV, phandle 189
4. PMIC Regulators:
   - DCDC_REG1 (vdd_logic): min=950000, max=1350000 (1.35V headroom for Mali Bifrost GPU DVFS), always-on, boot-on
   - DCDC_REG2 (vdd_arm): min=950000, max=1350000, always-on, boot-on
   - LDO_REG1 (vcc_1v0): min=1000000, max=1000000, always-on, boot-on (prevents regulator_init_complete power cut)
   - LDO_REG5 (vccio_sd): min=1800000, max=3300000, regulator-always-on, regulator-boot-on (phandle 61)
   - LDO_REG6 (vcc_sd): min=3300000, max=3300000, regulator-always-on, regulator-boot-on (phandle 137)
   - LDO_REG7 (vcc_backlight): min=3000000, max=3000000, regulator-always-on, regulator-boot-on (phandle 190)
   - LDO_REG8 (vcc_lcd): min=3300000, max=3300000, regulator-always-on, regulator-boot-on (phandle 149)
   - LDO_REG9 (vcc_wifi): min=3300000, max=3300000, always-on, boot-on
5. /backlight:
   - pwms = <&pwm1 0 25000 0> ([186, 0, 25000, 0], 40 kHz)
   - power-supply = <&LDO_REG7> (phandle 190)
6. Audio Amplifier:
   - /i2c@ff180000/pmic@20/codec: spk-ctl-gpios = <&gpio3 7 0> ([141, 7, 0], active-high GPIO3_PA7)
   - spk-ctl-gpio = <&gpio3 7 0>
   - spk-mute-delay-ms = <50>, hp-mute-delay-ms = <50>, spk-volume = <3>, hp-volume = <20>
   - use-ext-amplifier
   - /rk817-sound: spk-ctl-gpios = <&gpio3 7 0>, simple-audio-card,hp-det-gpio = <&gpio2 22 1>
7. Joysticks & Buttons (/odroidgo3-joypad & /pinctrl):
   - /serial@ff160000: status = "okay" (keeps ttyS2 & pclk_uart2 active for console=ttyS2,115200n8 and ATF)
   - /fiq-debugger: status = "okay", rockchip,serial-id = <2>, pinctrl-0 = <70> (matches stock 4.19 so fiq-debugger yields cleanly to serial@ff160000)
   - /pinctrl/uart2-m1/uart2m1-xfer: rockchip,pins = <2 12 2 173> (claims only TX pin GPIO2_PB4, freeing GPIO2_PB6 [pin 14] for R3 thumbstick click sw11!)
   - amux-count = <4>
   - amux-channel-mapping = <2 3 1 0>
   - amux-a-gpios = <&gpio2 16 1> ([91, 16, 1], GPIO2_PC0)
   - amux-b-gpios = <&gpio2 15 1> ([91, 15, 1], GPIO2_PB7)
   - amux-en-gpios = <&gpio2 11 1> ([91, 11, 1], GPIO2_PB3)
   - Buttons: All 17 buttons mapped to Clone Type 2 physical GPIOs on GPIO3 and GPIO2
   - Pinctrl: /pinctrl/btns/btn-pins updated with pull-ups on all Clone Type 2 GPIOs
8. Volume Keys (/adc-keys):
   - Replaces stock /odroidgo3-keys (gpio-keys) with /adc-keys on SARADC channel 2
   - vol-down: 292000 uV (code 114)
   - vol-up: 15836 uV (code 115)
9. DMC (/dmc):
   - status = "disabled" (preserves 2-RAM DDR timings from idbloader.img)
10. SDMMC Controller (/dwmmc@ff370000):
   - max-frequency = 100000000 (100 MHz clone stability requirement, matching ArkOS clone DTB)
   - Remove sd-uhs-sdr12, sd-uhs-sdr25, sd-uhs-sdr50, sd-uhs-sdr104 to prevent 1.8V UHS-I switching dropout
11. Battery & Charger:
   - /i2c@ff180000/pmic@20/charger:
     - REMOVE bat_low_gpio (was erroneously assigned to GPIO2_PB5 which is joypad button, triggering false low bat!)
     - dc_det_gpio = <&gpio3 5 0> ([141, 5, 0], GPIO3_PA5, matching ArkOS clone hardware)
     - virtual_power = <1> (forces virtual battery mode so Android never triggers 0% battery shutdown)
     - chrg_finish_cur = <300>
   - /i2c@ff180000/pmic@20/battery:
     - virtual_power = <1> (forces MODE_VIRTUAL: 66% SoC, 3888mV, charging status)
     - power_off_thresd = <3000>
     - bat_res = <119>, design_capacity = <3124>, design_qmax = <3436>, power_dc2otg = <0>
     - ocv_table = <3300 3340 3380 ... 4046> (matches ArkOS clone curve)
12. Power & Status LEDs:
   - /gpio_leds:
     - heartbeat: label = "red:heartbeat", gpios = <&gpio0 17 0>
     - power: label = "blue:power", gpios = <&gpio0 0 0> (GPIO0_PA0, blue power LED), default-trigger = "default-on"
"""

import os
import sys
import hashlib
import shutil
import fdt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STOCK_419_DTB = os.path.join(BASE_DIR, "boot-files", "rk3326-r36s-panel1-stock-4.19.dtb")
BAK_DTB = os.path.join(BASE_DIR, "boot-files", "rk3326-r36s-android.dtb.bak")
OUT_BOOT_FILES = os.path.join(BASE_DIR, "boot-files", "rk3326-r36s-android.dtb")
E_DRIVE_DTB = os.path.join("E:\\", "rk3326-r36s-android.dtb")


def set_prop_safe(node, prop):
    """Sets or replaces a property on an fdt.Node."""
    existing = node.get_property(prop.name)
    if existing:
        node.remove_property(prop.name)
    node.append(prop)


def build():
    print("=" * 72)
    print("Building True Native LineageOS 18.1 (Linux 4.19) Clone DTB")
    print("=" * 72)

    # 1. Read base official 4.19 DTB
    if not os.path.exists(STOCK_419_DTB):
        alt_path = os.path.join("E:\\", "Panels", "Panel1", "rk3326-r36s-android.dtb")
        if os.path.exists(alt_path):
            print(f"[*] Copying stock 4.19 DTB from {alt_path} to {STOCK_419_DTB}...")
            shutil.copyfile(alt_path, STOCK_419_DTB)
        else:
            raise FileNotFoundError(f"Source 4.19 DTB not found at {STOCK_419_DTB} or {alt_path}")

    print(f"[*] Reading stock 4.19 Panel 1 DTB: {STOCK_419_DTB}")
    with open(STOCK_419_DTB, "rb") as f:
        dt419 = fdt.parse_dtb(f.read())

    print(f"[*] Reading working clone reference DTB: {BAK_DTB}")
    with open(BAK_DTB, "rb") as f:
        dtbak = fdt.parse_dtb(f.read())

    # Verify 4.19 architecture presence
    assert dt419.get_node("/vop@ff460000") is not None, "Missing /vop@ff460000 in base DTB!"
    assert dt419.get_node("/vop@ff470000") is not None, "Missing /vop@ff470000 in base DTB!"
    assert dt419.get_node("/iommu@ff470f00") is not None, "Missing /iommu@ff470f00 in base DTB!"
    assert dt419.get_node("/mpp-srv") is not None, "Missing /mpp-srv in base DTB!"
    print("    [+] Verified 100% Linux 4.19 dual-VOP & MPP architecture present in base DTB")

    # Hardware phandles in 4.19 DTB:
    # gpio0@ff040000: 81
    # gpio1@ff250000: 184
    # gpio2@ff260000: 91
    # gpio3@ff270000: 141
    # pcfg-pull-up: 173
    # saradc@ff288000: 183
    # pwm@ff200010 (pwm1): 186
    # Existing max phandle: 188
    # New phandles:
    PHANDLE_GPIO0 = 81
    PHANDLE_GPIO2 = 91
    PHANDLE_GPIO3 = 141
    PHANDLE_SARADC = 183
    PHANDLE_PULL_UP = 173
    PHANDLE_PWM1 = 186
    PHANDLE_VCC18_LCD0 = 189
    PHANDLE_LDO_REG7 = 190

    # ---------------------------------------------------------
    # 2a. /aliases: Ensure NO mmc0 or mmc1 aliases swap TF1/TF2
    # ---------------------------------------------------------
    aliases = dt419.get_node("/aliases")
    for mmc_alias in ["mmc0", "mmc1"]:
        if aliases.get_property(mmc_alias):
            aliases.remove_property(mmc_alias)
            print(f"    [-] Removed /aliases/{mmc_alias}")
    print("    [+] Verified /aliases has no mmc0/mmc1 swap aliases")

    # ---------------------------------------------------------
    # 2b. Fixed regulator /vcc18_lcd0 (GPIO3_PA3)
    # ---------------------------------------------------------
    try:
        vcc18 = dt419.get_node("/vcc18_lcd0")
    except Exception:
        vcc18 = fdt.Node("vcc18_lcd0")
        dt419.root.append(vcc18)

    set_prop_safe(vcc18, fdt.PropStrings("compatible", "regulator-fixed"))
    set_prop_safe(vcc18, fdt.PropStrings("regulator-name", "vcc18_lcd0_n"))
    set_prop_safe(vcc18, fdt.PropWords("regulator-min-microvolt", 1800000))
    set_prop_safe(vcc18, fdt.PropWords("regulator-max-microvolt", 1800000))
    set_prop_safe(vcc18, fdt.PropWords("gpio", PHANDLE_GPIO3, 3, 0))  # GPIO3_PA3 active-high
    set_prop_safe(vcc18, fdt.Property("enable-active-high"))
    set_prop_safe(vcc18, fdt.Property("regulator-boot-on"))
    set_prop_safe(vcc18, fdt.Property("regulator-always-on"))
    set_prop_safe(vcc18, fdt.PropWords("phandle", PHANDLE_VCC18_LCD0))
    print(f"    [+] Configured /vcc18_lcd0 on GPIO3_PA3 (phandle {PHANDLE_VCC18_LCD0})")

    # ---------------------------------------------------------
    # 2c. PMIC Regulators: DCDC1, DCDC2, LDO1..9, BOOST
    # ---------------------------------------------------------
    # DCDC_REG1: vdd_logic (950mV - 1350mV, 1.35V max ensures Bifrost GPU has headroom)
    dcdc1 = dt419.get_node("/i2c@ff180000/pmic@20/regulators/DCDC_REG1")
    set_prop_safe(dcdc1, fdt.PropWords("regulator-min-microvolt", 950000))
    set_prop_safe(dcdc1, fdt.PropWords("regulator-max-microvolt", 1350000))
    set_prop_safe(dcdc1, fdt.Property("regulator-always-on"))
    set_prop_safe(dcdc1, fdt.Property("regulator-boot-on"))
    print("    [+] Configured DCDC_REG1 (vdd_logic: 950mV-1350mV, always-on, boot-on)")

    # DCDC_REG2: vdd_arm (950mV - 1350mV)
    dcdc2 = dt419.get_node("/i2c@ff180000/pmic@20/regulators/DCDC_REG2")
    set_prop_safe(dcdc2, fdt.PropWords("regulator-min-microvolt", 950000))
    set_prop_safe(dcdc2, fdt.PropWords("regulator-max-microvolt", 1350000))
    set_prop_safe(dcdc2, fdt.Property("regulator-always-on"))
    set_prop_safe(dcdc2, fdt.Property("regulator-boot-on"))
    print("    [+] Configured DCDC_REG2 (vdd_arm: 950mV-1350mV, always-on, boot-on)")

    # LDO_REG1: vcc_1v0 (1.0V, critical internal SoC logic - must be always-on to prevent regulator_init_complete power cut)
    ldo1 = dt419.get_node("/i2c@ff180000/pmic@20/regulators/LDO_REG1")
    set_prop_safe(ldo1, fdt.PropWords("regulator-min-microvolt", 1000000))
    set_prop_safe(ldo1, fdt.PropWords("regulator-max-microvolt", 1000000))
    set_prop_safe(ldo1, fdt.Property("regulator-always-on"))
    set_prop_safe(ldo1, fdt.Property("regulator-boot-on"))
    print("    [+] Configured LDO_REG1 (vcc_1v0: 1.0V, always-on, boot-on)")

    # LDO_REG5: vccio_sd (1.8V - 3.3V)
    ldo5 = dt419.get_node("/i2c@ff180000/pmic@20/regulators/LDO_REG5")
    set_prop_safe(ldo5, fdt.PropStrings("regulator-name", "vccio_sd"))
    set_prop_safe(ldo5, fdt.PropWords("regulator-min-microvolt", 1800000))
    set_prop_safe(ldo5, fdt.PropWords("regulator-max-microvolt", 3300000))
    set_prop_safe(ldo5, fdt.Property("regulator-always-on"))
    set_prop_safe(ldo5, fdt.Property("regulator-boot-on"))
    print("    [+] Configured LDO_REG5 (vccio_sd: 1.8V-3.3V, always-on, boot-on)")

    # LDO_REG6: vcc_sd (3.3V)
    ldo6 = dt419.get_node("/i2c@ff180000/pmic@20/regulators/LDO_REG6")
    set_prop_safe(ldo6, fdt.PropStrings("regulator-name", "vcc_sd"))
    set_prop_safe(ldo6, fdt.PropWords("regulator-min-microvolt", 3300000))
    set_prop_safe(ldo6, fdt.PropWords("regulator-max-microvolt", 3300000))
    set_prop_safe(ldo6, fdt.Property("regulator-always-on"))
    set_prop_safe(ldo6, fdt.Property("regulator-boot-on"))
    print("    [+] Configured LDO_REG6 (vcc_sd: 3.3V, always-on, boot-on)")

    # LDO_REG7: vcc_backlight (3.0V)
    ldo7 = dt419.get_node("/i2c@ff180000/pmic@20/regulators/LDO_REG7")
    set_prop_safe(ldo7, fdt.PropStrings("regulator-name", "vcc_backlight"))
    set_prop_safe(ldo7, fdt.PropWords("regulator-min-microvolt", 3000000))
    set_prop_safe(ldo7, fdt.PropWords("regulator-max-microvolt", 3000000))
    set_prop_safe(ldo7, fdt.Property("regulator-always-on"))
    set_prop_safe(ldo7, fdt.Property("regulator-boot-on"))
    set_prop_safe(ldo7, fdt.PropWords("phandle", PHANDLE_LDO_REG7))
    print(f"    [+] Configured LDO_REG7 (vcc_backlight: 3.0V, always-on, boot-on, phandle {PHANDLE_LDO_REG7})")

    # LDO_REG8: vcc_lcd (3.3V)
    ldo8 = dt419.get_node("/i2c@ff180000/pmic@20/regulators/LDO_REG8")
    set_prop_safe(ldo8, fdt.PropStrings("regulator-name", "vcc_lcd"))
    set_prop_safe(ldo8, fdt.PropWords("regulator-min-microvolt", 3300000))
    set_prop_safe(ldo8, fdt.PropWords("regulator-max-microvolt", 3300000))
    set_prop_safe(ldo8, fdt.Property("regulator-always-on"))
    set_prop_safe(ldo8, fdt.Property("regulator-boot-on"))
    print("    [+] Configured LDO_REG8 (vcc_lcd: 3.3V, always-on, boot-on, phandle 149)")

    # LDO_REG9: vcc_wifi (3.3V)
    ldo9 = dt419.get_node("/i2c@ff180000/pmic@20/regulators/LDO_REG9")
    set_prop_safe(ldo9, fdt.Property("regulator-always-on"))
    set_prop_safe(ldo9, fdt.Property("regulator-boot-on"))
    print("    [+] Configured LDO_REG9 (vcc_wifi: 3.3V, always-on, boot-on)")

    # ---------------------------------------------------------
    # 2d. /backlight
    # ---------------------------------------------------------
    bl = dt419.get_node("/backlight")
    set_prop_safe(bl, fdt.PropWords("pwms", PHANDLE_PWM1, 0, 25000, 0))  # 40 kHz
    set_prop_safe(bl, fdt.PropWords("power-supply", PHANDLE_LDO_REG7))
    print("    [+] Configured /backlight (pwm1 @ 25000ns, power-supply = LDO_REG7)")

    # ---------------------------------------------------------
    # 2e. Display Panel (/dsi@ff450000/panel@0)
    # ---------------------------------------------------------
    panel = dt419.get_node("/dsi@ff450000/panel@0")
    set_prop_safe(panel, fdt.PropStrings("compatible", "elida,kd35t133", "simple-panel-dsi"))
    set_prop_safe(panel, fdt.PropWords("reset-gpios", PHANDLE_GPIO3, 27, 1))  # GPIO3_PD3, active-low
    set_prop_safe(panel, fdt.PropWords("power-supply", PHANDLE_VCC18_LCD0))

    # Panel init sequence from working BAK DTB (370 bytes)
    bak_panel = dtbak.get_node("/dsi@ff450000/panel@0")
    bak_seq = bak_panel.get_property("panel-init-sequence")
    assert len(bak_seq.data) == 370, f"Expected 370 bytes init sequence, got {len(bak_seq.data)}"
    set_prop_safe(panel, fdt.PropBytes("panel-init-sequence", *bak_seq.data))

    bak_exit = bak_panel.get_property("panel-exit-sequence")
    if bak_exit:
        set_prop_safe(panel, fdt.PropWords("panel-exit-sequence", *bak_exit.data))

    set_prop_safe(panel, fdt.PropWords("prepare-delay-ms", 20))
    set_prop_safe(panel, fdt.PropWords("reset-delay-ms", 20))
    set_prop_safe(panel, fdt.PropWords("init-delay-ms", 20))
    set_prop_safe(panel, fdt.PropWords("enable-delay-ms", 120))
    set_prop_safe(panel, fdt.PropWords("disable-delay-ms", 20))
    set_prop_safe(panel, fdt.PropWords("unprepare-delay-ms", 20))
    set_prop_safe(panel, fdt.PropWords("width-mm", 153))
    set_prop_safe(panel, fdt.PropWords("height-mm", 85))
    set_prop_safe(panel, fdt.PropWords("dsi,flags", 3587))
    set_prop_safe(panel, fdt.PropWords("dsi,format", 0))
    set_prop_safe(panel, fdt.PropWords("dsi,lanes", 4))

    # Display Timings for Clone Panel 1 (640x480 @ 30MHz)
    timings = dt419.get_node("/dsi@ff450000/panel@0/display-timings")
    timing_params = {
        "clock-frequency": 30000000,
        "hactive": 640,
        "vactive": 480,
        "hfront-porch": 150,
        "hsync-len": 40,
        "hback-porch": 135,
        "vfront-porch": 20,
        "vsync-len": 6,
        "vback-porch": 12,
        "hsync-active": 0,
        "vsync-active": 0,
        "de-active": 0,
        "pixelclk-active": 0,
    }
    for sub in timings.nodes:
        for k, v in timing_params.items():
            set_prop_safe(sub, fdt.PropWords(k, v))
        print(f"    [+] Updated {sub.name} display timings: 640x480 @ 30MHz, hfp=150, hsync=40, hbp=135")

    print("    [+] Configured /dsi@ff450000/panel@0 (reset-gpios=GPIO3_PD3, 370-byte init seq, vcc18_lcd0)")

    # ---------------------------------------------------------
    # 2f. Audio Amplifier (GPIO3_PA7) & Codec
    # ---------------------------------------------------------
    codec = dt419.get_node("/i2c@ff180000/pmic@20/codec")
    set_prop_safe(codec, fdt.PropWords("spk-ctl-gpios", PHANDLE_GPIO3, 7, 0))  # GPIO3_PA7 active-high
    set_prop_safe(codec, fdt.PropWords("spk-ctl-gpio", PHANDLE_GPIO3, 7, 0))
    set_prop_safe(codec, fdt.PropWords("spk-mute-delay-ms", 50))
    set_prop_safe(codec, fdt.PropWords("hp-mute-delay-ms", 50))
    set_prop_safe(codec, fdt.PropWords("spk-volume", 3))
    set_prop_safe(codec, fdt.PropWords("hp-volume", 20))
    set_prop_safe(codec, fdt.Property("use-ext-amplifier"))
    print("    [+] Configured /i2c@ff180000/pmic@20/codec (spk-ctl-gpios=GPIO3_PA7, use-ext-amplifier)")

    snd = dt419.get_node("/rk817-sound")
    set_prop_safe(snd, fdt.PropWords("spk-ctl-gpios", PHANDLE_GPIO3, 7, 0))
    set_prop_safe(snd, fdt.PropWords("spk-ctl-gpio", PHANDLE_GPIO3, 7, 0))
    # Headphone detect on Clone Type 2 is GPIO2_PC6 (pin 22) active-low
    set_prop_safe(snd, fdt.PropWords("simple-audio-card,hp-det-gpio", PHANDLE_GPIO2, 22, 1))
    print("    [+] Configured /rk817-sound (spk-ctl-gpios=GPIO3_PA7, hp-det=GPIO2_PC6 active-low)")

    # ---------------------------------------------------------
    # 2g. Joysticks & Action Buttons (/odroidgo3-joypad)
    # ---------------------------------------------------------
    # Keep /serial@ff160000 (ttyS2) and /fiq-debugger EXACTLY at their stock 4.19 settings
    # (status="okay", rockchip,serial-id=<2>, pinctrl-0=<70>) so ttyS2 stays alive for
    # console=ttyS2,115200n8 and ATF without gating pclk_uart2 or hanging on unclocked UART5!
    # To resolve the GPIO2_PB6 (pin 14) conflict with R3 (sw11), update /pinctrl/uart2-m1/uart2m1-xfer
    # (phandle 70) to only claim TX pin GPIO2_PB4 (<2 12 2 173>), freeing GPIO2_PB6 (pin 14) for joypad!
    serial2 = dt419.get_node("/serial@ff160000")
    set_prop_safe(serial2, fdt.PropStrings("status", "okay"))
    set_prop_safe(serial2, fdt.PropWords("pinctrl-0", 70))

    fiq = dt419.get_node("/fiq-debugger")
    set_prop_safe(fiq, fdt.PropStrings("status", "okay"))
    set_prop_safe(fiq, fdt.PropWords("rockchip,serial-id", 2))
    set_prop_safe(fiq, fdt.PropWords("pinctrl-0", 70))

    uart2m1_xfer = dt419.get_node("/pinctrl/uart2-m1/uart2m1-xfer")
    set_prop_safe(uart2m1_xfer, fdt.PropWords("rockchip,pins", 2, 12, 2, PHANDLE_PULL_UP))
    print("    [+] Restored /serial@ff160000 & /fiq-debugger (UART2) and removed GPIO2_14 from uart2m1-xfer!")

    joy = dt419.get_node("/odroidgo3-joypad")
    set_prop_safe(joy, fdt.PropWords("amux-count", 4))
    set_prop_safe(joy, fdt.PropWords("amux-channel-mapping", 2, 3, 1, 0))
    set_prop_safe(joy, fdt.PropWords("amux-a-gpios", PHANDLE_GPIO2, 16, 1))  # GPIO2_PC0
    set_prop_safe(joy, fdt.PropWords("amux-b-gpios", PHANDLE_GPIO2, 15, 1))  # GPIO2_PB7
    set_prop_safe(joy, fdt.PropWords("amux-en-gpios", PHANDLE_GPIO2, 11, 1)) # GPIO2_PB3
    print("    [+] Configured /odroidgo3-joypad AMUX (<2 3 1 0>, mux-en on GPIO2_PB3, preserved pinctrl-1)")

    # Remove all stock R36S buttons from /odroidgo3-joypad
    old_sw_nodes = [node for node in joy.nodes if node.name.startswith("sw")]
    for sw in old_sw_nodes:
        joy.remove_subnode(sw.name)

    # Add Clone Type 2 physical buttons with 100% verified GPIOs & Android keycodes
    # Physical layout:
    # DPAD: UP=GPIO3_PC6(22), DOWN=GPIO3_PC7(23), LEFT=GPIO3_PC4(20), RIGHT=GPIO3_PC5(21)
    # Action buttons: A=GPIO3_PC0(16), B=GPIO3_PC1(17), Y=GPIO3_PC3(19), X=GPIO3_PC2(18)
    # Triggers/Shoulders: TL/L1=GPIO3_PB5(13), TR/R1=GPIO3_PB3(11), TL2/L2=GPIO3_PB6(14), TR2/R2=GPIO3_PB4(12)
    # Control: SELECT=GPIO3_PD0(24), START=GPIO3_PD1(25), FN=GPIO3_PB2(10)
    # Thumb clicks: THUMBL=GPIO2_PB5(13), THUMBR=GPIO2_PB6(14)
    clone_buttons = [
        ("sw1",  "GPIO DPAD-UP",   103, PHANDLE_GPIO3, 22),  # KEY_UP
        ("sw2",  "GPIO DPAD-DOWN", 108, PHANDLE_GPIO3, 23),  # KEY_DOWN
        ("sw3",  "GPIO DPAD-LEFT", 105, PHANDLE_GPIO3, 20),  # KEY_LEFT
        ("sw4",  "GPIO DPAD-RIGHT",106, PHANDLE_GPIO3, 21),  # KEY_RIGHT
        ("sw5",  "GPIO KEY BTN-A", 304, PHANDLE_GPIO3, 16),  # BTN_A (Confirm/Enter)
        ("sw6",  "GPIO BTN-B",     305, PHANDLE_GPIO3, 17),  # BTN_B (Back/Cancel)
        ("sw7",  "GPIO BTN-Y",     308, PHANDLE_GPIO3, 19),  # BTN_Y
        ("sw8",  "GPIO BTN-X",     307, PHANDLE_GPIO3, 18),  # BTN_X
        ("sw11", "GPIO F3",        318, PHANDLE_GPIO2, 14),  # BTN_THUMBR (Right stick click)
        ("sw12", "GPIO F4",        317, PHANDLE_GPIO2, 13),  # BTN_THUMBL (Left stick click)
        ("sw13", "GPIO F5",        172, PHANDLE_GPIO3, 10),  # FN button (KEY_HOMEPAGE)
        ("sw15", "GPIO TOP-LEFT",  310, PHANDLE_GPIO3, 13),  # L1 (BTN_TL)
        ("sw16", "GPIO TOP-RIGHT", 311, PHANDLE_GPIO3, 11),  # R1 (BTN_TR)
        ("sw19", "GPIO F1",        314, PHANDLE_GPIO3, 24),  # SELECT (BTN_SELECT)
        ("sw20", "GPIO TOP-RIGHT2",313, PHANDLE_GPIO3, 12),  # R2 (BTN_TR2)
        ("sw21", "GPIO TOP-LEFT2", 312, PHANDLE_GPIO3, 14),  # L2 (BTN_TL2)
        ("sw22", "GPIO F2",        315, PHANDLE_GPIO3, 25),  # START (BTN_START)
    ]

    for name, label, code, gpio_ph, pin in clone_buttons:
        btn_node = fdt.Node(name)
        btn_node.append(fdt.PropWords("gpios", gpio_ph, pin, 1))  # active-low
        btn_node.append(fdt.PropStrings("label", label))
        btn_node.append(fdt.PropWords("linux,code", code))
        joy.append(btn_node)

    print(f"    [+] Configured {len(clone_buttons)} Clone Type 2 buttons on /odroidgo3-joypad (GPIO3 & GPIO2)")

    # ---------------------------------------------------------
    # 2h. Pinctrl for Clone Type 2 Buttons (/pinctrl/btns/btn-pins)
    # ---------------------------------------------------------
    btn_pins = dt419.get_node("/pinctrl/btns/btn-pins")
    clone_rockchip_pins = [
        3, 10, 0, PHANDLE_PULL_UP,  # BTN_F (GPIO3_PB2)
        3, 11, 0, PHANDLE_PULL_UP,  # BTN_TR / R1 (GPIO3_PB3)
        3, 12, 0, PHANDLE_PULL_UP,  # BTN_TR2 / R2 (GPIO3_PB4)
        3, 13, 0, PHANDLE_PULL_UP,  # BTN_TL / L1 (GPIO3_PB5)
        3, 14, 0, PHANDLE_PULL_UP,  # BTN_TL2 / L2 (GPIO3_PB6)
        3, 16, 0, PHANDLE_PULL_UP,  # BTN_A (GPIO3_PC0)
        3, 17, 0, PHANDLE_PULL_UP,  # BTN_B (GPIO3_PC1)
        3, 18, 0, PHANDLE_PULL_UP,  # BTN_X (GPIO3_PC2)
        3, 19, 0, PHANDLE_PULL_UP,  # BTN_Y (GPIO3_PC3)
        3, 20, 0, PHANDLE_PULL_UP,  # DPAD_LEFT (GPIO3_PC4)
        3, 21, 0, PHANDLE_PULL_UP,  # DPAD_RIGHT (GPIO3_PC5)
        3, 22, 0, PHANDLE_PULL_UP,  # DPAD_UP (GPIO3_PC6)
        3, 23, 0, PHANDLE_PULL_UP,  # DPAD_DOWN (GPIO3_PC7)
        3, 24, 0, PHANDLE_PULL_UP,  # BTN_SELECT (GPIO3_PD0)
        3, 25, 0, PHANDLE_PULL_UP,  # BTN_START (GPIO3_PD1)
        2, 13, 0, PHANDLE_PULL_UP,  # BTN_THUMBL (GPIO2_PB5)
        2, 14, 0, PHANDLE_PULL_UP,  # BTN_THUMBR (GPIO2_PB6)
    ]
    set_prop_safe(btn_pins, fdt.PropWords("rockchip,pins", *clone_rockchip_pins))
    print(f"    [+] Updated /pinctrl/btns/btn-pins for Clone Type 2 (17 pins with pull-up phandle {PHANDLE_PULL_UP})")

    # ---------------------------------------------------------
    # 2i. Volume Keys (/adc-keys on SARADC Channel 2)
    # ---------------------------------------------------------
    # Remove stock /odroidgo3-keys (gpio-keys on GPIO2 pins 0 & 1)
    try:
        dt419.root.remove_subnode("odroidgo3-keys")
        print("    [-] Removed /odroidgo3-keys (stock GPIO volume keys)")
    except Exception:
        pass

    try:
        adc_keys = dt419.get_node("/adc-keys")
    except Exception:
        adc_keys = fdt.Node("adc-keys")
        dt419.root.append(adc_keys)

    set_prop_safe(adc_keys, fdt.PropStrings("compatible", "adc-keys"))
    set_prop_safe(adc_keys, fdt.PropWords("io-channels", PHANDLE_SARADC, 2))
    set_prop_safe(adc_keys, fdt.PropStrings("io-channel-names", "buttons"))
    set_prop_safe(adc_keys, fdt.PropWords("keyup-threshold-microvolt", 1800000))
    set_prop_safe(adc_keys, fdt.PropWords("poll-interval", 100))

    # Remove existing subnodes if any
    for sub in list(adc_keys.nodes):
        adc_keys.remove_subnode(sub.name)

    # Add Clone Type 2 volume keys with exact resistor ladder ADC thresholds
    voldown = fdt.Node("vol-down-key")
    voldown.append(fdt.PropStrings("label", "volume down"))
    voldown.append(fdt.PropWords("linux,code", 114))
    voldown.append(fdt.PropWords("press-threshold-microvolt", 292000))
    adc_keys.append(voldown)

    volup = fdt.Node("vol-up-key")
    volup.append(fdt.PropStrings("label", "volume up"))
    volup.append(fdt.PropWords("linux,code", 115))
    volup.append(fdt.PropWords("press-threshold-microvolt", 15836))
    adc_keys.append(volup)
    print("    [+] Configured /adc-keys on SARADC channel 2 (vol-down=292mV, vol-up=15.8mV)")

    # ---------------------------------------------------------
    # 2j. DMC (/dmc)
    # ---------------------------------------------------------
    dmc = dt419.get_node("/dmc")
    set_prop_safe(dmc, fdt.PropStrings("status", "disabled"))
    print("    [+] Set /dmc status = 'disabled' (protects 2-RAM DDR timings)")

    # ---------------------------------------------------------
    # 2k. SDMMC Controller (/dwmmc@ff370000)
    # ---------------------------------------------------------
    mmc0 = dt419.get_node("/dwmmc@ff370000")
    set_prop_safe(mmc0, fdt.PropWords("max-frequency", 100000000))
    # Remove UHS-I 1.8V switching modes to keep controller rock-solid in 3.3V High-Speed mode
    uhs_props_to_remove = ["sd-uhs-sdr12", "sd-uhs-sdr25", "sd-uhs-sdr50", "sd-uhs-sdr104"]
    for uhs_prop in uhs_props_to_remove:
        if mmc0.get_property(uhs_prop):
            mmc0.remove_property(uhs_prop)
            print(f"    [-] Removed /dwmmc@ff370000/{uhs_prop} (lock SDMMC to 3.3V High-Speed)")
    print("    [+] Configured /dwmmc@ff370000 (max-frequency = 100000000 Hz / 100MHz, UHS-I 1.8V modes removed)")

    # TF2 / Game Card Controller (/dwmmc@ff380000)
    # CRITICAL ROOT CAUSE FOR JOYPAD FAILURE:
    # On stock R36S, cd-gpios was set to <&gpio3 14 1>.
    # On Clone Type 2, GPIO3_PB6 (pin 14) is physical L2 button (sw21 / BTN_TL2).
    # When dwmmc@ff380000 claimed GPIO3 pin 14, joypad_probe's devm_gpio_request_one
    # for sw21 returned -EBUSY (-16), aborting joypad probe and disabling ALL controls!
    # On Clone Type 2, TF2 card detect is wired to GPIO0_PA2 (pin 2 active-low).
    mmc1 = dt419.get_node("/dwmmc@ff380000")
    set_prop_safe(mmc1, fdt.PropWords("cd-gpios", PHANDLE_GPIO0, 2, 1))
    set_prop_safe(mmc1, fdt.PropWords("max-frequency", 100000000))
    for uhs_prop in uhs_props_to_remove:
        if mmc1.get_property(uhs_prop):
            mmc1.remove_property(uhs_prop)
    print("    [+] Configured /dwmmc@ff380000 (cd-gpios=GPIO0_PA2 [81, 2, 1], freed GPIO3 pin 14 for L2 button!)")

    # ---------------------------------------------------------
    # 2l. Battery and Charger Subsystem
    # ---------------------------------------------------------
    # Charger: Remove incorrect bat_low_gpio (was GPIO2_PB5 joypad button!), set clone dc_det_gpio (GPIO3_PA5)
    chrg = dt419.get_node("/i2c@ff180000/pmic@20/charger")
    if chrg.get_property("bat_low_gpio"):
        chrg.remove_property("bat_low_gpio")
        print("    [-] Removed /charger/bat_low_gpio (eliminated false low-battery interrupt from gamepad button)")
    set_prop_safe(chrg, fdt.PropWords("dc_det_gpio", PHANDLE_GPIO3, 5, 0))  # GPIO3_PA5 matching ArkOS clone
    set_prop_safe(chrg, fdt.PropWords("virtual_power", 1))
    set_prop_safe(chrg, fdt.PropWords("chrg_finish_cur", 300))
    print("    [+] Configured /charger (dc_det=GPIO3_PA5, virtual_power=1, finish_cur=300)")

    # Battery: Set virtual_power=1 (forces MODE_VIRTUAL: 66% SoC, 3888mV, charging status), preventing Android 0% battery shutdown
    bat = dt419.get_node("/i2c@ff180000/pmic@20/battery")
    if bat.get_property("bat_low_gpio"):
        bat.remove_property("bat_low_gpio")
    set_prop_safe(bat, fdt.PropWords("virtual_power", 1))
    set_prop_safe(bat, fdt.PropWords("bat_res", 119))
    set_prop_safe(bat, fdt.PropWords("design_capacity", 3124))
    set_prop_safe(bat, fdt.PropWords("design_qmax", 3436))
    set_prop_safe(bat, fdt.PropWords("power_off_thresd", 3000))
    set_prop_safe(bat, fdt.PropWords("ocv_table",
        3300, 3340, 3380, 3420, 3460, 3500, 3540, 3570, 3610, 3650,
        3690, 3720, 3750, 3790, 3830, 3870, 3910, 3940, 3967, 4001, 4046))
    set_prop_safe(bat, fdt.PropWords("power_dc2otg", 0))
    print("    [+] Configured /battery (virtual_power=1, power_off_thresd=3000, ArkOS OCV curve, bat_res=119)")

    # ---------------------------------------------------------
    # 2m. Power and Status LEDs
    # ---------------------------------------------------------
    leds = dt419.get_node("/gpio_leds")
    hb = leds.get_subnode("heartbeat")
    if hb:
        set_prop_safe(hb, fdt.PropStrings("label", "red:heartbeat"))
        print("    [+] Renamed heartbeat LED to 'red:heartbeat' (GPIO0_PC1)")

    pwr_led = leds.get_subnode("power")
    if not pwr_led:
        pwr_led = fdt.Node("power")
        leds.append(pwr_led)
    set_prop_safe(pwr_led, fdt.PropStrings("label", "blue:power"))
    set_prop_safe(pwr_led, fdt.PropWords("gpios", PHANDLE_GPIO0, 0, 0))  # GPIO0_PA0, active-high
    set_prop_safe(pwr_led, fdt.PropStrings("default-state", "on"))
    set_prop_safe(pwr_led, fdt.PropStrings("linux,default-trigger", "default-on"))
    print("    [+] Added /gpio_leds/power (blue:power on GPIO0_PA0, default-on)")

    # ---------------------------------------------------------
    # 3. Serialize and Validate DTB
    # ---------------------------------------------------------
    patched_dtb_bytes = dt419.to_dtb()
    print(f"\n[*] Patched DTB successfully serialized: {len(patched_dtb_bytes)} bytes")

    # Validate readback
    dt_val = fdt.parse_dtb(patched_dtb_bytes)
    assert dt_val.get_node("/vop@ff460000") is not None
    assert dt_val.get_node("/vop@ff470000") is not None
    assert dt_val.get_node("/iommu@ff470f00") is not None
    assert dt_val.get_node("/mpp-srv") is not None
    assert dt_val.get_node("/vcc18_lcd0") is not None
    assert dt_val.get_node("/dsi@ff450000/panel@0").get_property("reset-gpios").data == [141, 27, 1]
    assert len(dt_val.get_node("/dsi@ff450000/panel@0").get_property("panel-init-sequence").data) == 370
    assert dt_val.get_node("/dmc").get_property("status").value == "disabled"
    assert dt_val.get_node("/dwmmc@ff370000").get_property("max-frequency").data == [100000000]

    # Verify UART2 / FIQ-Debugger & freed GPIO2_14
    assert dt_val.get_node("/serial@ff160000").get_property("status").value == "okay"
    assert dt_val.get_node("/fiq-debugger").get_property("status").value == "okay"
    assert dt_val.get_node("/fiq-debugger").get_property("rockchip,serial-id").data == [2]
    assert dt_val.get_node("/pinctrl/uart2-m1/uart2m1-xfer").get_property("rockchip,pins").data == [2, 12, 2, 173]

    # Verify joypad buttons
    val_joy = dt_val.get_node("/odroidgo3-joypad")
    assert val_joy.get_property("amux-channel-mapping").data == [2, 3, 1, 0]
    assert val_joy.get_subnode("sw1").get_property("gpios").data == [141, 22, 1], "sw1 DPAD-UP must be GPIO3_PC6"
    assert val_joy.get_subnode("sw2").get_property("gpios").data == [141, 23, 1], "sw2 DPAD-DOWN must be GPIO3_PC7"
    assert val_joy.get_subnode("sw3").get_property("gpios").data == [141, 20, 1], "sw3 DPAD-LEFT must be GPIO3_PC4"
    assert val_joy.get_subnode("sw4").get_property("gpios").data == [141, 21, 1], "sw4 DPAD-RIGHT must be GPIO3_PC5"
    assert val_joy.get_subnode("sw5").get_property("gpios").data == [141, 16, 1], "sw5 BTN-A must be GPIO3_PC0"
    assert val_joy.get_subnode("sw6").get_property("gpios").data == [141, 17, 1], "sw6 BTN-B must be GPIO3_PC1"
    assert val_joy.get_subnode("sw11").get_property("gpios").data == [91, 14, 1], "sw11 THUMBR must be GPIO2_PB6"
    assert val_joy.get_subnode("sw12").get_property("gpios").data == [91, 13, 1], "sw12 THUMBL must be GPIO2_PB5"
    assert val_joy.get_property("pinctrl-1").data == [112], "pinctrl-1 must be preserved on odroidgo3-joypad"
    assert val_joy.get_subnode("sw11").get_property("linux,code").data == [318], "sw11 code must be 318"
    assert val_joy.get_subnode("sw12").get_property("linux,code").data == [317], "sw12 code must be 317"
    assert val_joy.get_subnode("sw20").get_property("gpios").data == [141, 12, 1], "sw20 TR2 must be GPIO3_PB4"
    assert val_joy.get_subnode("sw21").get_property("gpios").data == [141, 14, 1], "sw21 TL2 must be GPIO3_PB6"
    assert val_joy.get_subnode("sw22").get_property("gpios").data == [141, 25, 1], "sw22 START must be GPIO3_PD1"
    assert dt_val.get_node("/dwmmc@ff380000").get_property("cd-gpios").data == [81, 2, 1], "dwmmc@ff380000 cd-gpios must be GPIO0_PA2"

    # Verify pinctrl
    val_pins = dt_val.get_node("/pinctrl/btns/btn-pins").get_property("rockchip,pins").data
    assert val_pins == clone_rockchip_pins, "btn-pins rockchip,pins mismatch!"

    # Verify adc-keys
    val_adc_keys = dt_val.get_node("/adc-keys")
    assert val_adc_keys is not None
    assert val_adc_keys.get_property("io-channels").data == [183, 2]
    assert val_adc_keys.get_subnode("vol-down-key").get_property("press-threshold-microvolt").data == [292000]
    assert val_adc_keys.get_subnode("vol-up-key").get_property("press-threshold-microvolt").data == [15836]

    # Verify audio
    assert dt_val.get_node("/i2c@ff180000/pmic@20/codec").get_property("spk-ctl-gpios").data == [141, 7, 0]
    assert dt_val.get_node("/rk817-sound").get_property("simple-audio-card,hp-det-gpio").data == [91, 22, 1]

    # Verify battery/charger
    val_chrg = dt_val.get_node("/i2c@ff180000/pmic@20/charger")
    assert val_chrg.get_property("bat_low_gpio") is None
    assert val_chrg.get_property("virtual_power").data == [1]
    assert val_chrg.get_property("dc_det_gpio").data == [141, 5, 0]

    val_bat = dt_val.get_node("/i2c@ff180000/pmic@20/battery")
    assert val_bat.get_property("virtual_power").data == [1]

    # Verify LED
    assert dt_val.get_node("/gpio_leds").get_subnode("power").get_property("gpios").data == [81, 0, 0]

    print("[+] Complete DTB verification PASSED: all Clone Type 2 buttons, ADC keys & Audio verified!")

    # Write to boot-files/rk3326-r36s-android.dtb
    os.makedirs(os.path.dirname(OUT_BOOT_FILES), exist_ok=True)
    with open(OUT_BOOT_FILES, "wb") as f:
        f.write(patched_dtb_bytes)
    print(f"[+] Written to {OUT_BOOT_FILES} (sha256: {hashlib.sha256(patched_dtb_bytes).hexdigest()})")

    # Write to E:\rk3326-r36s-android.dtb if E: is mounted
    if os.path.exists("E:\\"):
        with open(E_DRIVE_DTB, "wb") as f:
            f.write(patched_dtb_bytes)
        print(f"[+] Written to {E_DRIVE_DTB}")

    return patched_dtb_bytes


if __name__ == "__main__":
    build()
