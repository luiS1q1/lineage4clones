#!/usr/bin/env python3
"""
Patches SDMMC voltage/frequency and PMIC regulators in rk3326-r36s-android.dtb
starting from rk3326-r36s-android.dtb.bak.
"""

import hashlib
import os
import shutil
import fdt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BAK_DTB = os.path.join(BASE_DIR, "boot-files", "rk3326-r36s-android.dtb.bak")
ARKOS_DTB = os.path.join(BASE_DIR, "boot-files", "arkos_clone_type2.dtb")
OUT_DTB = os.path.join(BASE_DIR, "boot-files", "rk3326-r36s-android.dtb")
E_DTB = r"E:\rk3326-r36s-android.dtb"

def copy_regulator_props(src_node, dst_node, name):
    orig_phandle_prop = dst_node.get_property("phandle")
    orig_phandle_val = orig_phandle_prop.data[0] if orig_phandle_prop else None

    # Clear existing props in dst_node
    for p in list(dst_node.props):
        dst_node.remove_property(p.name)

    # Copy props from src_node
    for p in src_node.props:
        if p.name == "phandle":
            if orig_phandle_val is not None:
                dst_node.set_property("phandle", orig_phandle_val)
        else:
            dst_node.append(p.copy())

    print(f"[+] {name} updated:")
    for p in dst_node.props:
        print(f"    - {p}")

def patch():
    print(f"[*] Reading arkos dtb: {ARKOS_DTB}")
    with open(ARKOS_DTB, "rb") as f:
        arkos = fdt.parse_dtb(f.read())

    print(f"[*] Reading android bak dtb: {BAK_DTB}")
    with open(BAK_DTB, "rb") as f:
        android = fdt.parse_dtb(f.read())

    # 1. Copy LDO_REG5 and LDO_REG6 properties from ArkOS
    ldo5_ark = arkos.get_node("/i2c@ff180000/pmic@20/regulators/LDO_REG5")
    ldo5_and = android.get_node("/i2c@ff180000/pmic@20/regulators/LDO_REG5")
    copy_regulator_props(ldo5_ark, ldo5_and, "LDO_REG5")

    ldo6_ark = arkos.get_node("/i2c@ff180000/pmic@20/regulators/LDO_REG6")
    ldo6_and = android.get_node("/i2c@ff180000/pmic@20/regulators/LDO_REG6")
    copy_regulator_props(ldo6_ark, ldo6_and, "LDO_REG6")

    # Restore regulator-always-on and regulator-boot-on on LDO_REG6
    if not ldo6_and.exist_property("regulator-always-on"):
        ldo6_and.append(fdt.Property("regulator-always-on"))
    if not ldo6_and.exist_property("regulator-boot-on"):
        ldo6_and.append(fdt.Property("regulator-boot-on"))
    print("[+] LDO_REG6 regulator-always-on and regulator-boot-on restored")

    # 2. DCDC_REG1: regulator-max-microvolt = 1350000
    dcdc1_and = android.get_node("/i2c@ff180000/pmic@20/regulators/DCDC_REG1")
    dcdc1_and.set_property("regulator-max-microvolt", 1350000)
    print(f"[+] DCDC_REG1 regulator-max-microvolt set to: {dcdc1_and.get_property('regulator-max-microvolt')}")

    # 3. dwmmc@ff370000: max-frequency = 100000000
    dwmmc_and = android.get_node("/dwmmc@ff370000")
    dwmmc_and.set_property("max-frequency", 100000000)
    print(f"[+] dwmmc@ff370000 max-frequency set to: {dwmmc_and.get_property('max-frequency')}")

    # 4. Check aliases
    aliases = android.get_node("/aliases")
    if aliases:
        assert not aliases.exist_property("mmc0"), "aliases contains mmc0!"
        assert not aliases.exist_property("mmc1"), "aliases contains mmc1!"
        print("[+] Verified /aliases has NO mmc0 or mmc1 properties")

    # 5. Serialize to dtb
    dtb_bytes = android.to_dtb()

    # Verify reparsing
    verify_dt = fdt.parse_dtb(dtb_bytes)
    v_ldo5 = verify_dt.get_node("/i2c@ff180000/pmic@20/regulators/LDO_REG5")
    v_ldo6 = verify_dt.get_node("/i2c@ff180000/pmic@20/regulators/LDO_REG6")
    v_dcdc1 = verify_dt.get_node("/i2c@ff180000/pmic@20/regulators/DCDC_REG1")
    v_dwmmc = verify_dt.get_node("/dwmmc@ff370000")

    assert v_ldo5.get_property("phandle").data[0] == 75
    assert v_ldo5.get_property("regulator-min-microvolt").data[0] == 1800000
    assert v_ldo5.get_property("regulator-max-microvolt").data[0] == 3300000
    assert v_ldo5.exist_property("regulator-always-on")
    assert v_ldo5.exist_property("regulator-boot-on")

    assert v_ldo6.get_property("phandle").data[0] == 148
    assert v_ldo6.get_property("regulator-min-microvolt").data[0] == 3300000
    assert v_ldo6.get_property("regulator-max-microvolt").data[0] == 3300000
    assert v_ldo6.exist_property("regulator-always-on")
    assert v_ldo6.exist_property("regulator-boot-on")

    assert v_dcdc1.get_property("regulator-max-microvolt").data[0] == 1350000
    assert v_dwmmc.get_property("max-frequency").data[0] == 100000000
    assert v_dwmmc.exist_property("sd-uhs-sdr12")
    assert v_dwmmc.exist_property("sd-uhs-sdr25")
    assert v_dwmmc.exist_property("sd-uhs-sdr50")
    assert v_dwmmc.exist_property("sd-uhs-sdr104")

    print("[+] All verification checks PASSED!")

    # Write to boot-files/rk3326-r36s-android.dtb
    with open(OUT_DTB, "wb") as f:
        f.write(dtb_bytes)
    print(f"[+] Written to {OUT_DTB} ({len(dtb_bytes)} bytes, SHA256: {hashlib.sha256(dtb_bytes).hexdigest()})")

    # Write to E:\rk3326-r36s-android.dtb
    if os.path.exists(r"E:\ "):
        pass
    with open(E_DTB, "wb") as f:
        f.write(dtb_bytes)
        f.flush()
        os.fsync(f.fileno())
    print(f"[+] Written to {E_DTB} ({len(dtb_bytes)} bytes, SHA256: {hashlib.sha256(dtb_bytes).hexdigest()})")

if __name__ == "__main__":
    patch()
